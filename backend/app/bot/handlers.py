import hashlib
import secrets
import warnings
from datetime import datetime, timezone, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from sqlalchemy import select, func, and_
import logging
import re

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import encrypt_text, decrypt_text, encrypt_case_content, encrypt_comment_content
from app.models import (
    Case, CaseAttachment, CaseComment, CaseCategory,
    CasePriority, CaseStatus, PollQuestion, PollOption, PollStatus
)
from app.services.storage import save_telegram_file
from app.services.notification import notify_admins
from app.services.bot_users import get_or_create_bot_user, update_bot_user_lang, get_bot_user_lang as db_get_user_lang
from app.bot.rate_limit import check_rate_limit, rate_limited
from app.bot.i18n import t, get_user_lang, set_user_lang, get_language_keyboard, SUPPORTED_LANGS

logger = logging.getLogger(__name__)

# ─── Conversation states ──────────────────────────────────────────────────────
(
    MAIN_MENU,
    CHOOSE_CATEGORY,
    ENTER_DESCRIPTION,
    ADD_ATTACHMENT,
    CHOOSE_ANONYMOUS,
    CONFIRM,
    CHECK_STATUS,
    FOLLOWUP_ENTER,
) = range(8)

CATEGORY_MAP = {
    "🔴 Korrupsiya / Pora": CaseCategory.CORRUPTION,
    "⚖️ Manfaatlar to'qnashuvi": CaseCategory.CONFLICT_OF_INTEREST,
    "💸 Firibgarlik / O'g'irlik": CaseCategory.FRAUD,
    "⚠️ Xavfsizlik buzilishi": CaseCategory.SAFETY,
    "🚫 Kamsitish / Bezovtalik": CaseCategory.DISCRIMINATION,
    "📋 Tender buzilishi": CaseCategory.PROCUREMENT,
    "❓ Boshqa": CaseCategory.OTHER,
}

PRIORITY_BY_CATEGORY = {
    CaseCategory.CORRUPTION: CasePriority.HIGH,
    CaseCategory.FRAUD: CasePriority.HIGH,
    CaseCategory.CONFLICT_OF_INTEREST: CasePriority.MEDIUM,
    CaseCategory.SAFETY: CasePriority.CRITICAL,
    CaseCategory.DISCRIMINATION: CasePriority.MEDIUM,
    CaseCategory.PROCUREMENT: CasePriority.MEDIUM,
    CaseCategory.OTHER: CasePriority.LOW,
}

WELCOME_TEXT = """
🛡️ *Integrity Hotline Bot*

Ushbu bot orqali siz xavfsiz va anonim tarzda muammo yoki qoidabuzarlik haqida xabar yuborishingiz mumkin.

*Kafolatlar:*
✅ To'liq anonimlik (istalsa)
✅ Xabaringiz shifrlangan holda saqlanadi
✅ Compliance departamenti darhol xabardor bo'ladi
✅ 7 ish kuni ichida ko'rib chiqiladi

Nima qilishni istaysiz?
"""

CATEGORY_TEXT = """
📋 *Murojaat kategoriyasini tanlang:*

Eng mos kategoriyani belgilang. Bu murojaat ustuvorligini belgilashga yordam beradi.
"""

HELP_TEXT = """
ℹ️ *Integrity Hotline Bot — Yordam*

*Asosiy buyruqlar:*
/start — Bosh menyuga qaytish
/help — Ushbu yordam sahifasi
/cancel — Joriy jarayonni bekor qilish

*Nima qila olaman?*
📝 *Murojaat yuborish* — Qoidabuzarlik haqida xabar bering
🔍 *Holat tekshirish* — Murojaatingiz statusini ko'ring
💬 *Javob yuborish* — Adminga qo'shimcha ma'lumot yuboring
❓ *FAQ* — Ko'p so'raladigan savollarga javoblar

*Anonimlik haqida:*
Siz anonim yuborishni tanlasangiz, shaxsiyatingiz hech qanday tizimda saqlanmaydi. Lekin javob olish uchun Telegram orqali muloqot davom etadi — faqat siz va bot.

*Murojaat ID ni yo'qotdingizmi?*
Afsuski, ID ni qayta olish imkoni yo'q. Kelajakda uni xavfsiz joyda saqlang.

*Muammo yuzaga keldimi?*
compliance@company.uz manziliga yozing.
"""


def get_main_keyboard(lang: str = "uz"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_report", lang),       callback_data="report")],
        [InlineKeyboardButton(t("btn_check_status", lang), callback_data="check_status")],
        [InlineKeyboardButton(t("btn_followup", lang),     callback_data="followup_prompt")],
        [InlineKeyboardButton(t("btn_faq", lang),          callback_data="faq")],
        [InlineKeyboardButton(t("btn_contacts", lang),     callback_data="contacts")],
    ])


def get_category_keyboard(lang: str = "uz"):
    category_keys = [
        "category_corruption", "category_conflict", "category_fraud",
        "category_safety", "category_discrimination", "category_procurement",
        "category_other",
    ]
    buttons = [
        [InlineKeyboardButton(t(key, lang), callback_data=f"cat_{i}")]
        for i, key in enumerate(category_keys)
    ]
    buttons.append([InlineKeyboardButton(t("cancel_btn", lang), callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def get_persistent_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Har doim xabar yozish maydoni yonida ko'rinadigan tugmalar"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t("menu_submit", lang)),      KeyboardButton(t("menu_check_status", lang))],
            [KeyboardButton(t("menu_reply_admin", lang)), KeyboardButton(t("menu_my_cases", lang))],
            [KeyboardButton(t("menu_help", lang)),        KeyboardButton(t("menu_settings", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# Barcha tillardagi persistent menu tugma matnlari (ConversationHandler Regex uchun)
_MENU_KEYS = ["menu_submit", "menu_check_status", "menu_reply_admin",
              "menu_my_cases", "menu_help", "menu_settings"]
_ALL_MENU_TEXTS = set()
for _key in _MENU_KEYS:
    for _lang in SUPPORTED_LANGS:
        _ALL_MENU_TEXTS.add(t(_key, _lang))
MENU_BUTTON_REGEX = "^(" + "|".join(re.escape(txt) for txt in _ALL_MENU_TEXTS) + ")$"


async def generate_case_id() -> str:
    async with AsyncSessionLocal() as db:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        result = await db.execute(
            select(func.count(Case.id)).where(
                Case.external_id.like(f"CASE-{today}-%")
            )
        )
        count = result.scalar() + 1
        return f"CASE-{today}-{count:05d}"


# ─── /start ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Guruh chatida /start berilsa — faqat qisqa yo'naltirish xabari
    if chat.type in ("group", "supergroup", "channel"):
        await update.message.reply_text(
            "ℹ️ Bu bot shaxsiy murojaat uchun mo'ljallangan.\n\n"
            "Anonim murojaat yuborish uchun bevosita botga yozing:\n"
            "@IntegrityBot"
        )
        return MAIN_MENU

    allowed, retry_after = await check_rate_limit(user.id, "start")
    if not allowed:
        await update.message.reply_text(
            f"⏳ Juda ko'p so'rov. {retry_after} soniyadan keyin urinib ko'ring."
        )
        return MAIN_MENU

    context.user_data.clear()

    # DB dan foydalanuvchi tilini o'qi (yoki yangi yozuv yarat)
    is_new_user = False
    try:
        from datetime import timedelta
        bot_user = await get_or_create_bot_user(user.id)
        lang = bot_user.lang
        # Yangi foydalanuvchi: first_seen va last_active orasidagi farq 5 soniyadan kam
        time_diff = abs((bot_user.last_active - bot_user.first_seen).total_seconds())
        is_new_user = time_diff < 5
    except Exception as e:
        logger.warning(f"BotUser DB xatosi (start): {e}")
        lang = get_user_lang(context)

    # context ga ham set qilamiz
    set_user_lang(context, lang)

    # Persistent menyu
    await update.message.reply_text(
        "👇 Quyidagi tugmalardan foydalaning:",
        reply_markup=get_persistent_menu(lang),
    )

    # Yangi vs qaytib kelgan foydalanuvchi uchun farqli xabar
    welcome_key = "welcome_new" if is_new_user else "welcome_returning"
    await update.message.reply_text(
        t(welcome_key, lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(lang),
    )
    return MAIN_MENU


# ─── /help ───────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam sahifasini ko'rsatish"""
    lang = get_user_lang(context)
    await update.message.reply_text(
        t("help", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t("btn_home", lang), callback_data="home")
        ]])
    )
    return MAIN_MENU


# ─── Main menu callback ───────────────────────────────────────────────────────

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    if query.data == "report":
        await query.edit_message_text(
            t("choose_category", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_category_keyboard(lang)
        )
        return CHOOSE_CATEGORY

    elif query.data == "check_status":
        await query.edit_message_text(
            t("enter_case_id", lang),
            parse_mode=ParseMode.MARKDOWN
        )
        return CHECK_STATUS

    elif query.data == "followup_prompt":
        await query.edit_message_text(
            t("enter_case_id", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("cancel_btn", lang), callback_data="home")
            ]])
        )
        context.user_data["followup_mode"] = "from_menu"
        return CHECK_STATUS

    elif query.data.startswith("followup_"):
        case_external_id = query.data.replace("followup_", "")
        context.user_data["followup_case_id"] = case_external_id
        await query.edit_message_text(
            f"💬 *Murojaat {case_external_id} bo'yicha xabar yozing:*\n\n"
            "Adminga qo'shimcha ma'lumot, tushuntirish yoki savolingizni yuboring.\n\n"
            "_Bekor qilish uchun /cancel yozing_",
            parse_mode=ParseMode.MARKDOWN
        )
        return FOLLOWUP_ENTER

    elif query.data == "faq":
        faq_text = """
❓ *Ko'p so'raladigan savollar*

*Mening shaxsiyatim oshkor bo'ladimi?*
Yo'q. Siz anonim yuborishni tanlasangiz, botimiz hech qanday shaxsiy ma'lumot saqlamaydi.

*Murojaat qancha vaqtda ko'rib chiqiladi?*
• 🔴 Kritik: 24 soat ichida
• 🟠 Yuqori: 72 soat ichida
• 🟡 O'rta: 7 kun ichida
• 🟢 Past: 30 kun ichida

*Fayl yuborishim mumkinmi?*
Ha, rasm va hujjatlar (20 MB gacha) yuborishingiz mumkin.

*Murojaat holatini qanday bilaman?*
Murojaat ID raqamingizni bosh menyudan "Holat tekshirish" orqali kiriting.

*Adminga qo'shimcha ma'lumot yuborishim mumkinmi?*
Ha! "Adminga javob yozish" tugmasi orqali yoki status tekshirishda "Javob yozish" tugmasini bosing.

*Nechta fayl biriktirish mumkin?*
Bitta murojaat uchun 5 tagacha fayl (har biri 20 MB gacha).
        """
        await query.edit_message_text(
            faq_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
            ]])
        )
        return MAIN_MENU

    elif query.data == "contacts":
        await query.edit_message_text(
            "📞 *Compliance Departamenti*\n\n"
            "📧 Email: compliance@company.uz\n"
            "📱 Telefon: +998 XX XXX XX XX\n\n"
            "🕐 Ish vaqti: Du-Ju, 09:00-18:00\n\n"
            "_Shoshilinch holatlarda 24/7 ushbu bot orqali murojaat qiling._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
            ]])
        )
        return MAIN_MENU

    elif query.data == "choose_language":
        await query.answer()
        lang = get_user_lang(context)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            t("choose_language", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_language_keyboard(),
        )
        return MAIN_MENU

    elif query.data == "home":
        await query.edit_message_text(
            t("welcome", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(lang)
        )
        return MAIN_MENU

    elif query.data.startswith("mycase_"):
        case_external_id = query.data.replace("mycase_", "")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Case).where(Case.external_id == case_external_id))
            case = result.scalar_one_or_none()

        if not case:
            await query.edit_message_text(
                "❌ Murojaat topilmadi.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
                ]])
            )
            return MAIN_MENU

        status_emoji = {
            CaseStatus.NEW: "🆕", CaseStatus.IN_PROGRESS: "🔄",
            CaseStatus.NEEDS_INFO: "❓", CaseStatus.COMPLETED: "✅",
            CaseStatus.REJECTED: "❌", CaseStatus.ARCHIVED: "📦"
        }
        status_text = {
            CaseStatus.NEW: "Yangi",
            CaseStatus.IN_PROGRESS: "Ko'rib chiqilmoqda",
            CaseStatus.NEEDS_INFO: "Qo'shimcha ma'lumot kerak",
            CaseStatus.COMPLETED: "Yakunlandi",
            CaseStatus.REJECTED: "Rad etildi",
            CaseStatus.ARCHIVED: "Arxivlandi",
        }
        priority_text = {
            CasePriority.CRITICAL: "🔴 Kritik",
            CasePriority.HIGH: "🟠 Yuqori",
            CasePriority.MEDIUM: "🟡 O'rta",
            CasePriority.LOW: "🟢 Past",
        }

        detail = (
            f"📋 *Murojaat: `{case.external_id}`*\n\n"
            f"*Holat:* {status_emoji.get(case.status,'•')} {status_text.get(case.status, case.status.value)}\n"
            f"*Ustuvorlik:* {priority_text.get(case.priority, case.priority.value)}\n"
            f"*Kategoriya:* {case.category.value}\n"
            f"*Yuborilgan:* {case.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        if case.due_at:
            detail += f"*Muddat:* {case.due_at.strftime('%d.%m.%Y')}\n"

        keyboard = []
        if case.status in (CaseStatus.NEEDS_INFO, CaseStatus.IN_PROGRESS):
            keyboard.append([InlineKeyboardButton(
                "💬 Javob yozish",
                callback_data=f"followup_{case.external_id}"
            )])
        keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="back_mycases")])
        keyboard.append([InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")])

        await query.edit_message_text(
            detail,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return MAIN_MENU

    elif query.data == "back_mycases":
        # Mening murojaatlarimga qaytish (callback versiyasi)
        user_id = query.from_user.id
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Case)
                .where(Case.telegram_chat_id == user_id)
                .order_by(Case.created_at.desc())
                .limit(10)
            )
            cases = result.scalars().all()

        status_emoji = {
            CaseStatus.NEW: "🆕", CaseStatus.IN_PROGRESS: "🔄",
            CaseStatus.NEEDS_INFO: "❓", CaseStatus.COMPLETED: "✅",
            CaseStatus.REJECTED: "❌", CaseStatus.ARCHIVED: "📦",
        }
        buttons = []
        for c in cases:
            emoji = status_emoji.get(c.status, "•")
            date  = c.created_at.strftime("%d.%m.%y")
            buttons.append([InlineKeyboardButton(
                f"{emoji} {c.external_id} · {date}",
                callback_data=f"mycase_{c.external_id}"
            )])
        buttons.append([InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")])

        await query.edit_message_text(
            "📂 *Mening murojaatlarim* (so'nggi 10 ta):\n\nKo'rish uchun bosing:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return MAIN_MENU


# ─── Category selection ───────────────────────────────────────────────────────

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    if query.data == "cancel":
        await query.edit_message_text(
            t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(lang)
        )
        return MAIN_MENU

    if query.data.startswith("cat_"):
        idx = int(query.data.split("_")[1])
        cat_name = list(CATEGORY_MAP.keys())[idx]
        category = CATEGORY_MAP[cat_name]
        context.user_data["category"] = category
        context.user_data["category_name"] = cat_name

        await query.edit_message_text(
            f"✅ Kategoriya: *{cat_name}*\n\n"
            "📝 *Iltimos, muammo haqida batafsil yozing:*\n\n"
            "Quyidagilarni ko'rsating:\n"
            "• Kim, nima, qachon, qayerda\n"
            "• Dalillar (agar bo'lsa)\n"
            "• Qo'shimcha ma'lumotlar\n\n"
            "_Matnni quyida yozing (kamida 20 belgi):_",
            parse_mode=ParseMode.MARKDOWN
        )
        return ENTER_DESCRIPTION


# ─── Description ─────────────────────────────────────────────────────────────

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(context)
    allowed, retry_after = await check_rate_limit(user.id, "report")
    if not allowed:
        minutes = retry_after // 60
        time_str = f"{minutes} daqiqa" if minutes > 0 else f"{retry_after} soniya"
        await update.message.reply_text(
            f"⏳ Juda ko'p urinish. {time_str}dan keyin urinib ko'ring."
        )
        return ENTER_DESCRIPTION

    text = update.message.text
    if len(text) < 20:
        await update.message.reply_text(
            t("text_too_short", lang, length=len(text)),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ENTER_DESCRIPTION

    if len(text) > 5000:
        await update.message.reply_text(
            t("text_too_long", lang, length=len(text)),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ENTER_DESCRIPTION

    context.user_data["description"] = text
    context.user_data.setdefault("attachments", [])

    await update.message.reply_text(
        "📎 *Fayl yoki rasm biriktirmoqchimisiz?*\n\n"
        "Rasm yoki hujjat yuboring (20 MB gacha, maksimal 5 ta).\n"
        "Yoki davom etish uchun tugmani bosing.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ Fayl qo'shmasdan davom etish", callback_data="skip_attachment")]
        ])
    )
    return ADD_ATTACHMENT


# ─── Attachment ───────────────────────────────────────────────────────────────

async def add_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Rate limiting — fayl yuklash
    user = update.effective_user
    allowed, retry_after = await check_rate_limit(user.id, "file_upload")
    if not allowed:
        await update.message.reply_text(
            f"⏳ Juda ko'p fayl yuklandi. {retry_after} soniyadan keyin urinib ko'ring."
        )
        return ADD_ATTACHMENT

    attachments = context.user_data.setdefault("attachments", [])

    if len(attachments) >= 5:
        await update.message.reply_text(
            "⚠️ Maksimal 5 ta fayl biriktirish mumkin.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➡️ Davom etish", callback_data="skip_attachment")]
            ])
        )
        return ADD_ATTACHMENT

    if update.message.document:
        doc = update.message.document
        # Block executable files
        blocked_exts = [".exe", ".bat", ".sh", ".ps1", ".cmd", ".vbs", ".msi", ".dll"]
        if any(doc.file_name.lower().endswith(ext) for ext in blocked_exts):
            await update.message.reply_text(
                "❌ Bu turdagi fayl qabul qilinmaydi (.exe, .bat va boshqalar).\n"
                "Rasm, PDF, Word, Excel fayllarini yuboring."
            )
            return ADD_ATTACHMENT
        if doc.file_size > 20 * 1024 * 1024:
            await update.message.reply_text("❌ Fayl hajmi 20 MB dan oshmasligi kerak.")
            return ADD_ATTACHMENT
        attachments.append({
            "file_id": doc.file_id,
            "filename": doc.file_name,
            "mime_type": doc.mime_type or "application/octet-stream",
        })
    elif update.message.photo:
        photo = update.message.photo[-1]
        attachments.append({
            "file_id": photo.file_id,
            "filename": f"photo_{len(attachments)+1}.jpg",
            "mime_type": "image/jpeg",
        })

    count = len(attachments)
    remaining = 5 - count
    more_msg = f"Yana {remaining} ta fayl qo'shishingiz mumkin." if remaining > 0 else "Maksimal songa yetdingiz."
    await update.message.reply_text(
        f"✅ Fayl qo'shildi ({count}/5)\n\n{more_msg}\n"
        "Davom etish uchun tugmani bosing.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ Davom etish", callback_data="skip_attachment")]
        ])
    )
    return ADD_ATTACHMENT


async def skip_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔒 *Anonimlik sozlamalari*\n\n"
        "Murojaat anonim yuborilsin?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ha, anonim yuborish", callback_data="anon_yes")],
            [InlineKeyboardButton("👤 Yo'q, ma'lumotlarimni qoldirmoqchiman", callback_data="anon_no")],
        ])
    )
    return CHOOSE_ANONYMOUS


# ─── Anonymity choice ─────────────────────────────────────────────────────────

async def choose_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["is_anonymous"] = query.data == "anon_yes"

    cat = context.user_data.get("category_name", "Noma'lum")
    desc = context.user_data.get("description", "")
    att_count = len(context.user_data.get("attachments", []))
    is_anon = context.user_data["is_anonymous"]

    summary = (
        f"📋 *Murojaat xulosasi*\n\n"
        f"*Kategoriya:* {cat}\n"
        f"*Anonimlik:* {'✅ Anonim' if is_anon else '❌ Anonim emas'}\n"
        f"*Fayllar:* {att_count} ta\n\n"
        f"*Tavsif:*\n_{desc[:300]}{'...' if len(desc) > 300 else ''}_\n\n"
        "Ushbu ma'lumotlar to'g'rimi?"
    )
    await query.edit_message_text(
        summary,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Tasdiqlash va yuborish", callback_data="confirm_send")],
            [InlineKeyboardButton("✏️ Qayta tahrirlash", callback_data="edit_restart")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_all")],
        ])
    )
    return CONFIRM


# ─── Confirm & save ───────────────────────────────────────────────────────────

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    if query.data == "cancel_all":
        context.user_data.clear()
        await query.edit_message_text(
            t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(lang)
        )
        return MAIN_MENU

    if query.data == "edit_restart":
        await query.edit_message_text(
            CATEGORY_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=get_category_keyboard()
        )
        return CHOOSE_CATEGORY

    # Rate limiting — murojaat yuborish uchun
    user = update.effective_user
    allowed, retry_after = await check_rate_limit(user.id, "report")
    if not allowed:
        minutes = retry_after // 60
        time_str = f"{minutes} daqiqa" if minutes > 0 else f"{retry_after} soniya"
        await query.edit_message_text(
            f"⏳ *Juda ko'p murojaat yuborildi.*\n\n"
            f"{time_str}dan keyin urinib ko'ring.\n"
            f"_Limit: 5 ta murojaat / 5 daqiqa_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return MAIN_MENU

    await query.edit_message_text("⏳ Murojaat saqlanmoqda...")

    try:
        async with AsyncSessionLocal() as db:
            case_id = await generate_case_id()
            reporter_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(reporter_token.encode()).hexdigest()

            category = context.user_data["category"]
            description = context.user_data["description"]
            is_anonymous = context.user_data["is_anonymous"]

            case = Case(
                external_id=case_id,
                reporter_token=token_hash,
                telegram_chat_id=update.effective_user.id,
                is_anonymous=is_anonymous,
                category=category,
                priority=PRIORITY_BY_CATEGORY.get(category, CasePriority.MEDIUM),
                status=CaseStatus.NEW,
                description_encrypted=encrypt_case_content(description),
                title=f"{description[:100]}..." if len(description) > 100 else description,
            )
            db.add(case)
            await db.flush()

            # Save attachments
            for att_data in context.user_data.get("attachments", []):
                try:
                    path, checksum, size = await save_telegram_file(
                        context.bot, att_data["file_id"],
                        att_data["filename"], str(case.id)
                    )
                    db.add(CaseAttachment(
                        case_id=case.id,
                        filename=path.split("/")[-1],
                        original_filename=att_data["filename"],
                        storage_path=path,
                        mime_type=att_data["mime_type"],
                        size_bytes=size,
                        checksum=checksum,
                    ))
                except Exception as e:
                    logger.error(f"Failed to save attachment: {e}")

            await db.commit()
            await notify_admins(context.bot, case_id, category, description, is_anonymous)

            # Real-time WebSocket notification to admin panel
            try:
                import redis.asyncio as aioredis
                from app.services.websocket_manager import publish_notification
                r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await publish_notification(r, "new_case", {
                    "case_id": case_id,
                    "category": category.value if hasattr(category, "value") else str(category),
                    "priority": PRIORITY_BY_CATEGORY.get(category, CasePriority.MEDIUM).value,
                    "is_anonymous": is_anonymous,
                    "message": f"Yangi murojaat: {case_id}",
                })
                await r.aclose()
            except Exception as e:
                logger.warning(f"WS notify failed: {e}")

            # SIEM: yangi murojaat hodisasi
            try:
                from app.services.siem import siem_service
                await siem_service.send_case_event(
                    action="CREATED",
                    case_id=case_id,
                    category=category.value if hasattr(category, "value") else str(category),
                    priority=PRIORITY_BY_CATEGORY.get(category, CasePriority.MEDIUM).value,
                    is_anonymous=is_anonymous,
                )
            except Exception as e:
                logger.debug(f"SIEM case event xatosi: {e}")

            # Jira / Redmine tiket yaratish (kritik/yuqori prioritylar uchun)
            try:
                from app.services.jira_integration import ticket_service
                ticket_result = await ticket_service.create_ticket_for_case(
                    case_id=case_id,
                    category=category.value if hasattr(category, "value") else str(category),
                    priority=PRIORITY_BY_CATEGORY.get(category, CasePriority.MEDIUM).value,
                    description=description,
                    is_anonymous=is_anonymous,
                )
                if ticket_result.created:
                    logger.info(
                        f"Tiket yaratildi [{ticket_result.system}]: "
                        f"{ticket_result.ticket_id} → {case_id}"
                    )
                    # Tiket ID ni case ga saqlash
                    async with AsyncSessionLocal() as db2:
                        from sqlalchemy import select as _select
                        result = await db2.execute(_select(Case).where(Case.external_id == case_id))
                        saved_case = result.scalar_one_or_none()
                        if saved_case:
                            saved_case.jira_ticket_id = ticket_result.ticket_id
                            saved_case.jira_ticket_url = ticket_result.url
                            await db2.commit()
                elif ticket_result.skipped:
                    logger.debug(f"Tiket o'tkazildi ({case_id}): {ticket_result.skip_reason}")
            except Exception as e:
                logger.warning(f"Tiket yaratishda xato ({case_id}): {e}")

        lang = get_user_lang(context)
        success_text = t(
            "case_submitted", lang,
            case_id=case_id,
            token=reporter_token,
        )
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("btn_home", lang), callback_data="home")
            ]])
        )
    except Exception as e:
        logger.error(f"Error saving case: {e}")
        lang = get_user_lang(context)
        await query.edit_message_text(
            t("error_generic", lang),
            reply_markup=get_main_keyboard(lang)
        )

    context.user_data.clear()
    return MAIN_MENU


# ─── Check status ─────────────────────────────────────────────────────────────

async def check_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Rate limiting
    user = update.effective_user
    allowed, retry_after = await check_rate_limit(user.id, "check_status")
    if not allowed:
        await update.message.reply_text(
            f"⏳ Juda ko'p so'rov. {retry_after} soniyadan keyin urinib ko'ring."
        )
        return CHECK_STATUS

    text = update.message.text.strip().upper()

    if not re.match(r"CASE-\d{8}-\d{5}", text):
        await update.message.reply_text(
            "⚠️ Noto'g'ri format. Masalan: `CASE-20251201-00001`",
            parse_mode=ParseMode.MARKDOWN
        )
        return CHECK_STATUS

    # Agar followup_mode bo'lsa — bu murojaat ID ni followup uchun ishlatamiz
    if context.user_data.get("followup_mode") == "from_menu":
        context.user_data.pop("followup_mode", None)
        # Ish mavjudligini tekshiramiz
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Case).where(Case.external_id == text))
            case = result.scalar_one_or_none()

        if not case:
            await update.message.reply_text(
                "❌ Murojaat topilmadi. Raqamni to'g'ri kiritganingizni tekshiring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
                ]])
            )
            return MAIN_MENU

        # Murojaat topildi — followup ga o'tish
        context.user_data["followup_case_id"] = text
        await update.message.reply_text(
            f"💬 *Murojaat {text} bo'yicha xabar yozing:*\n\n"
            "Adminga qo'shimcha ma'lumot, tushuntirish yoki savolingizni yuboring.\n\n"
            "_Bekor qilish uchun /cancel yozing_",
            parse_mode=ParseMode.MARKDOWN
        )
        return FOLLOWUP_ENTER

    # Oddiy status tekshirish
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Case).where(Case.external_id == text))
        case = result.scalar_one_or_none()

    if not case:
        await update.message.reply_text(
            "❌ Murojaat topilmadi. Raqamni to'g'ri kiritganingizni tekshiring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
            ]])
        )
        return MAIN_MENU

    status_emoji = {
        CaseStatus.NEW: "🆕", CaseStatus.IN_PROGRESS: "🔄",
        CaseStatus.NEEDS_INFO: "❓", CaseStatus.COMPLETED: "✅",
        CaseStatus.REJECTED: "❌", CaseStatus.ARCHIVED: "📦"
    }
    status_text = {
        CaseStatus.NEW: "Yangi — ko'rib chiqilishini kuting",
        CaseStatus.IN_PROGRESS: "Ko'rib chiqilmoqda",
        CaseStatus.NEEDS_INFO: "Qo'shimcha ma'lumot kerak",
        CaseStatus.COMPLETED: "Yakunlandi",
        CaseStatus.REJECTED: "Rad etildi",
        CaseStatus.ARCHIVED: "Arxivlandi"
    }

    reply = (
        f"📋 *Murojaat holati*\n\n"
        f"*Raqam:* `{case.external_id}`\n"
        f"*Holat:* {status_emoji.get(case.status, '❔')} {status_text.get(case.status, case.status.value)}\n"
        f"*Kategoriya:* {case.category.value}\n"
        f"*Sana:* {case.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    if case.due_at:
        reply += f"*Muddat:* {case.due_at.strftime('%d.%m.%Y')}\n"

    keyboard = [[InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")]]

    # "Needs info" yoki "In progress" bo'lsa — javob tugmasini ko'rsatish
    if case.status in (CaseStatus.NEEDS_INFO, CaseStatus.IN_PROGRESS):
        keyboard.insert(0, [InlineKeyboardButton(
            "💬 Adminga javob yozish",
            callback_data=f"followup_{case.external_id}"
        )])

    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU


# ─── Follow-up: reporter → admin ─────────────────────────────────────────────

async def followup_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Reporter tomonidan adminга jo'natilayotgan qo'shimcha xabar.
    FOLLOWUP_ENTER holatida ishlaydi.
    """
    # Rate limiting
    user = update.effective_user
    allowed, retry_after = await check_rate_limit(user.id, "followup")
    if not allowed:
        await update.message.reply_text(
            f"⏳ Juda ko'p xabar yuborildi. {retry_after} soniyadan keyin urinib ko'ring."
        )
        return FOLLOWUP_ENTER

    text = update.message.text.strip()
    case_external_id = context.user_data.get("followup_case_id")

    if not case_external_id:
        await update.message.reply_text(
            "❌ Xatolik: murojaat ID si topilmadi. Qaytadan urinib ko'ring.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return MAIN_MENU

    if len(text) < 5:
        await update.message.reply_text("⚠️ Xabar juda qisqa. Iltimos, batafsil yozing.")
        return FOLLOWUP_ENTER

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Case).where(Case.external_id == case_external_id))
            case = result.scalar_one_or_none()

            if not case:
                await update.message.reply_text(
                    "❌ Murojaat topilmadi.",
                    reply_markup=get_main_keyboard()
                )
                context.user_data.clear()
                return MAIN_MENU

            # CaseComment sifatida saqlash (reporter tomonidan)
            comment = CaseComment(
                case_id=case.id,
                author_id=None,          # reporter — tashqi foydalanuvchi
                is_from_reporter=True,
                is_internal=False,
                content_encrypted=encrypt_comment_content(
                    f"[Reporter xabari]\n{text}"
                ),
            )
            db.add(comment)
            await db.commit()

        # Adminlarga bildirishnoma
        try:
            admin_msg = (
                f"💬 *Reporter dan yangi xabar*\n\n"
                f"📋 *Murojaat:* `{case_external_id}`\n"
                f"📝 *Xabar:*\n_{text[:500]}{'...' if len(text) > 500 else ''}_\n\n"
                f"👉 Admin panelda ko'ring"
            )
            await context.bot.send_message(
                chat_id=settings.ADMIN_CHAT_ID,
                text=admin_msg,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"Could not notify admin about followup: {e}")

        await update.message.reply_text(
            f"✅ *Xabaringiz yuborildi!*\n\n"
            f"Murojaat: `{case_external_id}`\n\n"
            f"Compliance departamenti javob bilan siz bilan bog'lanadi.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
            ]])
        )

    except Exception as e:
        logger.error(f"Followup save error: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=get_main_keyboard()
        )

    context.user_data.clear()
    return MAIN_MENU


# ─── Persistent menu reply keyboard handler ───────────────────────────────────

async def reply_keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pastdagi doimiy tugmalar bosilganda ishga tushadi"""
    text = update.message.text
    lang = get_user_lang(context)

    # Barcha tillardagi tugma matnlari bilan solishtirish
    from app.bot.i18n import SUPPORTED_LANGS, t as _t

    def matches(key: str) -> bool:
        return any(text == _t(key, l) for l in SUPPORTED_LANGS)

    if matches("menu_submit"):
        context.user_data.clear()
        await update.message.reply_text(
            _t("choose_category", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_category_keyboard(lang),
        )
        return CHOOSE_CATEGORY

    elif matches("menu_check_status"):
        await update.message.reply_text(
            _t("enter_case_id", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_t("cancel_btn", lang), callback_data="home")
            ]]),
        )
        return CHECK_STATUS

    elif matches("menu_reply_admin"):
        await update.message.reply_text(
            _t("followup_enter_id", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_t("cancel_btn", lang), callback_data="home")
            ]]),
        )
        context.user_data["followup_mode"] = "from_menu"
        return CHECK_STATUS

    elif matches("menu_my_cases"):
        return await my_cases_handler(update, context)

    elif matches("menu_help"):
        await update.message.reply_text(
            _t("help", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_t("btn_home", lang), callback_data="home")
            ]]),
        )
        return MAIN_MENU

    elif matches("menu_settings"):
        await update.message.reply_text(
            _t("settings_info", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_t("btn_home", lang), callback_data="home"),
                InlineKeyboardButton(_t("btn_language", lang), callback_data="choose_language"),
            ]]),
        )
        return MAIN_MENU

    # Noma'lum matn — bosh menyuga qaytaramiz
    await update.message.reply_text(
        _t("welcome", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(lang),
    )
    return MAIN_MENU


async def my_cases_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining barcha murojaatlarini ko'rsatish"""
    user = update.effective_user
    allowed, retry_after = await check_rate_limit(user.id, "check_status")
    if not allowed:
        await update.message.reply_text(
            f"⏳ Juda ko'p so'rov. {retry_after} soniyadan keyin urinib ko'ring."
        )
        return

    user_id = user.id

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Case)
            .where(Case.telegram_chat_id == user_id)
            .order_by(Case.created_at.desc())
            .limit(10)
        )
        cases = result.scalars().all()

    if not cases:
        await update.message.reply_text(
            "📭 *Sizda hali murojaatlar yo'q.*\n\n"
            "Murojaat yuborish uchun «📝 Murojaat yuborish» tugmasini bosing.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Murojaat yuborish", callback_data="report")
            ]]),
        )
        return MAIN_MENU

    status_emoji = {
        CaseStatus.NEW: "🆕",
        CaseStatus.IN_PROGRESS: "🔄",
        CaseStatus.NEEDS_INFO: "❓",
        CaseStatus.COMPLETED: "✅",
        CaseStatus.REJECTED: "❌",
        CaseStatus.ARCHIVED: "📦",
    }

    buttons = []
    for case in cases:
        emoji  = status_emoji.get(case.status, "•")
        date   = case.created_at.strftime("%d.%m.%y")
        label  = f"{emoji} {case.external_id} · {date}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"mycase_{case.external_id}")])

    buttons.append([InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")])

    await update.message.reply_text(
        "📂 *Mening murojaatlarim* (so'nggi 10 ta):\n\n"
        "Ko'rish uchun bosing:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return MAIN_MENU


# ─── Cancel ───────────────────────────────────────────────────────────────────

# ─── Universal fallback handler ──────────────────────────────────────────────

async def universal_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ConversationHandler tashqarisidan yoki tushunilmagan xabar kelganda ishlaydigan fallback.
    - Guruh/kanal xabarlari → jim o'tkazib yuborish
    - Shaxsiy chat → bosh menyu ko'rsatish
    """
    if not update.message:
        return MAIN_MENU

    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup", "channel"):
        return  # Guruhda hech narsa qilmaymiz

    user = update.effective_user
    # Rate limit tekshiruvi (start limiti ishlatiladi)
    allowed, retry_after = await check_rate_limit(user.id, "start")
    if not allowed:
        await update.message.reply_text(
            f"⏳ {retry_after} soniyadan keyin urinib ko'ring."
        )
        return MAIN_MENU

    lang = get_user_lang(context)
    await update.message.reply_text(
        t("unknown_command", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(lang),
    )
    return MAIN_MENU


# ─── State-specific invalid input handlers ────────────────────────────────────

async def invalid_category_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CHOOSE_CATEGORY state da matn (yoki noto'g'ri narsa) kelsa."""
    if not update.message:
        return CHOOSE_CATEGORY
    lang = get_user_lang(context)
    await update.message.reply_text(
        t("choose_category_invalid", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_category_keyboard(lang),
    )
    return CHOOSE_CATEGORY


async def invalid_description_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ENTER_DESCRIPTION state da matn emas narsa (sticker, location, va h.k.) kelsa."""
    if not update.message:
        return ENTER_DESCRIPTION
    lang = get_user_lang(context)
    await update.message.reply_text(
        "✍️ " + t("text_too_short", lang, length=0).split("(")[0].strip() +
        "\n\nIltimos, murojaat matnini yozing (kamida 20 belgi).",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ENTER_DESCRIPTION


async def invalid_confirm_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CONFIRM state da noto'g'ri xabar kelsa."""
    if not update.message:
        return CONFIRM
    lang = get_user_lang(context)
    await update.message.reply_text(
        t("invalid_input_in_state", lang),
        parse_mode=ParseMode.MARKDOWN,
    )
    return CONFIRM


# ─── Global error handler ─────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Barcha xatolarni ushlaydi.
    - Stack trace HECH QACHON foydalanuvchiga yuborilmaydi
    - Faqat loglarga yoziladi
    - Foydalanuvchiga umumiy xato xabari yuboriladi
    """
    logger.error("Exception while handling update:", exc_info=context.error)

    # Update mavjud va xabar yoki callback bo'lsa
    if not isinstance(update, Update):
        return

    try:
        lang = "uz"
        if update.effective_user and hasattr(context, "user_data"):
            lang = context.user_data.get("lang", "uz") if context.user_data else "uz"

        error_text = t("technical_error", lang)

        if update.message:
            await update.message.reply_text(
                error_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif update.callback_query:
            try:
                await update.callback_query.answer(
                    "😔 Texnik xato yuz berdi. /start bosing.",
                    show_alert=True,
                )
            except Exception:
                pass
            try:
                await update.callback_query.message.reply_text(
                    error_text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error in error_handler itself: {e}")


# ─── /cancel ─────────────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context)
    context.user_data.clear()
    await update.message.reply_text(
        t("cancelled", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(lang)
    )
    return MAIN_MENU


# ─── /lang — Til tanlash ─────────────────────────────────────────────────────

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/lang buyrug'i — til tanlash menyusini ko'rsatadi."""
    await update.message.reply_text(
        t("choose_language", get_user_lang(context)),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_language_keyboard(),
    )
    return MAIN_MENU


async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """lang_{code} callback — tilni o'zgartiradi va DB ga yozadi."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.replace("lang_", "")
    if lang_code not in SUPPORTED_LANGS:
        lang_code = "uz"

    # context ga saqlash
    set_user_lang(context, lang_code)

    # DB ga yozish
    try:
        await update_bot_user_lang(query.from_user.id, lang_code)
    except Exception as e:
        logger.warning(f"BotUser lang DB yozish xatosi: {e}")

    await query.edit_message_text(
        t("language_changed", lang_code),
        parse_mode=ParseMode.MARKDOWN,
    )
    # Persistent menyu tugmalarini yangi tilda yangilash
    await query.message.reply_text(
        t("welcome", lang_code),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_persistent_menu(lang_code),
    )
    await query.message.reply_text(
        t("welcome", lang_code),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(lang_code),
    )
    return MAIN_MENU


# ─── Helper: get chat id ─────────────────────────────────────────────────────

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin guruh ID sini olish uchun helper command"""
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"ℹ️ *Chat ma'lumotlari*\n\n"
        f"Chat ID: `{chat.id}`\n"
        f"Chat turi: `{chat.type}`\n"
        f"Sizning ID: `{user.id}`\n\n"
        f"_Admin guruh uchun shu Chat ID ni .env faylidagi ADMIN\\_CHAT\\_ID ga qo'ying_",
        parse_mode=ParseMode.MARKDOWN
    )


# ─── Reminder scheduler ───────────────────────────────────────────────────────

async def send_pending_reminders(context: ContextTypes.DEFAULT_TYPE):
    """
    Har kuni ishga tushadigan scheduler.
    Javob kutayotgan (NEEDS_INFO) holati uchun 3 kundan keyin eslatma yuboradi.
    Yangi (NEW) holat uchun 7 kundan keyin eslatma yuboradi.
    """
    now = datetime.now(timezone.utc)
    reminders_sent = 0

    try:
        async with AsyncSessionLocal() as db:
            # 1. NEEDS_INFO → 3 kun o'tgan, reporter hali javob bermagan
            needs_info_cutoff = now - timedelta(days=3)
            result = await db.execute(
                select(Case).where(
                    and_(
                        Case.status == CaseStatus.NEEDS_INFO,
                        Case.updated_at <= needs_info_cutoff,
                        Case.telegram_chat_id.isnot(None),
                    )
                )
            )
            needs_info_cases = result.scalars().all()

            for case in needs_info_cases:
                try:
                    await context.bot.send_message(
                        chat_id=case.telegram_chat_id,
                        text=(
                            f"🔔 *Eslatma — Murojaat {case.external_id}*\n\n"
                            f"Compliance departamenti sizdan qo'shimcha ma'lumot kutmoqda.\n\n"
                            f"Javob yuborish uchun:\n"
                            f"1️⃣ Bosh menyuga o'ting\n"
                            f"2️⃣ «Adminga javob yozish» ni bosing\n"
                            f"3️⃣ Murojaat raqamingizni kiriting: `{case.external_id}`\n\n"
                            f"_Agar javob 7 kun ichida kelmasa, murojaat yopilishi mumkin._"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("✍️ Javob yozish", callback_data=f"followup_{case.external_id}")
                        ]])
                    )
                    reminders_sent += 1
                    logger.info(f"Reminder sent for NEEDS_INFO case {case.external_id}")
                except Exception as e:
                    logger.warning(f"Could not send reminder to {case.telegram_chat_id}: {e}")

            # 2. NEW holatdagi ish 7 kun qimirlamagan bo'lsa — reporterga holat xabari
            new_cutoff = now - timedelta(days=7)
            result2 = await db.execute(
                select(Case).where(
                    and_(
                        Case.status == CaseStatus.NEW,
                        Case.created_at <= new_cutoff,
                        Case.telegram_chat_id.isnot(None),
                    )
                )
            )
            new_cases = result2.scalars().all()

            for case in new_cases:
                try:
                    await context.bot.send_message(
                        chat_id=case.telegram_chat_id,
                        text=(
                            f"📬 *Murojaat {case.external_id} haqida yangilik*\n\n"
                            f"Murojaatingiz hali ko'rib chiqilmoqda. "
                            f"Compliance departamenti tez orada siz bilan bog'lanadi.\n\n"
                            f"*Holat:* 🆕 Yangi\n"
                            f"*Yuborilgan:* {case.created_at.strftime('%d.%m.%Y')}"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    reminders_sent += 1
                    logger.info(f"Status reminder sent for NEW case {case.external_id}")
                except Exception as e:
                    logger.warning(f"Could not send NEW reminder to {case.telegram_chat_id}: {e}")

    except Exception as e:
        logger.error(f"Reminder scheduler error: {e}")

    if reminders_sent:
        logger.info(f"Reminder job completed: {reminders_sent} reminders sent")


# ─── Build application ────────────────────────────────────────────────────────

async def handle_poll_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram anonymous poll natijasi o'zgarganda chaqiriladi (kanal poll'lari).
    `poll` update turi — poll.options ichida yangilangan voter_count bor.
    """
    poll = update.poll
    if not poll:
        return

    tg_poll_id = poll.id
    logger.info(f"POLL_UPDATE received: tg_poll_id={tg_poll_id}, total_voters={poll.total_voter_count}")

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            result = await db.execute(
                select(PollQuestion).where(PollQuestion.telegram_poll_id == tg_poll_id)
            )
            question = result.scalar_one_or_none()
            if not question:
                logger.warning(f"POLL_UPDATE: no question found for telegram_poll_id={tg_poll_id}")
                return

            logger.info(f"POLL_UPDATE: matched question_id={question.id}")

            # poll.options da har bir variant uchun voter_count bor
            opts_result = await db.execute(
                select(PollOption)
                .where(PollOption.question_id == question.id)
                .order_by(PollOption.order)
            )
            options = opts_result.scalars().all()

            for idx, tg_option in enumerate(poll.options):
                if idx < len(options):
                    options[idx].vote_count = tg_option.voter_count
                    logger.info(f"  option[{idx}]='{options[idx].option_text}' -> {tg_option.voter_count}")

            await db.commit()

            # WebSocket broadcast
            try:
                import redis.asyncio as aioredis
                from app.services.websocket_manager import publish_notification
                r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await publish_notification(r, "poll_vote", {
                    "poll_id": str(question.poll_id),
                    "question_id": str(question.id),
                    "message": "So'rovnomada yangi ovoz berildi",
                })
                await r.aclose()
            except Exception as e:
                logger.warning(f"WS poll_vote notify failed: {e}")

        except Exception as e:
            logger.error(f"handle_poll_update error: {e}")


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Foydalanuvchi Telegram native poll'da ovoz berganda chaqiriladi.
    Ovozni DB ga yozadi va WebSocket orqali admin panelga yuboradi.
    """
    poll_answer = update.poll_answer
    if not poll_answer:
        return

    tg_poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    logger.info(f"POLL_ANSWER received: tg_poll_id={tg_poll_id}, options={option_ids}")

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            result = await db.execute(
                select(PollQuestion).where(PollQuestion.telegram_poll_id == tg_poll_id)
            )
            question = result.scalar_one_or_none()
            if not question:
                logger.warning(f"POLL_ANSWER: no question found for telegram_poll_id={tg_poll_id}")
                return

            logger.info(f"POLL_ANSWER: matched question_id={question.id}, poll_id={question.poll_id}")

            opts_result = await db.execute(
                select(PollOption)
                .where(PollOption.question_id == question.id)
                .order_by(PollOption.order)
            )
            options = opts_result.scalars().all()

            for idx in option_ids:
                if 0 <= idx < len(options):
                    options[idx].vote_count += 1
                    logger.info(f"POLL_ANSWER: option[{idx}]='{options[idx].option_text}' vote_count={options[idx].vote_count}")

            await db.commit()

            # WebSocket orqali admin panelga real-time yangilanish
            try:
                import redis.asyncio as aioredis
                from app.services.websocket_manager import publish_notification
                r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await publish_notification(r, "poll_vote", {
                    "poll_id": str(question.poll_id),
                    "question_id": str(question.id),
                    "message": "So'rovnomada yangi ovoz berildi",
                })
                await r.aclose()
            except Exception as e:
                logger.warning(f"WS poll_vote notify failed: {e}")

        except Exception as e:
            logger.error(f"handle_poll_answer error: {e}")


def build_application() -> Application:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Faqat shaxsiy chat filtri — ConversationHandler entry_points uchun
    private_filter = filters.ChatType.PRIVATE


    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # /lang buyrug'i va lang_* callback — barcha state-larda ishlashi uchun
        lang_handlers = [
            CommandHandler("lang", lang_command),
            CallbackQueryHandler(lang_callback, pattern=r"^lang_(uz|ru|en)$"),
        ]

        # Persistent menyu tugmalari handler — barcha tillarda
        persistent_menu_handler = MessageHandler(
            filters.Regex(MENU_BUTTON_REGEX),
            reply_keyboard_handler,
        )

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", start),
                CommandHandler("help", help_command),
                CommandHandler("lang", lang_command),
                MessageHandler(
                    private_filter & filters.Regex(MENU_BUTTON_REGEX),
                    reply_keyboard_handler,
                ),
            ],
            states={
                MAIN_MENU: [
                    *lang_handlers,
                    CallbackQueryHandler(main_menu_callback),
                    persistent_menu_handler,
                ],
                CHOOSE_CATEGORY: [
                    *lang_handlers,
                    CallbackQueryHandler(choose_category),
                    persistent_menu_handler,
                    # State fallback: matn kelsa kategoriya klaviaturasini ko'rsat
                    MessageHandler(filters.ALL, invalid_category_input),
                ],
                ENTER_DESCRIPTION: [
                    *lang_handlers,
                    persistent_menu_handler,
                    MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description),
                    # State fallback: matn emas narsa (sticker, location, va h.k.) kelsa
                    MessageHandler(filters.ALL, invalid_description_input),
                ],
                ADD_ATTACHMENT: [
                    *lang_handlers,
                    MessageHandler(filters.Document.ALL | filters.PHOTO, add_attachment),
                    CallbackQueryHandler(skip_attachment, pattern="^skip_attachment$"),
                    persistent_menu_handler,
                ],
                CHOOSE_ANONYMOUS: [
                    *lang_handlers,
                    CallbackQueryHandler(choose_anonymous, pattern="^anon_"),
                    persistent_menu_handler,
                ],
                CONFIRM: [
                    *lang_handlers,
                    CallbackQueryHandler(confirm_send),
                    persistent_menu_handler,
                    # State fallback: noto'g'ri xabar kelsa
                    MessageHandler(filters.ALL, invalid_confirm_input),
                ],
                CHECK_STATUS: [
                    *lang_handlers,
                    persistent_menu_handler,
                    MessageHandler(filters.TEXT & ~filters.COMMAND, check_status_handler),
                ],
                FOLLOWUP_ENTER: [
                    *lang_handlers,
                    persistent_menu_handler,
                    MessageHandler(filters.TEXT & ~filters.COMMAND, followup_enter),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CommandHandler("start", start),
                CommandHandler("help", help_command),
                CommandHandler("lang", lang_command),
                CallbackQueryHandler(lang_callback, pattern=r"^lang_(uz|ru|en)$"),
                CallbackQueryHandler(main_menu_callback, pattern="^home$"),
                persistent_menu_handler,
                # Universal fallback — ENG OXIRIDA bo'lishi shart
                MessageHandler(filters.ALL, universal_fallback),
            ],
            per_user=True,
            per_chat=True,
            per_message=False,
            allow_reentry=True,
        )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("getchatid", get_chat_id))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern=r"^lang_(uz|ru|en)$"))

    # Guruhda /start uchun alohida handler (ConversationHandler tashqarisida)
    app.add_handler(CommandHandler("start", start))

    # ConversationHandler tashqarisidan kelgan barcha xabarlar uchun fallback
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.Regex(MENU_BUTTON_REGEX),
        reply_keyboard_handler,
    ))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND,
        universal_fallback,
    ))

    # Poll answer handler
    from telegram.ext import PollAnswerHandler as TGPollAnswerHandler
    from telegram.ext import PollHandler as TGPollHandler
    app.add_handler(TGPollAnswerHandler(handle_poll_answer))
    app.add_handler(TGPollHandler(handle_poll_update))

    # ✅ Global error handler — barcha xatolarni ushlaydi
    app.add_error_handler(error_handler)

    # ✅ Reminder scheduler
    if app.job_queue:
        app.job_queue.run_repeating(
            callback=send_pending_reminders,
            interval=86400,
            first=60,
            name="daily_reminders",
        )
        logger.info("Daily reminder scheduler registered ✅")
    else:
        logger.warning(
            "JobQueue not available. Install 'python-telegram-bot[job-queue]' "
            "for reminder functionality."
        )

    return app