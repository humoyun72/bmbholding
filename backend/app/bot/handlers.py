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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
import re

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import encrypt_text
from app.models import Case, CaseAttachment, CaseComment, CaseCategory, CasePriority, CaseStatus
from app.services.storage import save_telegram_file
from app.services.notification import notify_admins

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


def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Murojaat yuborish", callback_data="report")],
        [InlineKeyboardButton("🔍 Murojaat holatini tekshirish", callback_data="check_status")],
        [InlineKeyboardButton("❓ FAQ / Ko'p so'raladigan savollar", callback_data="faq")],
        [InlineKeyboardButton("📞 Aloqa ma'lumotlari", callback_data="contacts")],
    ])


def get_category_keyboard():
    buttons = [[InlineKeyboardButton(cat, callback_data=f"cat_{i}")]
               for i, cat in enumerate(CATEGORY_MAP.keys())]
    buttons.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


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


# ─── Handlers ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "report":
        await query.edit_message_text(
            CATEGORY_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_category_keyboard()
        )
        return CHOOSE_CATEGORY

    elif query.data == "check_status":
        await query.edit_message_text(
            "🔍 *Murojaat raqamingizni kiriting:*\n\nMasalan: `CASE-20251201-00001`",
            parse_mode=ParseMode.MARKDOWN
        )
        return CHECK_STATUS

    elif query.data == "faq":
        faq_text = """
❓ *Ko'p so'raladigan savollar*

*Mening shaxsiyatim oshkor bo'ladimi?*
Yo'q. Siz anonim yuborishni tanlasangiz, botimiz hech qanday shaxsiy ma'lumot saqlamaydi.

*Murojaat qancha vaqtda ko'rib chiqiladi?*
• Kritik: 24 soat ichida
• Yuqori: 72 soat ichida
• O'rta: 7 kun ichida
• Past: 30 kun ichida

*Fayl yuborishim mumkinmi?*
Ha, rasm va hujjatlar (20 MB gacha) yuborishingiz mumkin.

*Murojaat holatini qanday bilaman?*
Murojaat ID raqamingizni kiritib tekshiring.
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
            "📞 *Compliance Departamenti*\n\nEmail: compliance@company.uz\nTelefon: +998 XX XXX XX XX\n\nIsh vaqti: Du-Ju, 09:00-18:00",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
            ]])
        )
        return MAIN_MENU

    elif query.data == "home":
        await query.edit_message_text(
            WELCOME_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU


async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())
        return MAIN_MENU

    if query.data.startswith("cat_"):
        idx = int(query.data.split("_")[1])
        cat_name = list(CATEGORY_MAP.keys())[idx]
        category = CATEGORY_MAP[cat_name]
        context.user_data["category"] = category
        context.user_data["category_name"] = cat_name

        await query.edit_message_text(
            f"✅ Kategoriya: *{cat_name}*\n\n📝 *Iltimos, muammo haqida batafsil yozing:*\n\n"
            "Quyidagilarni ko'rsating:\n"
            "• Kim, nima, qachon, qayerda\n"
            "• Dalillar (agar bo'lsa)\n"
            "• Qo'shimcha ma'lumotlar\n\n"
            "_Matnni quyida yozing:_",
            parse_mode=ParseMode.MARKDOWN
        )
        return ENTER_DESCRIPTION


async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if len(text) < 20:
        await update.message.reply_text("⚠️ Iltimos, kamida 20 ta belgi kiriting. Ko'proq ma'lumot bering.")
        return ENTER_DESCRIPTION

    context.user_data["description"] = text

    await update.message.reply_text(
        "📎 *Fayl yoki rasm biriktirmoqchimisiz?*\n\n"
        "Rasm yoki hujjat yuboring, yoki davom eting.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ Fayl yuklamasdan davom etish", callback_data="skip_attachment")]
        ])
    )
    context.user_data["attachments"] = []
    return ADD_ATTACHMENT


async def add_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document or update.message.photo:
        if update.message.document:
            file_obj = update.message.document
            file_id = file_obj.file_id
            filename = file_obj.file_name or "document"
            mime_type = file_obj.mime_type or "application/octet-stream"
            size = file_obj.file_size or 0
        else:
            file_obj = update.message.photo[-1]  # largest photo
            file_id = file_obj.file_id
            filename = f"photo_{file_id[:8]}.jpg"
            mime_type = "image/jpeg"
            size = file_obj.file_size or 0

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if size > max_size:
            await update.message.reply_text(f"⚠️ Fayl hajmi {settings.MAX_FILE_SIZE_MB} MB dan oshmasligi kerak.")
            return ADD_ATTACHMENT

        # Block executables
        blocked_exts = [".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js"]
        if any(filename.lower().endswith(ext) for ext in blocked_exts):
            await update.message.reply_text("🚫 Ushbu fayl turi qabul qilinmaydi.")
            return ADD_ATTACHMENT

        context.user_data["attachments"].append({
            "file_id": file_id,
            "filename": filename,
            "mime_type": mime_type,
            "size": size,
        })

        current_count = len(context.user_data["attachments"])
        await update.message.reply_text(
            f"✅ Fayl qabul qilindi ({current_count} ta)\n\nYana fayl yuboring yoki davom eting.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Davom etish", callback_data="skip_attachment")]
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


async def choose_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["is_anonymous"] = query.data == "anon_yes"

    cat = context.user_data.get("category_name", "Noma'lum")
    desc = context.user_data.get("description", "")
    att_count = len(context.user_data.get("attachments", []))
    is_anon = context.user_data["is_anonymous"]

    summary = f"""
📋 *Murojaat xulosasi*

*Kategoriya:* {cat}
*Anonimlik:* {"✅ Anonim" if is_anon else "❌ Anonim emas"}
*Fayllar:* {att_count} ta
*Tavsif:*
_{desc[:300]}{"..." if len(desc) > 300 else ""}_

Ushbu ma'lumotlar to'g'rimi?
    """
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


async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_all":
        context.user_data.clear()
        await query.edit_message_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())
        return MAIN_MENU

    if query.data == "edit_restart":
        await query.edit_message_text(
            CATEGORY_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=get_category_keyboard()
        )
        return CHOOSE_CATEGORY

    # Save case to database
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
                telegram_chat_id=update.effective_user.id,  # har doim saqlaymiz — javob yuborish uchun
                is_anonymous=is_anonymous,
                category=category,
                priority=PRIORITY_BY_CATEGORY.get(category, CasePriority.MEDIUM),
                status=CaseStatus.NEW,
                description_encrypted=encrypt_text(description),
                title=f"{description[:100]}..." if len(description) > 100 else description,
            )
            db.add(case)
            await db.flush()

            # Save attachments
            attachments = context.user_data.get("attachments", [])
            for att_data in attachments:
                try:
                    path, checksum, size = await save_telegram_file(
                        context.bot, att_data["file_id"],
                        att_data["filename"], str(case.id)
                    )
                    attachment = CaseAttachment(
                        case_id=case.id,
                        filename=path.split("/")[-1],
                        original_filename=att_data["filename"],
                        storage_path=path,
                        mime_type=att_data["mime_type"],
                        size_bytes=size,
                        checksum=checksum,
                    )
                    db.add(attachment)
                except Exception as e:
                    logger.error(f"Failed to save attachment: {e}")

            await db.commit()

            # Notify admins
            await notify_admins(context.bot, case_id, category, description, is_anonymous)

        # Success message
        priority_map = {
            CasePriority.CRITICAL: "🔴 Kritik (24 soat)",
            CasePriority.HIGH: "🟠 Yuqori (72 soat)",
            CasePriority.MEDIUM: "🟡 O'rta (7 kun)",
            CasePriority.LOW: "🟢 Past (30 kun)",
        }
        priority = PRIORITY_BY_CATEGORY.get(category, CasePriority.MEDIUM)

        success_text = f"""
✅ *Murojaat muvaffaqiyatli yuborildi!*

📋 *Murojaat raqamingiz:* `{case_id}`
🔑 *Kuzatuv tokeni:* `{reporter_token}`

⚡ *Ustuvorlik:* {priority_map[priority]}
{"🔒 *Anonimlik:* Shaxsiyatingiz maxfiy saqlandi" if is_anonymous else "👤 *Anonimlik:* Yo'q"}

📬 *Javob qayerga keladi?*
Compliance departamenti javob yuborganida bu chatga xabar keladi.

ℹ️ _Murojaat raqamini saqlang — holat tekshirish uchun kerak bo'ladi._
        """
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")
            ]])
        )
    except Exception as e:
        logger.error(f"Error saving case: {e}")
        await query.edit_message_text(
            "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=get_main_keyboard()
        )

    context.user_data.clear()
    return MAIN_MENU


async def check_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    if not re.match(r"CASE-\d{8}-\d{5}", text):
        await update.message.reply_text(
            "⚠️ Noto'g'ri format. Masalan: `CASE-20251201-00001`",
            parse_mode=ParseMode.MARKDOWN
        )
        return CHECK_STATUS

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
        CaseStatus.NEW: "Yangi", CaseStatus.IN_PROGRESS: "Ko'rib chiqilmoqda",
        CaseStatus.NEEDS_INFO: "Qo'shimcha ma'lumot kerak",
        CaseStatus.COMPLETED: "Yakunlandi", CaseStatus.REJECTED: "Rad etildi",
        CaseStatus.ARCHIVED: "Arxivlandi"
    }

    reply = f"""
📋 *Murojaat holati*

*Raqam:* `{case.external_id}`
*Holat:* {status_emoji[case.status]} {status_text[case.status]}
*Kategoriya:* {case.category.value}
*Sana:* {case.created_at.strftime("%d.%m.%Y %H:%M")}
    """

    keyboard = [[InlineKeyboardButton("🏠 Bosh menyu", callback_data="home")]]
    if case.status == CaseStatus.NEEDS_INFO:
        keyboard.insert(0, [InlineKeyboardButton("💬 Javob yozish", callback_data=f"followup_{case.external_id}")])

    await update.message.reply_text(
        reply, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Bekor qilindi.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())
    return MAIN_MENU


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


def build_application() -> Application:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                MAIN_MENU: [CallbackQueryHandler(main_menu_callback)],
                CHOOSE_CATEGORY: [CallbackQueryHandler(choose_category)],
                ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
                ADD_ATTACHMENT: [
                    MessageHandler(filters.Document.ALL | filters.PHOTO, add_attachment),
                    CallbackQueryHandler(skip_attachment, pattern="skip_attachment"),
                ],
                CHOOSE_ANONYMOUS: [CallbackQueryHandler(choose_anonymous, pattern="anon_")],
                CONFIRM: [CallbackQueryHandler(confirm_send)],
                CHECK_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_status_handler)],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CommandHandler("start", start),
                CallbackQueryHandler(main_menu_callback, pattern="home"),
            ],
            per_user=True,
            per_chat=True,
            per_message=False,
        )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("getchatid", get_chat_id))
    return app
