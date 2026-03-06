import hashlib
import secrets
import warnings
from datetime import datetime, timezone, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ForceReply
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
    CasePriority, CaseStatus, PollQuestion, PollOption, PollStatus,
    User, UserRole, AuditLog, AuditAction,
)
from app.services.storage import save_telegram_file
from app.services.notification import (
    notify_admins,
    format_group_message,
    build_status_keyboard,
    update_group_message,
    ALLOWED_TRANSITIONS,
    STATUS_LABELS,
)
from app.services.bot_users import get_or_create_bot_user, update_bot_user_lang, get_bot_user_lang as db_get_user_lang
from app.bot.rate_limit import check_rate_limit, check_case_rate_limit, rate_limited
from app.bot.i18n import t, get_user_lang, set_user_lang, get_language_keyboard, SUPPORTED_LANGS
from app.bot.auth import get_admin_user, is_admin, is_investigator_or_above

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
    REJECT_REASON,
) = range(9)

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


def get_admin_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Admin uchun kengaytirilgan menyu"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📊 Statistika"), KeyboardButton("🔔 Yangi murojaatlar")],
            [KeyboardButton("⏰ Deadline yaqin"), KeyboardButton("🚨 Muddati o'tgan")],
            [KeyboardButton("📋 Mening murojaatlarim"), KeyboardButton("👥 Jamoam")],
            [KeyboardButton("⚙️ Hisobot sozlamalari"), KeyboardButton("🏠 Standart menyu")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_investigator_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Investigator uchun kengaytirilgan menyu"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📋 Mening murojaatlarim"), KeyboardButton("🔔 Yangi tayinlovlar")],
            [KeyboardButton("⏰ Deadline yaqin"), KeyboardButton("📊 Mening statistikam")],
            [KeyboardButton("🏠 Standart menyu")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# Admin menyu tugma matnlari
_ADMIN_MENU_TEXTS = {
    "📊 Statistika", "🔔 Yangi murojaatlar", "⏰ Deadline yaqin",
    "🚨 Muddati o'tgan", "📋 Mening murojaatlarim", "👥 Jamoam",
    "⚙️ Hisobot sozlamalari", "🏠 Standart menyu",
    "🔔 Yangi tayinlovlar", "📊 Mening statistikam",
}


# Barcha tillardagi persistent menu tugma matnlari (ConversationHandler Regex uchun)
_MENU_KEYS = ["menu_submit", "menu_check_status", "menu_reply_admin",
              "menu_my_cases", "menu_help", "menu_settings"]
_ALL_MENU_TEXTS = set()
for _key in _MENU_KEYS:
    for _lang in SUPPORTED_LANGS:
        _ALL_MENU_TEXTS.add(t(_key, _lang))
# Admin menyu matnlarini ham qo'shish
_ALL_MENU_TEXTS.update(_ADMIN_MENU_TEXTS)
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

    # ── Telegram bog'lash deep link: /start link_{token} ──────────────────
    args = context.args  # /start dan keyingi argument
    if args and args[0].startswith("link_"):
        token = args[0][len("link_"):]
        await _handle_telegram_link(update, context, token)
        return MAIN_MENU
    # ─────────────────────────────────────────────────────────────────────

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

    # Admin/investigator ekanligini tekshirish
    admin_user = await get_admin_user(user.id)

    # Menyu tanlash
    if admin_user and admin_user.role == UserRole.ADMIN:
        # Admin uchun kengaytirilgan menyu
        await update.message.reply_text(
            "👋 *Xush kelibsiz, Admin!*\n\n"
            "📊 Quyidagi admin tugmalardan foydalaning:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_menu(lang),
        )
        context.user_data["is_admin"] = True
        context.user_data["admin_user_id"] = str(admin_user.id)
    elif admin_user and admin_user.role == UserRole.INVESTIGATOR:
        # Investigator uchun kengaytirilgan menyu
        await update.message.reply_text(
            "👋 *Xush kelibsiz!*\n\n"
            "📋 Quyidagi tugmalardan foydalaning:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_investigator_menu(lang),
        )
        context.user_data["is_investigator"] = True
        context.user_data["admin_user_id"] = str(admin_user.id)
    else:
        # Oddiy foydalanuvchi — standart menyu
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


async def _handle_telegram_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    token: str,
):
    """Telegram account ni admin panel foydalanuvchisi bilan bog'lash."""
    tg_user = update.effective_user
    redis_key = f"tg_link:{token}"

    try:
        import redis.asyncio as aioredis
        import uuid as _uuid

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        user_id_str = await r.get(redis_key)

        if not user_id_str:
            await update.message.reply_text(
                "❌ *Havola yaroqsiz yoki muddati o'tgan.*\n\n"
                "Admin paneldan yangi havola oling.",
                parse_mode=ParseMode.MARKDOWN,
            )
            await r.aclose()
            return

        # Tokenni o'chirish — bir martalik
        await r.delete(redis_key)
        await r.aclose()

        user_uuid = _uuid.UUID(user_id_str)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_uuid))
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
                return

            # Bu telegram ID boshqa foydalanuvchida bormi — tekshirish
            existing = await db.execute(
                select(User).where(
                    User.telegram_chat_id == tg_user.id,
                    User.id != user_uuid,
                )
            )
            if existing.scalar_one_or_none():
                await update.message.reply_text(
                    "⚠️ *Bu Telegram akkaunt boshqa foydalanuvchiga bog'langan.*\n\n"
                    "Avval u yerdan uzib, qayta urinib ko'ring.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            admin_user.telegram_chat_id = tg_user.id
            db.add(AuditLog(
                user_id=admin_user.id,
                action=AuditAction.USER_UPDATE,
                entity_type="user",
                entity_id=str(admin_user.id),
                payload={
                    "action": "telegram_linked",
                    "telegram_id": tg_user.id,
                    "telegram_username": tg_user.username,
                },
            ))
            await db.commit()

        display_name = admin_user.full_name or admin_user.username
        await update.message.reply_text(
            f"✅ *Muvaffaqiyatli bog'landi!*\n\n"
            f"👤 Admin panel: *{display_name}*\n"
            f"📱 Telegram: @{tg_user.username or tg_user.first_name}\n\n"
            f"Endi admin panelidan tayinlangan murojaatlar haqida xabar olasiz.",
            parse_mode=ParseMode.MARKDOWN,
        )

    except Exception as e:
        logger.error(f"Telegram link error: {e}")
        await update.message.reply_text(
            "❌ Bog'lashda xatolik yuz berdi. Qayta urinib ko'ring."
        )


# ─── /help ───────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam sahifasini ko'rsatish (admin bo'lsa kengaytirilgan)"""
    telegram_id = update.effective_user.id
    lang = get_user_lang(context)

    # Asosiy yordam matni
    help_text = t("help", lang)

    # Admin bo'lsa qo'shimcha buyruqlar
    admin_user = await get_admin_user(telegram_id)
    if admin_user and admin_user.role in (UserRole.ADMIN, UserRole.INVESTIGATOR):
        admin_help = (
            "\n\n*📊 Admin buyruqlar:*\n"
            "/stats — Bugungi statistika\n"
            "/overdue — Muddati o'tganlar\n"
            "/mine — Mening murojaatlarim\n"
            "/search — Murojaat qidirish\n"
            "/note — Ichki izoh qo'shish (guruhda)"
        )
        help_text += admin_help

    await update.message.reply_text(
        help_text,
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

            from app.services.deadline import calculate_due_at
            case_priority = PRIORITY_BY_CATEGORY.get(category, CasePriority.MEDIUM)
            case_due_at = await calculate_due_at(case_priority)

            case = Case(
                external_id=case_id,
                reporter_token=token_hash,
                telegram_chat_id=update.effective_user.id,
                is_anonymous=is_anonymous,
                category=category,
                priority=case_priority,
                status=CaseStatus.NEW,
                description_encrypted=encrypt_case_content(description),
                title=f"{description[:100]}..." if len(description) > 100 else description,
                due_at=case_due_at,
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
            admin_msg = await notify_admins(context.bot, case_id, category, description, is_anonymous)

            # Admin guruh xabar ID sini bot_data va DB da saqlash (keyinchalik tahrirlash uchun)
            if admin_msg:
                context.bot_data.setdefault("admin_messages", {})[case_id] = admin_msg.message_id
                # DB ga ham yozish
                try:
                    async with AsyncSessionLocal() as db2:
                        res2 = await db2.execute(select(Case).where(Case.external_id == case_id))
                        saved = res2.scalar_one_or_none()
                        if saved:
                            saved.group_message_id = admin_msg.message_id
                            await db2.commit()
                except Exception as e:
                    logger.warning(f"group_message_id saqlashda xato: {e}")

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

    # Admin menyu tugmalarini tekshirish
    if text in _ADMIN_MENU_TEXTS:
        return await admin_menu_handler(update, context)

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


# ─── Admin guruh: ruxsat tekshiruvi helper ───────────────────────────────────

CATEGORY_LABELS_DISPLAY = {
    CaseCategory.CORRUPTION: "🔴 Korrupsiya / Pora",
    CaseCategory.CONFLICT_OF_INTEREST: "⚖️ Manfaatlar to'qnashuvi",
    CaseCategory.FRAUD: "💸 Firibgarlik / O'g'irlik",
    CaseCategory.SAFETY: "⚠️ Xavfsizlik buzilishi",
    CaseCategory.DISCRIMINATION: "🚫 Kamsitish / Bezovtalik",
    CaseCategory.PROCUREMENT: "📋 Tender buzilishi",
    CaseCategory.OTHER: "❓ Boshqa",
}

PRIORITY_LABELS_DISPLAY = {
    CasePriority.CRITICAL: "🔴 Kritik",
    CasePriority.HIGH: "🟠 Yuqori",
    CasePriority.MEDIUM: "🟡 O'rta",
    CasePriority.LOW: "🟢 Past",
}


async def _check_admin_permission(query) -> bool:
    """Foydalanuvchi admin yoki investigator ekanligini DB dan tekshirish."""
    telegram_id = query.from_user.id
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.telegram_chat_id == telegram_id,
                User.is_active == True,
                User.role.in_([UserRole.ADMIN, UserRole.INVESTIGATOR]),
            )
        )
        user = result.scalar_one_or_none()
    return user is not None


async def _get_admin_user(telegram_id: int):
    """DB dan admin/investigator foydalanuvchini qaytaradi."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.telegram_chat_id == telegram_id,
                User.is_active == True,
                User.role.in_([UserRole.ADMIN, UserRole.INVESTIGATOR]),
            )
        )
        return result.scalar_one_or_none()


# ─── 1. Tayinlash callback handleri ──────────────────────────────────────────

async def handle_assign_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """assign_{case_external_id} — barcha faol admin/investigator larni tanlash menyusi ko'rsatadi."""
    query = update.callback_query
    await query.answer()

    if not await _check_admin_permission(query):
        await query.answer("❌ Ruxsatingiz yo'q", show_alert=True)
        return

    case_external_id = query.data.replace("assign_", "", 1)

    async with AsyncSessionLocal() as db:
        # Faol admin va investigator foydalanuvchilar
        result = await db.execute(
            select(User).where(
                User.is_active == True,
                User.role.in_([UserRole.ADMIN, UserRole.INVESTIGATOR]),
            ).order_by(User.full_name)
        )
        users = result.scalars().all()

    if not users:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_case_{case_external_id}")]
        ]))
        await query.message.reply_text("⚠️ Tayinlash uchun faol admin/investigator topilmadi.")
        return

    buttons = []
    for u in users:
        label = u.full_name or u.username
        username_part = f" (@{u.username})" if u.username else ""
        buttons.append([
            InlineKeyboardButton(
                f"{label}{username_part}",
                callback_data=f"do_assign_{case_external_id}_{u.id}",
            )
        ])
    buttons.append([InlineKeyboardButton("❌ Bekor qilish", callback_data=f"back_case_{case_external_id}")])

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.warning(f"handle_assign_callback edit failed: {e}")


# ─── 2. Tayinlov bajarish callback handleri ──────────────────────────────────

async def handle_do_assign_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """do_assign_{case_id}_{user_uuid} — murojaat tayinlanadi."""
    query = update.callback_query
    await query.answer("⏳ Tayinlanmoqda...")

    if not await _check_admin_permission(query):
        await query.answer("❌ Ruxsatingiz yo'q", show_alert=True)
        return

    # Callback data: do_assign_{case_external_id}_{user_uuid}
    # UUID ni aniq ajratish (uuid 36 belgi)
    data = query.data  # "do_assign_CASE-20260305-00001_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    prefix = "do_assign_"
    rest = data[len(prefix):]  # "CASE-20260305-00001_xxxxxxxx-..."
    # UUID har doim oxirida (36 belgi), case_id oldida
    user_uuid_str = rest[-36:]
    case_external_id = rest[: -(36 + 1)]  # -37: underscore + uuid

    actor_telegram_id = query.from_user.id

    try:
        import uuid as _uuid
        user_uuid = _uuid.UUID(user_uuid_str)
    except ValueError:
        await query.answer("❌ Noto'g'ri ma'lumot", show_alert=True)
        return

    async with AsyncSessionLocal() as db:
        async with db.begin():
            # Case ni lock bilan olamiz (race condition oldini olish)
            case_result = await db.execute(
                select(Case).where(Case.external_id == case_external_id).with_for_update()
            )
            case = case_result.scalar_one_or_none()
            if not case:
                await query.answer("❌ Murojaat topilmadi", show_alert=True)
                return

            # Tayinlanadigan foydalanuvchi
            user_result = await db.execute(select(User).where(User.id == user_uuid))
            assignee = user_result.scalar_one_or_none()
            if not assignee:
                await query.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
                return

            # Faol actor
            actor_result = await db.execute(
                select(User).where(User.telegram_chat_id == actor_telegram_id)
            )
            actor = actor_result.scalar_one_or_none()

            # DB da tayinlash
            case.assigned_to = user_uuid

            # Audit log
            db.add(AuditLog(
                user_id=actor.id if actor else None,
                case_id=case.id,
                action=AuditAction.CASE_ASSIGN,
                payload={
                    "assigned_to": str(user_uuid),
                    "assigned_by_telegram": actor_telegram_id,
                    "source": "telegram_callback",
                },
            ))

            # Session yopilishidan oldin kerakli qiymatlarni saqlash
            assignee_telegram_id = assignee.telegram_chat_id
            assignee_name = assignee.full_name or assignee.username
            case_ext_id = case.external_id
            case_category = case.category
            case_priority = case.priority

    # Transaction commit bo'ldi, endi bildirish

    # Tayinlangan foydalanuvchiga xabar
    if assignee_telegram_id:
        cat_label = CATEGORY_LABELS_DISPLAY.get(case_category, str(case_category))
        pri_label = PRIORITY_LABELS_DISPLAY.get(case_priority, str(case_priority))
        try:
            await context.bot.send_message(
                chat_id=assignee_telegram_id,
                text=(
                    f"📋 *Sizga tayinlandi:* `{case_ext_id}`\n"
                    f"📂 *Kategoriya:* {cat_label}\n"
                    f"⚠️ *Ustuvorlik:* {pri_label}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.warning(f"Assignee Telegram notify failed: {e}")

    # Guruh xabarini yangilash
    new_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Qayta tayinlash", callback_data=f"assign_{case_ext_id}"),
            InlineKeyboardButton("🔍 Admin panelda ko'r", callback_data=f"view_{case_ext_id}"),
        ],
        [
            InlineKeyboardButton("▶️ Boshlash", callback_data=f"start_{case_ext_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{case_ext_id}"),
        ],
    ])
    try:
        await query.edit_message_reply_markup(reply_markup=new_keyboard)
        await query.message.reply_text(
            f"✅ *Tayinlandi:* `{case_ext_id}`\n👤 *Ijrochi:* {assignee_name}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning(f"do_assign edit failed: {e}")


# ─── 3. Boshlash callback handleri ───────────────────────────────────────────

async def handle_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """start_{case_external_id} — murojaat holatini in_progress ga o'tkazadi."""
    query = update.callback_query
    await query.answer("⏳ Boshlanmoqda...")

    if not await _check_admin_permission(query):
        await query.answer("❌ Ruxsatingiz yo'q", show_alert=True)
        return

    case_external_id = query.data.replace("start_", "", 1)
    actor_telegram_id = query.from_user.id

    async with AsyncSessionLocal() as db:
        async with db.begin():
            case_result = await db.execute(
                select(Case).where(Case.external_id == case_external_id).with_for_update()
            )
            case = case_result.scalar_one_or_none()
            if not case:
                await query.answer("❌ Murojaat topilmadi", show_alert=True)
                return

            if case.status not in (CaseStatus.NEW, CaseStatus.NEEDS_INFO):
                await query.answer(
                    f"⚠️ Holat: {case.status.value}. Boshlash mumkin emas.",
                    show_alert=True,
                )
                return

            case.status = CaseStatus.IN_PROGRESS

            actor_result = await db.execute(
                select(User).where(User.telegram_chat_id == actor_telegram_id)
            )
            actor = actor_result.scalar_one_or_none()
            db.add(AuditLog(
                user_id=actor.id if actor else None,
                case_id=case.id,
                action=AuditAction.CASE_UPDATE,
                payload={"status": "in_progress", "source": "telegram_callback"},
            ))

    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    new_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Tayinlash",           callback_data=f"assign_{case_external_id}"),
            InlineKeyboardButton("🔍 Admin panelda ko'r",  callback_data=f"view_{case_external_id}"),
        ],
        [
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{case_external_id}"),
        ],
    ])
    try:
        await query.edit_message_reply_markup(reply_markup=new_keyboard)
        await query.message.reply_text(
            f"▶️ *Boshlandi:* `{case_external_id}`\n🕐 {now_str}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning(f"handle_start_callback edit failed: {e}")


# ─── 4. Rad etish callback handleri ──────────────────────────────────────────

async def handle_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """reject_{case_external_id} — rad etish sababini so'raydi."""
    query = update.callback_query
    await query.answer()

    if not await _check_admin_permission(query):
        await query.answer("❌ Ruxsatingiz yo'q", show_alert=True)
        return

    case_external_id = query.data.replace("reject_", "", 1)

    # context.user_data da holat va case_id saqlash
    context.user_data["reject_case_id"] = case_external_id
    context.user_data["reject_message_id"] = query.message.message_id
    context.user_data["reject_chat_id"] = query.message.chat_id

    try:
        await query.message.reply_text(
            f"❓ *{case_external_id} murojaatini rad etish sababi:*\n\nSababni yozing:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ForceReply(selective=True),
        )
    except Exception as e:
        logger.warning(f"handle_reject_callback reply failed: {e}")


async def handle_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin guruhida rad etish sababini qabul qiladi va holat yangilanadi."""
    if not update.message:
        return

    # Faqat guruh chatida ishlaydi
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    case_external_id = context.user_data.get("reject_case_id")
    if not case_external_id:
        return  # Bu handler uchun emas

    # Ruxsatni tekshirish
    telegram_id = update.effective_user.id
    async with AsyncSessionLocal() as db:
        perm_result = await db.execute(
            select(User).where(
                User.telegram_chat_id == telegram_id,
                User.is_active == True,
                User.role.in_([UserRole.ADMIN, UserRole.INVESTIGATOR]),
            )
        )
        actor = perm_result.scalar_one_or_none()
        if not actor:
            return

    reason = update.message.text.strip()
    if len(reason) < 3:
        await update.message.reply_text("⚠️ Sabab juda qisqa. Iltimos, batafsil yozing.")
        return

    async with AsyncSessionLocal() as db:
        async with db.begin():
            case_result = await db.execute(
                select(Case).where(Case.external_id == case_external_id).with_for_update()
            )
            case = case_result.scalar_one_or_none()
            if not case:
                await update.message.reply_text("❌ Murojaat topilmadi.")
                context.user_data.pop("reject_case_id", None)
                return

            case.status = CaseStatus.REJECTED

            actor_result = await db.execute(
                select(User).where(User.telegram_chat_id == telegram_id)
            )
            actor_user = actor_result.scalar_one_or_none()
            db.add(AuditLog(
                user_id=actor_user.id if actor_user else None,
                case_id=case.id,
                action=AuditAction.CASE_UPDATE,
                payload={"status": "rejected", "reason": reason, "source": "telegram_callback"},
            ))

    context.user_data.pop("reject_case_id", None)
    orig_msg_id = context.user_data.pop("reject_message_id", None)

    # Guruh xabarini yangilash (faqat keyboard qismi)
    new_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Admin panelda ko'r", callback_data=f"view_{case_external_id}")]
    ])
    try:
        if orig_msg_id:
            await context.bot.edit_message_reply_markup(
                chat_id=update.effective_chat.id,
                message_id=orig_msg_id,
                reply_markup=new_keyboard,
            )
    except Exception as e:
        logger.warning(f"handle_reject_reason edit_reply_markup failed: {e}")

    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    await update.message.reply_text(
        f"❌ *Rad etildi:* `{case_external_id}`\n"
        f"📝 *Sabab:* {reason}\n"
        f"🕐 {now_str}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── 5. "view" callback — admin panelga yo'naltirish ─────────────────────────

async def handle_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """view_{case_external_id} — admin panelga havola yuboradi."""
    query = update.callback_query
    await query.answer()

    if not await _check_admin_permission(query):
        await query.answer("❌ Ruxsatingiz yo'q", show_alert=True)
        return

    case_external_id = query.data.replace("view_", "", 1)
    panel_url = settings.WEBHOOK_URL.replace("/api/telegram/webhook", "")
    await query.message.reply_text(
        f"🔍 Admin panelda ko'rish:\n{panel_url}/admin/cases/{case_external_id}",
        disable_web_page_preview=True,
    )


# ─── 6. back_case callback — asl keyboardga qaytish ─────────────────────────

async def handle_back_case_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """back_case_{case_id} — asl 4-tugmali keyboardga qaytadi."""
    query = update.callback_query
    await query.answer()

    case_external_id = query.data.replace("back_case_", "", 1)
    original_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Tayinlash",           callback_data=f"assign_{case_external_id}"),
            InlineKeyboardButton("🔍 Admin panelda ko'r",  callback_data=f"view_{case_external_id}"),
        ],
        [
            InlineKeyboardButton("▶️ Boshlash",  callback_data=f"start_{case_external_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{case_external_id}"),
        ],
    ])
    try:
        await query.edit_message_reply_markup(reply_markup=original_keyboard)
    except Exception as e:
        logger.warning(f"handle_back_case_callback failed: {e}")


# ─── 7. Holat o'zgartirish callback handleri (ALLOWED_TRANSITIONS bilan) ─────

async def handle_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    status_{case_id}_{new_status} — murojaat holatini ALLOWED_TRANSITIONS ga qarab o'zgartiradi.
    "rejected" yoki "completed" uchun sabab so'raydi.
    """
    query = update.callback_query

    # Faqat guruhda ishlaydi
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await query.answer("❌ Bu amal faqat guruhda ishlaydi", show_alert=True)
        return

    if not await _check_admin_permission(query):
        await query.answer("❌ Ruxsatingiz yo'q", show_alert=True)
        return

    # Callback data: status_{case_id}_{new_status}
    # Masalan: status_CASE-20260305-00001_in_progress
    parts = query.data.split("_", 2)  # ["status", "CASE-20260305-00001", "in_progress"] yoki ko'proq
    if len(parts) < 3:
        await query.answer("❌ Noto'g'ri format", show_alert=True)
        return

    # Case ID va status ni ajratish
    rest = query.data[len("status_"):]  # "CASE-20260305-00001_in_progress"
    # Oxirgi _ dan keyin status keladi
    last_underscore = rest.rfind("_")
    if last_underscore == -1:
        await query.answer("❌ Noto'g'ri format", show_alert=True)
        return

    case_external_id = rest[:last_underscore]
    new_status_str = rest[last_underscore + 1:]

    # Status ni CaseStatus enumga aylantirish
    try:
        new_status = CaseStatus(new_status_str)
    except ValueError:
        await query.answer(f"❌ Noto'g'ri status: {new_status_str}", show_alert=True)
        return

    # Case rate limit tekshiruvi
    allowed, retry_after = await check_case_rate_limit(case_external_id)
    if not allowed:
        await query.answer(
            f"⏳ Juda ko'p amal. {retry_after} soniyadan keyin urinib ko'ring.",
            show_alert=True
        )
        return

    await query.answer("⏳ O'zgartirilmoqda...")

    actor_telegram_id = query.from_user.id

    async with AsyncSessionLocal() as db:
        case_result = await db.execute(
            select(Case).where(Case.external_id == case_external_id)
        )
        case = case_result.scalar_one_or_none()

        if not case:
            await query.answer("❌ Murojaat topilmadi", show_alert=True)
            return

        old_status = case.status

        # ALLOWED_TRANSITIONS tekshiruvi
        allowed_next = ALLOWED_TRANSITIONS.get(old_status, [])
        if new_status not in allowed_next:
            await query.answer(
                f"⚠️ {old_status.value} → {new_status.value} o'tish mumkin emas",
                show_alert=True
            )
            return

    # "rejected" yoki "completed" uchun sabab so'rash
    if new_status in (CaseStatus.REJECTED, CaseStatus.COMPLETED):
        status_label = "rad etish" if new_status == CaseStatus.REJECTED else "yakunlash"
        context.user_data["pending_status_change"] = {
            "case_external_id": case_external_id,
            "new_status": new_status.value,
            "message_id": query.message.message_id,
            "chat_id": query.message.chat_id,
            "actor_telegram_id": actor_telegram_id,
        }

        try:
            await query.message.reply_text(
                f"✍️ *{case_external_id}* murojaatini {status_label} uchun sabab/izoh yozing:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=ForceReply(selective=True),
            )
        except Exception as e:
            logger.warning(f"handle_status_callback ForceReply failed: {e}")
        return

    # Boshqa statuslar uchun to'g'ridan status o'zgartirish
    await _apply_status_change(
        context=context,
        case_external_id=case_external_id,
        new_status=new_status,
        actor_telegram_id=actor_telegram_id,
        reason=None,
        original_message_id=query.message.message_id,
        chat_id=query.message.chat_id,
    )


async def _apply_status_change(
    context: ContextTypes.DEFAULT_TYPE,
    case_external_id: str,
    new_status: CaseStatus,
    actor_telegram_id: int,
    reason: str | None,
    original_message_id: int,
    chat_id: int,
):
    """Status o'zgartirishni bajaradi va guruh xabarini yangilaydi."""

    async with AsyncSessionLocal() as db:
        async with db.begin():
            case_result = await db.execute(
                select(Case).where(Case.external_id == case_external_id).with_for_update()
            )
            case = case_result.scalar_one_or_none()

            if not case:
                return

            old_status = case.status
            case.status = new_status

            # Closed date ni belgilash
            if new_status in (CaseStatus.COMPLETED, CaseStatus.REJECTED):
                case.closed_at = datetime.now(timezone.utc)

            # Actor
            actor_result = await db.execute(
                select(User).where(User.telegram_chat_id == actor_telegram_id)
            )
            actor = actor_result.scalar_one_or_none()

            # Audit log
            db.add(AuditLog(
                user_id=actor.id if actor else None,
                case_id=case.id,
                action=AuditAction.CASE_UPDATE,
                payload={
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "reason": reason,
                    "source": "telegram_group_callback",
                },
            ))

            # Sabab bilan comment qo'shish
            if reason:
                db.add(CaseComment(
                    case_id=case.id,
                    author_id=actor.id if actor else None,
                    is_from_reporter=False,
                    is_internal=True,
                    content_encrypted=encrypt_comment_content(
                        f"[Status o'zgartirildi: {old_status.value} → {new_status.value}]\n{reason}"
                    ),
                ))

            # Assignee va case ma'lumotlarini olish (session yopilishidan oldin)
            case_ext_id = case.external_id
            case_data = {
                "external_id": case.external_id,
                "category": case.category,
                "priority": case.priority,
                "status": case.status,
                "assigned_to": case.assigned_to,
                "created_at": case.created_at,
                "due_at": case.due_at,
                "group_message_id": case.group_message_id,
            }

    # Guruh xabarini yangilash
    try:
        # Case ni DB dan qayta o'qish (assignee bilan)
        async with AsyncSessionLocal() as db:
            case_result = await db.execute(
                select(Case).where(Case.external_id == case_ext_id)
            )
            case_for_update = case_result.scalar_one_or_none()

            if case_for_update:
                new_msg = await update_group_message(context.bot, case_for_update, chat_id)

                # Yangi xabar ID ni saqlash (agar o'zgargan bo'lsa)
                if new_msg and new_msg.message_id != case_for_update.group_message_id:
                    case_for_update.group_message_id = new_msg.message_id
                    await db.commit()
    except Exception as e:
        logger.warning(f"_apply_status_change update message failed: {e}")

    # Javob xabari
    status_label = STATUS_LABELS.get(new_status, new_status.value)
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    result_text = f"{status_label}: `{case_ext_id}`\n🕐 {now_str}"
    if reason:
        result_text += f"\n📝 *Sabab:* {reason[:200]}"

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=result_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning(f"_apply_status_change result message failed: {e}")


async def handle_status_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status o'zgartirish uchun sabab xabarini qabul qiladi."""
    if not update.message:
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    pending = context.user_data.get("pending_status_change")
    if not pending:
        return

    # Ruxsatni tekshirish
    telegram_id = update.effective_user.id
    if telegram_id != pending.get("actor_telegram_id"):
        return  # Boshqa foydalanuvchi

    actor = await _get_admin_user(telegram_id)
    if not actor:
        return

    reason = update.message.text.strip()
    if len(reason) < 3:
        await update.message.reply_text("⚠️ Sabab juda qisqa. Iltimos, batafsil yozing.")
        return

    # Pending ma'lumotlarni olish va tozalash
    case_external_id = pending["case_external_id"]
    new_status_str = pending["new_status"]
    original_message_id = pending["message_id"]
    chat_id = pending["chat_id"]
    context.user_data.pop("pending_status_change", None)

    try:
        new_status = CaseStatus(new_status_str)
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri status")
        return

    await _apply_status_change(
        context=context,
        case_external_id=case_external_id,
        new_status=new_status,
        actor_telegram_id=telegram_id,
        reason=reason,
        original_message_id=original_message_id,
        chat_id=chat_id,
    )


# ─── 8. /note buyrug'i — ichki izoh qo'shish ─────────────────────────────────

async def handle_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /note CASE-00042 Tekshiruv boshlandi
    Faqat guruhda ishlaydi. case_comments ga is_internal=True bilan saqlaydi.
    """
    if not update.message:
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "❌ Bu buyruq faqat guruhda ishlaydi.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Ruxsatni tekshirish
    telegram_id = update.effective_user.id
    actor = await _get_admin_user(telegram_id)
    if not actor:
        await update.message.reply_text("❌ Ruxsatingiz yo'q")
        return

    # Matnni ajratish: /note CASE-XXXXX izoh matni
    text = update.message.text
    parts = text.split(maxsplit=2)  # ["/note", "CASE-XXXXX", "izoh matni"]

    if len(parts) < 3:
        await update.message.reply_text(
            "⚠️ Format: `/note CASE-XXXXX Izoh matni`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    case_id = parts[1].upper()
    note_text = parts[2].strip()

    if not re.match(r"CASE-\d{8}-\d{5}", case_id):
        await update.message.reply_text(
            "⚠️ Noto'g'ri murojaat raqami. Masalan: `CASE-20260305-00001`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if len(note_text) < 3:
        await update.message.reply_text("⚠️ Izoh juda qisqa.")
        return

    async with AsyncSessionLocal() as db:
        case_result = await db.execute(
            select(Case).where(Case.external_id == case_id)
        )
        case = case_result.scalar_one_or_none()

        if not case:
            await update.message.reply_text(f"❌ Murojaat topilmadi: `{case_id}`", parse_mode=ParseMode.MARKDOWN)
            return

        # Ichki izoh qo'shish
        comment = CaseComment(
            case_id=case.id,
            author_id=actor.id,
            is_from_reporter=False,
            is_internal=True,  # Ichki izoh
            content_encrypted=encrypt_comment_content(note_text),
        )
        db.add(comment)

        # Audit log
        db.add(AuditLog(
            user_id=actor.id,
            case_id=case.id,
            action=AuditAction.CASE_COMMENT,
            payload={"type": "internal_note", "source": "telegram_group"},
        ))

        await db.commit()

    await update.message.reply_text(
        f"📝 Ichki izoh saqlandi: `{case_id}`",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── 9. /search buyrug'i — murojaat qidirish ─────────────────────────────────

async def handle_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /search CASE-00042 yoki /search korrupsiya
    Faqat guruhda ishlaydi. Natija faqat so'ragan foydalanuvchiga ko'rinadi.
    """
    if not update.message:
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Bu buyruq faqat guruhda ishlaydi.")
        return

    # Ruxsatni tekshirish
    telegram_id = update.effective_user.id
    actor = await _get_admin_user(telegram_id)
    if not actor:
        await update.message.reply_text("❌ Ruxsatingiz yo'q")
        return

    # Qidiruv so'zi
    text = update.message.text
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text(
            "⚠️ Format: `/search CASE-XXXXX` yoki `/search kalit_soz`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    search_term = parts[1].strip()

    async with AsyncSessionLocal() as db:
        # Avval external_id bo'yicha qidirish
        if re.match(r"CASE-\d{8}-\d{5}", search_term.upper()):
            result = await db.execute(
                select(Case).where(Case.external_id == search_term.upper())
            )
            cases = [result.scalar_one_or_none()]
            cases = [c for c in cases if c]
        else:
            # Kalit so'z bo'yicha qidirish (title va external_id da)
            search_pattern = f"%{search_term}%"
            result = await db.execute(
                select(Case).where(
                    (Case.external_id.ilike(search_pattern)) |
                    (Case.title.ilike(search_pattern))
                ).order_by(Case.created_at.desc()).limit(10)
            )
            cases = result.scalars().all()

    if not cases:
        # Foydalanuvchiga shaxsiy xabar yuborish
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"🔍 *Qidiruv:* `{search_term}`\n\n❌ Natija topilmadi.",
                parse_mode=ParseMode.MARKDOWN,
            )
            await update.message.reply_text("📬 Natija shaxsiy xabarda yuborildi.")
        except Exception as e:
            await update.message.reply_text(f"❌ Natija topilmadi: `{search_term}`", parse_mode=ParseMode.MARKDOWN)
        return

    # Natijalarni formatlash
    result_text = f"🔍 *Qidiruv:* `{search_term}`\n\n*Natijalar:* {len(cases)} ta\n\n"

    status_emoji = {
        CaseStatus.NEW: "🆕", CaseStatus.IN_PROGRESS: "🔄",
        CaseStatus.NEEDS_INFO: "❓", CaseStatus.COMPLETED: "✅",
        CaseStatus.REJECTED: "❌", CaseStatus.ARCHIVED: "📦",
    }

    for case in cases:
        emoji = status_emoji.get(case.status, "•")
        date_str = case.created_at.strftime("%d.%m.%Y") if case.created_at else "—"
        title_short = (case.title[:40] + "...") if case.title and len(case.title) > 40 else (case.title or "—")
        result_text += f"{emoji} `{case.external_id}` · {date_str}\n   _{title_short}_\n\n"

    # Foydalanuvchiga shaxsiy xabar yuborish
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=result_text,
            parse_mode=ParseMode.MARKDOWN,
        )
        await update.message.reply_text("📬 Natija shaxsiy xabarda yuborildi.")
    except Exception as e:
        logger.warning(f"handle_search_command send failed: {e}")
        await update.message.reply_text("❌ Natijani yuborishda xatolik. Bot bilan shaxsiy chat oching.")


# ─── 10. Guruh reply → murojaat izohiga ──────────────────────────────────────

async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Guruhda murojaat xabariga reply qilinsa — izoh sifatida saqlaydi.
    """
    if not update.message:
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    # Reply mavjudligini tekshirish
    reply_to = update.message.reply_to_message
    if not reply_to:
        return

    # Ruxsatni tekshirish
    telegram_id = update.effective_user.id
    actor = await _get_admin_user(telegram_id)
    if not actor:
        return  # Oddiy foydalanuvchi — e'tiborsiz qoldiramiz

    # Reply qilingan xabardan case_id ni topish
    reply_text = reply_to.text or ""

    # Case ID ni topish (CASE-XXXXXXXX-XXXXX formatida)
    case_match = re.search(r"CASE-\d{8}-\d{5}", reply_text)
    if not case_match:
        return  # Bu murojaat xabari emas

    case_external_id = case_match.group(0)
    comment_text = update.message.text.strip()

    if len(comment_text) < 2:
        return

    async with AsyncSessionLocal() as db:
        case_result = await db.execute(
            select(Case).where(Case.external_id == case_external_id)
        )
        case = case_result.scalar_one_or_none()

        if not case:
            return

        # Izoh qo'shish (tashqi izoh — reporter ko'ra oladi)
        comment = CaseComment(
            case_id=case.id,
            author_id=actor.id,
            is_from_reporter=False,
            is_internal=False,  # Tashqi izoh
            content_encrypted=encrypt_comment_content(comment_text),
        )
        db.add(comment)

        # Audit log
        db.add(AuditLog(
            user_id=actor.id,
            case_id=case.id,
            action=AuditAction.CASE_COMMENT,
            payload={"type": "group_reply", "source": "telegram_group"},
        ))

        await db.commit()

    await update.message.reply_text(
        f"✅ Izoh `{case_external_id}` ga saqlandi",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── Admin buyruqlar: /stats, /overdue, /mine ────────────────────────────────

async def handle_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stats — Bugungi statistika (faqat admin/investigator uchun)
    """
    telegram_id = update.effective_user.id

    # Ruxsat tekshiruvi
    if not await is_investigator_or_above(telegram_id):
        await update.message.reply_text("❌ Ruxsatingiz yo'q")
        return

    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)

    async with AsyncSessionLocal() as db:
        # Bugungi statistika
        new_count = await db.scalar(
            select(func.count(Case.id)).where(Case.status == CaseStatus.NEW)
        )
        in_progress_count = await db.scalar(
            select(func.count(Case.id)).where(Case.status == CaseStatus.IN_PROGRESS)
        )
        completed_count = await db.scalar(
            select(func.count(Case.id)).where(
                Case.status == CaseStatus.COMPLETED,
                Case.closed_at >= today_start
            )
        )
        rejected_count = await db.scalar(
            select(func.count(Case.id)).where(
                Case.status == CaseStatus.REJECTED,
                Case.closed_at >= today_start
            )
        )

        # Deadline yaqin (3 kun ichida)
        deadline_soon = datetime.now(timezone.utc) + timedelta(days=3)
        deadline_count = await db.scalar(
            select(func.count(Case.id)).where(
                Case.due_at <= deadline_soon,
                Case.due_at > datetime.now(timezone.utc),
                Case.status.notin_([CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED])
            )
        )

    today_str = today.strftime("%d.%m.%Y")
    stats_text = (
        f"📊 *Statistika — {today_str}*\n\n"
        f"🆕 Yangi: {new_count or 0} | 🔄 Ko'rilmoqda: {in_progress_count or 0} | "
        f"✅ Hal: {completed_count or 0} | ❌ Rad: {rejected_count or 0}\n"
        f"⏰ Deadline yaqin (3 kun): {deadline_count or 0}"
    )

    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)


async def handle_overdue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /overdue — Muddati o'tgan murojaatlar (faqat admin/investigator uchun)
    """
    telegram_id = update.effective_user.id

    if not await is_investigator_or_above(telegram_id):
        await update.message.reply_text("❌ Ruxsatingiz yo'q")
        return

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Case)
            .where(
                Case.due_at < now,
                Case.status.notin_([CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED])
            )
            .order_by(Case.due_at.asc())
            .limit(10)
        )
        overdue_cases = result.scalars().all()

        # Jami son
        total_count = await db.scalar(
            select(func.count(Case.id)).where(
                Case.due_at < now,
                Case.status.notin_([CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED])
            )
        )

    if not overdue_cases:
        await update.message.reply_text("✅ Muddati o'tgan murojaatlar yo'q!")
        return

    text = "🚨 *Muddati o'tgan murojaatlar:*\n\n"

    category_labels = {
        CaseCategory.CORRUPTION: "Korrupsiya",
        CaseCategory.FRAUD: "Firibgarlik",
        CaseCategory.SAFETY: "Xavfsizlik",
        CaseCategory.DISCRIMINATION: "Kamsitish",
        CaseCategory.PROCUREMENT: "Tender",
        CaseCategory.CONFLICT_OF_INTEREST: "Manfaat to'qnashuvi",
        CaseCategory.OTHER: "Boshqa",
    }

    for case in overdue_cases:
        days_overdue = (now - case.due_at).days
        cat_label = category_labels.get(case.category, str(case.category.value))

        # Assignee nomi
        if case.assignee:
            assignee_name = case.assignee.full_name or case.assignee.username
        else:
            assignee_name = "Tayinlanmagan"

        text += f"🚨 `{case.external_id}` — {cat_label} — {days_overdue} kun kechikkan — {assignee_name}\n"

    text += f"\n*Jami:* {total_count or 0} ta"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def handle_mine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /mine — Menga tayinlangan murojaatlar (faqat admin/investigator uchun)
    """
    telegram_id = update.effective_user.id

    admin_user = await get_admin_user(telegram_id)
    if not admin_user:
        await update.message.reply_text("❌ Ruxsatingiz yo'q")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Case)
            .where(
                Case.assigned_to == admin_user.id,
                Case.status.notin_([CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED])
            )
            .order_by(Case.due_at.asc().nullslast(), Case.created_at.desc())
            .limit(15)
        )
        my_cases = result.scalars().all()

    if not my_cases:
        await update.message.reply_text("📭 Sizga tayinlangan ochiq murojaatlar yo'q.")
        return

    text = "📋 *Mening murojaatlarim:*\n\n"

    status_labels = {
        CaseStatus.NEW: "🆕 Yangi",
        CaseStatus.IN_PROGRESS: "🔄 Ko'rilmoqda",
        CaseStatus.NEEDS_INFO: "❓ Ma'lumot kerak",
    }

    category_short = {
        CaseCategory.CORRUPTION: "Korrupsiya",
        CaseCategory.FRAUD: "Firibgarlik",
        CaseCategory.SAFETY: "Xavfsizlik",
        CaseCategory.DISCRIMINATION: "Kamsitish",
        CaseCategory.PROCUREMENT: "Tender",
        CaseCategory.CONFLICT_OF_INTEREST: "Manfaat",
        CaseCategory.OTHER: "Boshqa",
    }

    buttons = []
    for case in my_cases:
        status_label = status_labels.get(case.status, case.status.value)
        cat_label = category_short.get(case.category, str(case.category.value))
        due_str = case.due_at.strftime("%d.%m") if case.due_at else "—"

        text += f"`{case.external_id}` | {cat_label} | {status_label} | Deadline: {due_str}\n"

        # Inline tugma
        panel_url = settings.WEBHOOK_URL.replace("/api/telegram/webhook", "")
        buttons.append([
            InlineKeyboardButton(
                f"🔍 {case.external_id}",
                url=f"{panel_url}/admin/cases/{case.external_id}"
            )
        ])

    keyboard = InlineKeyboardMarkup(buttons[:5])  # Ko'pi bilan 5 ta tugma

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ─── Admin menyu tugmalari handleri ──────────────────────────────────────────

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin menyu tugmalari bosilganda ishga tushadi"""
    text = update.message.text
    telegram_id = update.effective_user.id
    lang = get_user_lang(context)

    # Admin/investigator ekanligini tekshirish
    admin_user = await get_admin_user(telegram_id)

    if text == "📊 Statistika":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU
        return await handle_stats_command(update, context)

    elif text == "🔔 Yangi murojaatlar":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU
        # Yangi murojaatlar ro'yxati
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Case)
                .where(Case.status == CaseStatus.NEW)
                .order_by(Case.created_at.desc())
                .limit(10)
            )
            new_cases = result.scalars().all()

        if not new_cases:
            await update.message.reply_text("✅ Yangi murojaatlar yo'q!")
            return MAIN_MENU

        text_msg = "🔔 *Yangi murojaatlar:*\n\n"
        for case in new_cases:
            date_str = case.created_at.strftime("%d.%m %H:%M")
            text_msg += f"🆕 `{case.external_id}` — {date_str}\n"

        await update.message.reply_text(text_msg, parse_mode=ParseMode.MARKDOWN)
        return MAIN_MENU

    elif text == "⏰ Deadline yaqin":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU

        deadline_soon = datetime.now(timezone.utc) + timedelta(days=3)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Case)
                .where(
                    Case.due_at <= deadline_soon,
                    Case.due_at > datetime.now(timezone.utc),
                    Case.status.notin_([CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED])
                )
                .order_by(Case.due_at.asc())
                .limit(10)
            )
            cases = result.scalars().all()

        if not cases:
            await update.message.reply_text("✅ Deadline yaqin murojaatlar yo'q!")
            return MAIN_MENU

        text_msg = "⏰ *Deadline yaqin murojaatlar (3 kun ichida):*\n\n"
        for case in cases:
            due_str = case.due_at.strftime("%d.%m.%Y")
            days_left = (case.due_at.date() - datetime.now(timezone.utc).date()).days
            text_msg += f"⏰ `{case.external_id}` — {due_str} ({days_left} kun qoldi)\n"

        await update.message.reply_text(text_msg, parse_mode=ParseMode.MARKDOWN)
        return MAIN_MENU

    elif text == "🚨 Muddati o'tgan":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU
        return await handle_overdue_command(update, context)

    elif text == "📋 Mening murojaatlarim":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU
        return await handle_mine_command(update, context)

    elif text == "👥 Jamoam":
        if not admin_user or admin_user.role != UserRole.ADMIN:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU

        # Jamoa a'zolari va ularning yuklari
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User)
                .where(
                    User.is_active == True,
                    User.role.in_([UserRole.ADMIN, UserRole.INVESTIGATOR])
                )
                .order_by(User.full_name)
            )
            team_members = result.scalars().all()

        text_msg = "👥 *Jamoa a'zolari:*\n\n"
        for member in team_members:
            name = member.full_name or member.username
            role_label = "🔴 Admin" if member.role == UserRole.ADMIN else "🔵 Investigator"

            # Ochiq murojaatlar soni
            async with AsyncSessionLocal() as db:
                open_count = await db.scalar(
                    select(func.count(Case.id)).where(
                        Case.assigned_to == member.id,
                        Case.status.notin_([CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED])
                    )
                )

            text_msg += f"{role_label} *{name}* — {open_count or 0} ta ochiq\n"

        await update.message.reply_text(text_msg, parse_mode=ParseMode.MARKDOWN)
        return MAIN_MENU

    elif text == "⚙️ Hisobot sozlamalari":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU
        return await show_notification_settings(update, context)

    elif text == "🔔 Yangi tayinlovlar":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU

        # Oxirgi 7 kunda tayinlangan murojaatlar
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Case)
                .where(
                    Case.assigned_to == admin_user.id,
                    Case.updated_at >= week_ago,
                )
                .order_by(Case.updated_at.desc())
                .limit(10)
            )
            cases = result.scalars().all()

        if not cases:
            await update.message.reply_text("📭 Oxirgi 7 kunda yangi tayinlovlar yo'q.")
            return MAIN_MENU

        text_msg = "🔔 *Yangi tayinlovlar (7 kun):*\n\n"
        for case in cases:
            date_str = case.updated_at.strftime("%d.%m %H:%M")
            status_emoji = {"new": "🆕", "in_progress": "🔄", "needs_info": "❓"}.get(case.status.value, "•")
            text_msg += f"{status_emoji} `{case.external_id}` — {date_str}\n"

        await update.message.reply_text(text_msg, parse_mode=ParseMode.MARKDOWN)
        return MAIN_MENU

    elif text == "📊 Mening statistikam":
        if not admin_user:
            await update.message.reply_text("❌ Ruxsatingiz yo'q")
            return MAIN_MENU

        # Shaxsiy statistika
        async with AsyncSessionLocal() as db:
            open_count = await db.scalar(
                select(func.count(Case.id)).where(
                    Case.assigned_to == admin_user.id,
                    Case.status.notin_([CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED])
                )
            )
            completed_count = await db.scalar(
                select(func.count(Case.id)).where(
                    Case.assigned_to == admin_user.id,
                    Case.status == CaseStatus.COMPLETED
                )
            )

            # O'rtacha hal vaqti
            avg_result = await db.execute(
                select(func.avg(Case.closed_at - Case.created_at))
                .where(
                    Case.assigned_to == admin_user.id,
                    Case.status == CaseStatus.COMPLETED,
                    Case.closed_at.isnot(None)
                )
            )
            avg_time = avg_result.scalar()

        avg_days = avg_time.days if avg_time else 0

        text_msg = (
            f"📊 *Mening statistikam:*\n\n"
            f"📂 Ochiq murojaatlar: {open_count or 0}\n"
            f"✅ Yakunlangan: {completed_count or 0}\n"
            f"⏱ O'rtacha hal vaqti: {avg_days} kun"
        )

        await update.message.reply_text(text_msg, parse_mode=ParseMode.MARKDOWN)
        return MAIN_MENU

    elif text == "🏠 Standart menyu":
        # Standart menyuga qaytish
        await update.message.reply_text(
            "👇 Standart menyu:",
            reply_markup=get_persistent_menu(lang),
        )
        return MAIN_MENU

    return MAIN_MENU


# ─── Bildirishnoma sozlamalari ───────────────────────────────────────────────

async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bildirishnoma sozlamalarini ko'rsatish"""
    telegram_id = update.effective_user.id

    # Joriy sozlamalarni olish
    from app.models import BotUser
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        bot_user = result.scalar_one_or_none()

    # Default sozlamalar
    prefs = {
        "new_assignment": True,
        "deadline_reminder": True,
        "overdue_alert": True,
    }

    if bot_user and bot_user.notification_prefs:
        prefs.update(bot_user.notification_prefs)

    # Toggle tugmalar
    def toggle_label(key: str, label: str) -> str:
        status = "✅" if prefs.get(key, True) else "❌"
        return f"{label}: {status}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            toggle_label("new_assignment", "🔔 Yangi tayinlov"),
            callback_data="notif_toggle_new_assignment"
        )],
        [InlineKeyboardButton(
            toggle_label("deadline_reminder", "⏰ Deadline eslatma"),
            callback_data="notif_toggle_deadline_reminder"
        )],
        [InlineKeyboardButton(
            toggle_label("overdue_alert", "🚨 Muddati o'tgan"),
            callback_data="notif_toggle_overdue_alert"
        )],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="home")],
    ])

    await update.message.reply_text(
        "⚙️ *Bildirishnoma sozlamalari*\n\n"
        "Quyidagi sozlamalarni yoqish/o'chirish uchun bosing:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )
    return MAIN_MENU


async def handle_notification_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bildirishnoma sozlamasini toggle qilish"""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    # Toggle qilinadigan sozlama
    pref_key = query.data.replace("notif_toggle_", "")

    from app.models import BotUser
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        bot_user = result.scalar_one_or_none()

        if not bot_user:
            await query.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
            return

        # Joriy sozlamalar
        prefs = bot_user.notification_prefs or {
            "new_assignment": True,
            "deadline_reminder": True,
            "overdue_alert": True,
        }

        # Toggle
        prefs[pref_key] = not prefs.get(pref_key, True)
        bot_user.notification_prefs = prefs

        await db.commit()

    # Yangilangan sozlamalarni ko'rsatish
    def toggle_label(key: str, label: str) -> str:
        status = "✅" if prefs.get(key, True) else "❌"
        return f"{label}: {status}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            toggle_label("new_assignment", "🔔 Yangi tayinlov"),
            callback_data="notif_toggle_new_assignment"
        )],
        [InlineKeyboardButton(
            toggle_label("deadline_reminder", "⏰ Deadline eslatma"),
            callback_data="notif_toggle_deadline_reminder"
        )],
        [InlineKeyboardButton(
            toggle_label("overdue_alert", "🚨 Muddati o'tgan"),
            callback_data="notif_toggle_overdue_alert"
        )],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="home")],
    ])

    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except Exception:
        pass

    status_text = "yoqildi ✅" if prefs[pref_key] else "o'chirildi ❌"
    await query.answer(f"Sozlama {status_text}")



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

    # ✅ Admin guruh: inline keyboard callback handlerlari
    app.add_handler(CallbackQueryHandler(handle_assign_callback,    pattern=r"^assign_"))
    app.add_handler(CallbackQueryHandler(handle_do_assign_callback, pattern=r"^do_assign_"))
    app.add_handler(CallbackQueryHandler(handle_start_callback,     pattern=r"^start_"))
    app.add_handler(CallbackQueryHandler(handle_reject_callback,    pattern=r"^reject_"))
    app.add_handler(CallbackQueryHandler(handle_view_callback,      pattern=r"^view_"))
    app.add_handler(CallbackQueryHandler(handle_back_case_callback, pattern=r"^back_case_"))

    # ✅ Status o'zgartirish callback handleri (ALLOWED_TRANSITIONS bilan)
    app.add_handler(CallbackQueryHandler(handle_status_callback,    pattern=r"^status_"))

    # ✅ Admin guruh buyruqlari: /note va /search
    app.add_handler(CommandHandler("note", handle_note_command))
    app.add_handler(CommandHandler("search", handle_search_command))

    # ✅ Admin buyruqlari: /stats, /overdue, /mine
    app.add_handler(CommandHandler("stats", handle_stats_command))
    app.add_handler(CommandHandler("overdue", handle_overdue_command))
    app.add_handler(CommandHandler("mine", handle_mine_command))

    # ✅ Admin menyu tugmalari handleri
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(
            r"^(📊 Statistika|🔔 Yangi murojaatlar|⏰ Deadline yaqin|🚨 Muddati o'tgan|"
            r"📋 Mening murojaatlarim|👥 Jamoam|⚙️ Hisobot sozlamalari|🏠 Standart menyu|"
            r"🔔 Yangi tayinlovlar|📊 Mening statistikam)$"
        ),
        admin_menu_handler,
    ))

    # ✅ Bildirishnoma sozlamalari toggle callback
    app.add_handler(CallbackQueryHandler(handle_notification_toggle, pattern=r"^notif_toggle_"))

    # ✅ Admin guruh: rad etish sababi xabari (guruh chati)
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
        handle_reject_reason,
    ))

    # ✅ Admin guruh: status o'zgartirish sababi xabari (pending_status_change)
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND & filters.REPLY,
        handle_status_reason,
    ))

    # ✅ Admin guruh: reply → murojaat izohiga
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND & filters.REPLY,
        handle_group_reply,
    ))

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