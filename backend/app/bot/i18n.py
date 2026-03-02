"""
🌐 IntegrityBot — Ko'p-tillilik (i18n) moduli
=============================================

Qo'llab-quvvatlanadigan tillar:
  - uz  : O'zbek (asosiy)
  - ru  : Rus
  - en  : Ingliz

Ishlatish:
    from app.bot.i18n import t, get_user_lang, set_user_lang, SUPPORTED_LANGS

    # Tarjima olish:
    text = t("welcome", lang="uz")

    # Foydalanuvchi tilini saqlash (context.user_data da):
    lang = get_user_lang(context)
    set_user_lang(context, "ru")
"""

from typing import Optional
from telegram.ext import ContextTypes

# ── Qo'llab-quvvatlanadigan tillar ───────────────────────────────────────────
SUPPORTED_LANGS = ["uz", "ru", "en"]
DEFAULT_LANG = "uz"

LANG_FLAGS = {
    "uz": "🇺🇿 O'zbek",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

# ── Tarjimalar lug'ati ────────────────────────────────────────────────────────
TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── Xush kelibsiz ─────────────────────────────────────────────────────────
    "welcome": {
        "uz": (
            "🛡️ *Integrity Hotline Bot*\n\n"
            "Ushbu bot orqali siz xavfsiz va anonim tarzda muammo yoki "
            "qoidabuzarlik haqida xabar yuborishingiz mumkin.\n\n"
            "*Kafolatlar:*\n"
            "✅ To'liq anonimlik (istalsa)\n"
            "✅ Xabaringiz shifrlangan holda saqlanadi\n"
            "✅ Compliance departamenti darhol xabardor bo'ladi\n"
            "✅ 7 ish kuni ichida ko'rib chiqiladi\n\n"
            "Nima qilishni istaysiz?"
        ),
        "ru": (
            "🛡️ *Integrity Hotline Bot*\n\n"
            "С помощью этого бота вы можете безопасно и анонимно сообщить "
            "о проблеме или нарушении.\n\n"
            "*Гарантии:*\n"
            "✅ Полная анонимность (по желанию)\n"
            "✅ Ваше сообщение хранится в зашифрованном виде\n"
            "✅ Отдел комплаенс немедленно уведомляется\n"
            "✅ Рассматривается в течение 7 рабочих дней\n\n"
            "Что вы хотите сделать?"
        ),
        "en": (
            "🛡️ *Integrity Hotline Bot*\n\n"
            "Use this bot to safely and anonymously report a problem "
            "or compliance violation.\n\n"
            "*Guarantees:*\n"
            "✅ Full anonymity (if desired)\n"
            "✅ Your message is stored encrypted\n"
            "✅ Compliance department is notified immediately\n"
            "✅ Reviewed within 7 business days\n\n"
            "What would you like to do?"
        ),
    },

    # ── Yordam ────────────────────────────────────────────────────────────────
    "help": {
        "uz": (
            "ℹ️ *Integrity Hotline Bot — Yordam*\n\n"
            "*Asosiy buyruqlar:*\n"
            "/start — Bosh menyuga qaytish\n"
            "/help — Ushbu yordam sahifasi\n"
            "/cancel — Joriy jarayonni bekor qilish\n"
            "/lang — Tilni o'zgartirish\n\n"
            "*Nima qila olaman?*\n"
            "📝 *Murojaat yuborish* — Qoidabuzarlik haqida xabar bering\n"
            "🔍 *Holat tekshirish* — Murojaatingiz statusini ko'ring\n"
            "💬 *Javob yuborish* — Adminga qo'shimcha ma'lumot yuboring\n\n"
            "*Anonimlik haqida:*\n"
            "Anonim yuborishni tanlasangiz, shaxsiyatingiz hech qanday "
            "tizimda saqlanmaydi.\n\n"
            "*Muammo yuzaga keldimi?*\n"
            "compliance@company.uz manziliga yozing."
        ),
        "ru": (
            "ℹ️ *Integrity Hotline Bot — Помощь*\n\n"
            "*Основные команды:*\n"
            "/start — Вернуться в главное меню\n"
            "/help — Эта страница помощи\n"
            "/cancel — Отменить текущий процесс\n"
            "/lang — Изменить язык\n\n"
            "*Что я могу?*\n"
            "📝 *Отправить обращение* — Сообщите о нарушении\n"
            "🔍 *Проверить статус* — Узнайте статус вашего обращения\n"
            "💬 *Отправить ответ* — Дополнительная информация администратору\n\n"
            "*Об анонимности:*\n"
            "Если вы выберете анонимность, ваша личность нигде не сохраняется.\n\n"
            "*Возникли проблемы?*\n"
            "Напишите на compliance@company.uz"
        ),
        "en": (
            "ℹ️ *Integrity Hotline Bot — Help*\n\n"
            "*Main commands:*\n"
            "/start — Return to main menu\n"
            "/help — This help page\n"
            "/cancel — Cancel current process\n"
            "/lang — Change language\n\n"
            "*What can I do?*\n"
            "📝 *Submit report* — Report a violation\n"
            "🔍 *Check status* — View your report status\n"
            "💬 *Send reply* — Send additional info to admin\n\n"
            "*About anonymity:*\n"
            "If you choose anonymity, your identity is never stored anywhere.\n\n"
            "*Having issues?*\n"
            "Write to compliance@company.uz"
        ),
    },

    # ── Kategoriya tanlash ────────────────────────────────────────────────────
    "choose_category": {
        "uz": "📋 *Murojaat kategoriyasini tanlang:*\n\nEng mos kategoriyani belgilang. Bu murojaat ustuvorligini belgilashga yordam beradi.",
        "ru": "📋 *Выберите категорию обращения:*\n\nВыберите наиболее подходящую категорию. Это поможет определить приоритет обращения.",
        "en": "📋 *Select report category:*\n\nChoose the most appropriate category. This helps determine the priority of the report.",
    },

    # ── Tavsif kiritish ───────────────────────────────────────────────────────
    "enter_description": {
        "uz": (
            "✍️ *Voqeani batafsil tasvirlang:*\n\n"
            "• Kim, qachon, qayerda?\n"
            "• Qanday qoidabuzarlik?\n"
            "• Guvohlar bormi?\n\n"
            "_Qancha batafsil bo'lsa, ko'rib chiqish shuncha tezroq bo'ladi._\n\n"
            "*(Minimum 20, maksimum 5000 belgi)*"
        ),
        "ru": (
            "✍️ *Опишите ситуацию подробно:*\n\n"
            "• Кто, когда, где?\n"
            "• Какое нарушение?\n"
            "• Есть ли свидетели?\n\n"
            "_Чем подробнее, тем быстрее рассмотрение._\n\n"
            "*(Минимум 20, максимум 5000 символов)*"
        ),
        "en": (
            "✍️ *Describe the incident in detail:*\n\n"
            "• Who, when, where?\n"
            "• What violation occurred?\n"
            "• Are there any witnesses?\n\n"
            "_The more detailed, the faster the review._\n\n"
            "*(Minimum 20, maximum 5000 characters)*"
        ),
    },

    # ── Fayl biriktirish ──────────────────────────────────────────────────────
    "attach_file": {
        "uz": (
            "📎 *Dalil fayllarini biriktiring (ixtiyoriy):*\n\n"
            "Rasm, PDF, Word, Excel — maksimal 20 MB, 5 ta fayl.\n\n"
            "Fayl yo'q bo'lsa — davom eting."
        ),
        "ru": (
            "📎 *Прикрепите доказательства (необязательно):*\n\n"
            "Фото, PDF, Word, Excel — максимум 20 МБ, 5 файлов.\n\n"
            "Если файлов нет — продолжайте."
        ),
        "en": (
            "📎 *Attach evidence files (optional):*\n\n"
            "Photo, PDF, Word, Excel — max 20 MB, 5 files.\n\n"
            "If no files — continue."
        ),
    },

    # ── Anonimlik ─────────────────────────────────────────────────────────────
    "choose_anonymous": {
        "uz": "🔒 *Anonimlik sozlamalari*\n\nMurojaat anonim yuborilsin?",
        "ru": "🔒 *Настройки анонимности*\n\nОтправить обращение анонимно?",
        "en": "🔒 *Anonymity settings*\n\nSubmit report anonymously?",
    },

    "anon_yes": {
        "uz": "✅ Ha, anonim yuborish",
        "ru": "✅ Да, анонимно",
        "en": "✅ Yes, anonymously",
    },

    "anon_no": {
        "uz": "👤 Yo'q, ma'lumotlarimni qoldirmoqchiman",
        "ru": "👤 Нет, хочу оставить данные",
        "en": "👤 No, include my details",
    },

    # ── Tasdiqlash ────────────────────────────────────────────────────────────
    "confirm_title": {
        "uz": "📋 *Murojaat xulosasi*",
        "ru": "📋 *Сводка обращения*",
        "en": "📋 *Report summary*",
    },

    "confirm_send_btn": {
        "uz": "✅ Tasdiqlash va yuborish",
        "ru": "✅ Подтвердить и отправить",
        "en": "✅ Confirm and submit",
    },

    "edit_restart_btn": {
        "uz": "✏️ Qayta tahrirlash",
        "ru": "✏️ Редактировать заново",
        "en": "✏️ Edit again",
    },

    "cancel_btn": {
        "uz": "❌ Bekor qilish",
        "ru": "❌ Отмена",
        "en": "❌ Cancel",
    },

    # ── Muvaffaqiyatli yuborildi ───────────────────────────────────────────────
    "case_submitted": {
        "uz": (
            "✅ *Murojaatingiz qabul qilindi!*\n\n"
            "📋 Murojaat raqami: `{case_id}`\n\n"
            "🔐 Maxfiy token: `{token}`\n\n"
            "⚠️ *Ushbu tokenni xavfsiz joyda saqlang!* "
            "Keyinchalik holat tekshirish va javob yuborish uchun kerak bo'ladi.\n\n"
            "⏱ Ko'rib chiqish muddati: *7 ish kuni*"
        ),
        "ru": (
            "✅ *Ваше обращение принято!*\n\n"
            "📋 Номер обращения: `{case_id}`\n\n"
            "🔐 Секретный токен: `{token}`\n\n"
            "⚠️ *Сохраните этот токен в надёжном месте!* "
            "Он понадобится для проверки статуса и отправки ответа.\n\n"
            "⏱ Срок рассмотрения: *7 рабочих дней*"
        ),
        "en": (
            "✅ *Your report has been submitted!*\n\n"
            "📋 Report ID: `{case_id}`\n\n"
            "🔐 Secret token: `{token}`\n\n"
            "⚠️ *Keep this token in a safe place!* "
            "You will need it to check status and send follow-ups.\n\n"
            "⏱ Review period: *7 business days*"
        ),
    },

    # ── Holat tekshirish ──────────────────────────────────────────────────────
    "enter_case_id": {
        "uz": "🔍 *Murojaat raqamingizni kiriting:*\n\nMasalan: `CASE-20251201-00001`",
        "ru": "🔍 *Введите номер обращения:*\n\nНапример: `CASE-20251201-00001`",
        "en": "🔍 *Enter your report ID:*\n\nExample: `CASE-20251201-00001`",
    },

    "case_not_found": {
        "uz": "❌ *Murojaat topilmadi.*\n\nID: `{case_id}`\n\nRaqamni to'g'ri kiritganingizni tekshiring.",
        "ru": "❌ *Обращение не найдено.*\n\nID: `{case_id}`\n\nПроверьте правильность введённого номера.",
        "en": "❌ *Report not found.*\n\nID: `{case_id}`\n\nPlease verify the report ID.",
    },

    "invalid_case_id_format": {
        "uz": "⚠️ Noto'g'ri format. Masalan: `CASE-20251201-00001`",
        "ru": "⚠️ Неверный формат. Например: `CASE-20251201-00001`",
        "en": "⚠️ Invalid format. Example: `CASE-20251201-00001`",
    },

    # ── Bekor qilish ──────────────────────────────────────────────────────────
    "cancelled": {
        "uz": "❌ Bekor qilindi. Bosh menyuga qaytdingiz.",
        "ru": "❌ Отменено. Вы вернулись в главное меню.",
        "en": "❌ Cancelled. You've returned to the main menu.",
    },

    # ── Til tanlash ───────────────────────────────────────────────────────────
    "choose_language": {
        "uz": "🌐 *Tilni tanlang / Выберите язык / Choose language:*",
        "ru": "🌐 *Tilni tanlang / Выберите язык / Choose language:*",
        "en": "🌐 *Tilni tanlang / Выберите язык / Choose language:*",
    },

    "language_changed": {
        "uz": "✅ Til o'zgartirildi: 🇺🇿 O'zbek",
        "ru": "✅ Язык изменён: 🇷🇺 Русский",
        "en": "✅ Language changed: 🇬🇧 English",
    },

    # ── Tugmalar ──────────────────────────────────────────────────────────────
    "btn_report": {
        "uz": "📝 Murojaat yuborish",
        "ru": "📝 Отправить обращение",
        "en": "📝 Submit report",
    },

    "btn_check_status": {
        "uz": "🔍 Murojaat holatini tekshirish",
        "ru": "🔍 Проверить статус обращения",
        "en": "🔍 Check report status",
    },

    "btn_followup": {
        "uz": "💬 Adminga javob yozish",
        "ru": "💬 Написать ответ администратору",
        "en": "💬 Reply to admin",
    },

    "btn_my_cases": {
        "uz": "📂 Mening murojaatlarim",
        "ru": "📂 Мои обращения",
        "en": "📂 My reports",
    },

    "btn_faq": {
        "uz": "❓ FAQ / Ko'p so'raladigan savollar",
        "ru": "❓ FAQ / Часто задаваемые вопросы",
        "en": "❓ FAQ / Frequently asked questions",
    },

    "btn_contacts": {
        "uz": "📞 Aloqa ma'lumotlari",
        "ru": "📞 Контактная информация",
        "en": "📞 Contact information",
    },

    "btn_home": {
        "uz": "🏠 Bosh menyu",
        "ru": "🏠 Главное меню",
        "en": "🏠 Main menu",
    },

    "btn_settings": {
        "uz": "⚙️ Sozlamalar",
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
    },

    "btn_help": {
        "uz": "❓ Yordam",
        "ru": "❓ Помощь",
        "en": "❓ Help",
    },

    "btn_skip_attachment": {
        "uz": "➡️ Fayl qo'shmasdan davom etish",
        "ru": "➡️ Продолжить без файла",
        "en": "➡️ Continue without file",
    },

    "btn_continue": {
        "uz": "➡️ Davom etish",
        "ru": "➡️ Продолжить",
        "en": "➡️ Continue",
    },

    # ── Rate limit xabarlari ──────────────────────────────────────────────────
    "rate_limit_exceeded": {
        "uz": "⏳ *Juda ko'p so'rov yuborildi.*\n\n{time_str}dan keyin urinib ko'ring.",
        "ru": "⏳ *Слишком много запросов.*\n\nПовторите попытку через {time_str}.",
        "en": "⏳ *Too many requests.*\n\nPlease try again in {time_str}.",
    },

    "rate_limit_report": {
        "uz": "⏳ *Juda ko'p murojaat yuborildi.*\n\n{time_str}dan keyin urinib ko'ring.\n_Limit: 5 ta murojaat / 5 daqiqa_",
        "ru": "⏳ *Слишком много обращений.*\n\nПовторите через {time_str}.\n_Лимит: 5 обращений / 5 минут_",
        "en": "⏳ *Too many reports submitted.*\n\nTry again in {time_str}.\n_Limit: 5 reports / 5 minutes_",
    },

    # ── Xato xabarlari ────────────────────────────────────────────────────────
    "error_generic": {
        "uz": "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
        "ru": "❌ Произошла ошибка. Пожалуйста, попробуйте снова.",
        "en": "❌ An error occurred. Please try again.",
    },

    "description_too_short": {
        "uz": "⚠️ Tavsif juda qisqa. Iltimos, kamida 20 belgi kiriting.",
        "ru": "⚠️ Описание слишком короткое. Введите не менее 20 символов.",
        "en": "⚠️ Description too short. Please enter at least 20 characters.",
    },

    "description_too_long": {
        "uz": "⚠️ Tavsif juda uzun. Maksimal 5000 belgi.",
        "ru": "⚠️ Описание слишком длинное. Максимум 5000 символов.",
        "en": "⚠️ Description too long. Maximum 5000 characters.",
    },

    "no_cases_yet": {
        "uz": "📭 *Sizda hali murojaatlar yo'q.*\n\nMurojaat yuborish uchun «📝 Murojaat yuborish» tugmasini bosing.",
        "ru": "📭 *У вас пока нет обращений.*\n\nНажмите «📝 Отправить обращение» для подачи.",
        "en": "📭 *You have no reports yet.*\n\nPress «📝 Submit report» to get started.",
    },

    # ── Kategoriyalar ─────────────────────────────────────────────────────────
    "category_corruption": {
        "uz": "🔴 Korrupsiya / Pora",
        "ru": "🔴 Коррупция / Взятка",
        "en": "🔴 Corruption / Bribery",
    },

    "category_conflict": {
        "uz": "⚖️ Manfaatlar to'qnashuvi",
        "ru": "⚖️ Конфликт интересов",
        "en": "⚖️ Conflict of interest",
    },

    "category_fraud": {
        "uz": "💸 Firibgarlik / O'g'irlik",
        "ru": "💸 Мошенничество / Хищение",
        "en": "💸 Fraud / Theft",
    },

    "category_safety": {
        "uz": "⚠️ Xavfsizlik buzilishi",
        "ru": "⚠️ Нарушение безопасности",
        "en": "⚠️ Safety violation",
    },

    "category_discrimination": {
        "uz": "🚫 Kamsitish / Bezovtalik",
        "ru": "🚫 Дискриминация / Преследование",
        "en": "🚫 Discrimination / Harassment",
    },

    "category_procurement": {
        "uz": "📋 Tender buzilishi",
        "ru": "📋 Нарушение тендера",
        "en": "📋 Procurement violation",
    },

    "category_other": {
        "uz": "❓ Boshqa",
        "ru": "❓ Другое",
        "en": "❓ Other",
    },

    # ── Qo'shimcha kalitlar (settings, language) ──────────────────────────────
    "btn_language": {
        "uz": "🌐 Til tanlash",
        "ru": "🌐 Выбор языка",
        "en": "🌐 Choose language",
    },

    "followup_enter_id": {
        "uz": "💬 *Adminga javob yozish*\n\nMurojaat raqamingizni kiriting:\n`CASE-YYYYMMDD-XXXXX`",
        "ru": "💬 *Написать ответ администратору*\n\nВведите номер обращения:\n`CASE-YYYYMMDD-XXXXX`",
        "en": "💬 *Reply to admin*\n\nEnter your report number:\n`CASE-YYYYMMDD-XXXXX`",
    },

    "settings_info": {
        "uz": (
            "⚙️ *Sozlamalar*\n\n"
            "🌐 *Til:* Quyidagi tugma orqali tilni o'zgartiring.\n\n"
            "📬 *Telegram Webhook ulash:*\n"
            "Admin panel → Sozlamalar sahifasidan ulang.\n\n"
            "📞 *Muammo bo'lsa:*\ncompliance@company.uz"
        ),
        "ru": (
            "⚙️ *Настройки*\n\n"
            "🌐 *Язык:* Измените язык с помощью кнопки ниже.\n\n"
            "📬 *Подключение Telegram Webhook:*\n"
            "Панель администратора → страница Настройки.\n\n"
            "📞 *Возникли проблемы?*\ncompliance@company.uz"
        ),
        "en": (
            "⚙️ *Settings*\n\n"
            "🌐 *Language:* Change language using the button below.\n\n"
            "📬 *Telegram Webhook setup:*\n"
            "Admin panel → Settings page.\n\n"
            "📞 *Need help?*\ncompliance@company.uz"
        ),
    },
}


# ── Yordamchi funksiyalar ─────────────────────────────────────────────────────

def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    Tarjima qaytaradi.

    Args:
        key:    TRANSLATIONS lug'atidagi kalit
        lang:   Til kodi ("uz", "ru", "en"). None bo'lsa DEFAULT_LANG
        **kwargs: Format parametrlari (masalan: case_id=..., time_str=...)

    Returns:
        Tarjima qilingan matn. Kalit topilmasa — keyni qaytaradi.
    """
    lang = lang or DEFAULT_LANG
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    translations = TRANSLATIONS.get(key, {})
    text = translations.get(lang) or translations.get(DEFAULT_LANG) or key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def get_user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Foydalanuvchining tilini context.user_data dan qaytaradi.
    Saqlanmagan bo'lsa — DEFAULT_LANG qaytaradi.
    """
    return context.user_data.get("lang", DEFAULT_LANG)


def set_user_lang(context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """
    Foydalanuvchining tilini context.user_data ga saqlaydi.
    Noto'g'ri til berilsa — DEFAULT_LANG ishlatiladi.
    """
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    context.user_data["lang"] = lang


def get_language_keyboard():
    """Til tanlash uchun inline keyboard."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = [
        [InlineKeyboardButton(flag, callback_data=f"lang_{code}")]
        for code, flag in LANG_FLAGS.items()
    ]
    return InlineKeyboardMarkup(buttons)

