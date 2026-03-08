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

    # ── Bekor qilish (eski, orqaga muvofiqlik uchun) ──────────────────────────
    "cancelled_short": {
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

    # ── Fallback va xato kalitlar ─────────────────────────────────────────────
    "unknown_command": {
        "uz": (
            "🤔 *Kechirasiz, bu buyruqni tushunmadim.*\n\n"
            "Nima qilishni istaysiz?"
        ),
        "ru": (
            "🤔 *Извините, я не понял эту команду.*\n\n"
            "Что вы хотите сделать?"
        ),
        "en": (
            "🤔 *Sorry, I didn't understand that command.*\n\n"
            "What would you like to do?"
        ),
    },

    "invalid_input_in_state": {
        "uz": "⚠️ Iltimos, tugmalardan foydalaning yoki /cancel bosing.",
        "ru": "⚠️ Пожалуйста, используйте кнопки или нажмите /cancel.",
        "en": "⚠️ Please use the buttons or press /cancel.",
    },

    "text_too_short": {
        "uz": "⚠️ Matn juda qisqa (minimum 20 belgi). Hozir: *{length}/20*\n\nIltimos, batafsil yozing.",
        "ru": "⚠️ Текст слишком короткий (минимум 20 символов). Сейчас: *{length}/20*\n\nПожалуйста, напишите подробнее.",
        "en": "⚠️ Text too short (minimum 20 characters). Current: *{length}/20*\n\nPlease write in more detail.",
    },

    "text_too_long": {
        "uz": "⚠️ Matn juda uzun (maksimum 5000 belgi). Hozir: *{length}/5000*\n\nIltimos, qisqartiring.",
        "ru": "⚠️ Текст слишком длинный (максимум 5000 символов). Сейчас: *{length}/5000*\n\nПожалуйста, сократите.",
        "en": "⚠️ Text too long (maximum 5000 characters). Current: *{length}/5000*\n\nPlease shorten it.",
    },

    "welcome_new": {
        "uz": (
            "👋 *Xush kelibsiz, yangi foydalanuvchi!*\n\n"
            "Bu bot orqali qoidabuzarliklar haqida *xavfsiz va anonim* murojaat qilishingiz mumkin.\n\n"
            "📌 Murojaat yuborish: «📝 Murojaat yuborish» tugmasi\n"
            "📌 Holat tekshirish: «🔍 Holatni tekshirish» tugmasi\n"
            "📌 Yordam: /help\n\n"
            "🔒 Barcha murojaatlar *AES-256* shifrlangan holda saqlanadi.\n"
            "✅ Anonimlik to'liq kafolatlanadi.\n\n"
            "Nima qilishni istaysiz?"
        ),
        "ru": (
            "👋 *Добро пожаловать, новый пользователь!*\n\n"
            "Через этот бот вы можете *безопасно и анонимно* сообщить о нарушениях.\n\n"
            "📌 Подать обращение: кнопка «📝 Отправить обращение»\n"
            "📌 Проверить статус: кнопка «🔍 Проверить статус»\n"
            "📌 Помощь: /help\n\n"
            "🔒 Все обращения хранятся в зашифрованном виде (*AES-256*).\n"
            "✅ Анонимность полностью гарантируется.\n\n"
            "Что вы хотите сделать?"
        ),
        "en": (
            "👋 *Welcome, new user!*\n\n"
            "You can use this bot to *safely and anonymously* report violations.\n\n"
            "📌 Submit report: «📝 Submit report» button\n"
            "📌 Check status: «🔍 Check status» button\n"
            "📌 Help: /help\n\n"
            "🔒 All reports are stored encrypted (*AES-256*).\n"
            "✅ Full anonymity is guaranteed.\n\n"
            "What would you like to do?"
        ),
    },

    "welcome_returning": {
        "uz": (
            "🛡️ *Integrity Hotline Bot*\n\n"
            "Qaytib kelganingiz uchun rahmat!\n\n"
            "Nima qilishni istaysiz?"
        ),
        "ru": (
            "🛡️ *Integrity Hotline Bot*\n\n"
            "С возвращением!\n\n"
            "Что вы хотите сделать?"
        ),
        "en": (
            "🛡️ *Integrity Hotline Bot*\n\n"
            "Welcome back!\n\n"
            "What would you like to do?"
        ),
    },

    "group_redirect": {
        "uz": (
            "ℹ️ Bu bot shaxsiy murojaat uchun mo'ljallangan.\n\n"
            "Anonim murojaat yuborish uchun bevosita botga yozing:\n"
            "@IntegrityBot"
        ),
        "ru": (
            "ℹ️ Этот бот предназначен для личных обращений.\n\n"
            "Для отправки анонимного обращения напишите боту напрямую:\n"
            "@IntegrityBot"
        ),
        "en": (
            "ℹ️ This bot is designed for personal reports.\n\n"
            "To submit an anonymous report, write to the bot directly:\n"
            "@IntegrityBot"
        ),
    },

    "technical_error": {
        "uz": (
            "😔 *Texnik nosozlik yuz berdi.*\n\n"
            "Iltimos, birozdan keyin urinib ko'ring.\n"
            "Muammo davom etsa: /start buyrug'ini bering."
        ),
        "ru": (
            "😔 *Произошла техническая ошибка.*\n\n"
            "Пожалуйста, повторите попытку чуть позже.\n"
            "Если проблема сохраняется: введите /start."
        ),
        "en": (
            "😔 *A technical error occurred.*\n\n"
            "Please try again in a moment.\n"
            "If the issue persists: use the /start command."
        ),
    },

    "cancelled": {
        "uz": (
            "❌ *Bekor qilindi.*\n\n"
            "Murojaat saqlanmadi.\n"
            "Bosh menyudan davom etishingiz mumkin."
        ),
        "ru": (
            "❌ *Отменено.*\n\n"
            "Обращение не сохранено.\n"
            "Вы можете продолжить из главного меню."
        ),
        "en": (
            "❌ *Cancelled.*\n\n"
            "Report was not saved.\n"
            "You can continue from the main menu."
        ),
    },

    "choose_category_invalid": {
        "uz": "⚠️ Iltimos, ro'yxatdan kategoriya tanlang yoki /cancel bosing.",
        "ru": "⚠️ Пожалуйста, выберите категорию из списка или нажмите /cancel.",
        "en": "⚠️ Please select a category from the list or press /cancel.",
    },

    # ── Qo'shimcha kalitlar (settings, language) ──────────────────────────────
    "btn_language": {
        "uz": "🌐 Til tanlash",
        "ru": "🌐 Выбор языка",
        "en": "🌐 Choose language",
    },

    # ── Persistent reply keyboard tugmalari ───────────────────────────────────
    "menu_submit": {
        "uz": "📝 Murojaat yuborish",
        "ru": "📝 Отправить обращение",
        "en": "📝 Submit report",
    },
    "menu_check_status": {
        "uz": "🔍 Holatni tekshirish",
        "ru": "🔍 Проверить статус",
        "en": "🔍 Check status",
    },
    "menu_reply_admin": {
        "uz": "💬 Adminga javob",
        "ru": "💬 Ответить администратору",
        "en": "💬 Reply to admin",
    },
    "menu_my_cases": {
        "uz": "📂 Mening murojaatlarim",
        "ru": "📂 Мои обращения",
        "en": "📂 My reports",
    },
    "menu_help": {
        "uz": "❓ Yordam",
        "ru": "❓ Помощь",
        "en": "❓ Help",
    },
    "menu_settings": {
        "uz": "⚙️ Sozlamalar",
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
    },

    "followup_enter_id": {
        "uz": "💬 *Adminga javob yozish*\n\nMurojaat raqamingizni kiriting:\n`CASE-YYYYMMDD-XXXXX`",
        "ru": "💬 *Написать ответ администратору*\n\nВведите номер обращения:\n`CASE-YYYYMMDD-XXXXX`",
        "en": "💬 *Reply to admin*\n\nEnter your report number:\n`CASE-YYYYMMDD-XXXXX`",
    },

    "settings_info": {
        "uz": (
            "⚙️ *Sozlamalar*\n\n"
            "🌐 *Til:* Quyidagi tugma orqali tilni o'zgartiring."
        ),
        "ru": (
            "⚙️ *Настройки*\n\n"
            "🌐 *Язык:* Измените язык с помощью кнопки ниже."
        ),
        "en": (
            "⚙️ *Settings*\n\n"
            "🌐 *Language:* Change language using the button below."
        ),
    },
    # ── Admin xush kelibsiz ───────────────────────────────────────────────────
    "admin_welcome": {
        "uz": "👋 *Xush kelibsiz, Admin!*\n\n📊 Quyidagi admin tugmalardan foydalaning:",
        "ru": "👋 *Добро пожаловать, Admin!*\n\n📊 Используйте кнопки администратора:",
        "en": "👋 *Welcome, Admin!*\n\n📊 Use the admin buttons below:",
    },

    "investigator_welcome": {
        "uz": "👋 *Xush kelibsiz!*\n\n📋 Quyidagi tugmalardan foydalaning:",
        "ru": "👋 *Добро пожаловать!*\n\n📋 Используйте кнопки ниже:",
        "en": "👋 *Welcome!*\n\n📋 Use the buttons below:",
    },

    "menu_hint": {
        "uz": "👇 Quyidagi tugmalardan foydalaning:",
        "ru": "👇 Используйте кнопки ниже:",
        "en": "👇 Use the buttons below:",
    },

    # ── Telegram link ─────────────────────────────────────────────────────────
    "link_expired": {
        "uz": "❌ *Havola yaroqsiz yoki muddati o'tgan.*\n\nAdmin paneldan yangi havola oling.",
        "ru": "❌ *Ссылка недействительна или истекла.*\n\nПолучите новую ссылку в панели администратора.",
        "en": "❌ *Link is invalid or expired.*\n\nGet a new link from the admin panel.",
    },

    "user_not_found": {
        "uz": "❌ Foydalanuvchi topilmadi.",
        "ru": "❌ Пользователь не найден.",
        "en": "❌ User not found.",
    },

    "tg_already_linked": {
        "uz": "⚠️ *Bu Telegram akkaunt boshqa foydalanuvchiga bog'langan.*\n\nAvval u yerdan uzib, qayta urinib ko'ring.",
        "ru": "⚠️ *Этот Telegram аккаунт уже привязан к другому пользователю.*\n\nСначала отвяжите его и попробуйте снова.",
        "en": "⚠️ *This Telegram account is already linked to another user.*\n\nUnlink it first and try again.",
    },

    "tg_link_success": {
        "uz": "✅ *Muvaffaqiyatli bog'landi!*\n\n👤 Admin panel: *{display_name}*\n📱 Telegram: @{username}\n\nEndi admin panelidan tayinlangan murojaatlar haqida xabar olasiz.",
        "ru": "✅ *Успешно привязано!*\n\n👤 Панель администратора: *{display_name}*\n📱 Telegram: @{username}\n\nТеперь вы будете получать уведомления о назначенных обращениях.",
        "en": "✅ *Successfully linked!*\n\n👤 Admin panel: *{display_name}*\n📱 Telegram: @{username}\n\nYou will now receive notifications about assigned cases.",
    },

    "tg_link_error": {
        "uz": "❌ Bog'lashda xatolik yuz berdi. Qayta urinib ko'ring.",
        "ru": "❌ Ошибка привязки. Повторите попытку.",
        "en": "❌ Linking error. Please try again.",
    },

    # ── Admin yordam ──────────────────────────────────────────────────────────
    "admin_help_extra": {
        "uz": (
            "\n\n*📊 Admin buyruqlar:*\n"
            "/stats — Bugungi statistika\n"
            "/overdue — Muddati o'tganlar\n"
            "/mine — Mening murojaatlarim\n"
            "/search — Murojaat qidirish\n"
            "/note — Ichki izoh qo'shish (guruhda)"
        ),
        "ru": (
            "\n\n*📊 Команды администратора:*\n"
            "/stats — Сегодняшняя статистика\n"
            "/overdue — Просроченные\n"
            "/mine — Мои обращения\n"
            "/search — Поиск обращений\n"
            "/note — Добавить внутреннюю заметку (в группе)"
        ),
        "en": (
            "\n\n*📊 Admin commands:*\n"
            "/stats — Today's statistics\n"
            "/overdue — Overdue cases\n"
            "/mine — My cases\n"
            "/search — Search cases\n"
            "/note — Add internal note (in group)"
        ),
    },

    # ── FAQ ───────────────────────────────────────────────────────────────────
    "faq": {
        "uz": (
            "❓ *Ko'p so'raladigan savollar*\n\n"
            "*Mening shaxsiyatim oshkor bo'ladimi?*\n"
            "Yo'q. Siz anonim yuborishni tanlasangiz, botimiz hech qanday shaxsiy ma'lumot saqlamaydi.\n\n"
            "*Murojaat qancha vaqtda ko'rib chiqiladi?*\n"
            "• 🔴 Kritik: 24 soat ichida\n"
            "• 🟠 Yuqori: 72 soat ichida\n"
            "• 🟡 O'rta: 7 kun ichida\n"
            "• 🟢 Past: 30 kun ichida\n\n"
            "*Fayl yuborishim mumkinmi?*\n"
            "Ha, rasm va hujjatlar (20 MB gacha) yuborishingiz mumkin.\n\n"
            "*Murojaat holatini qanday bilaman?*\n"
            "Murojaat ID raqamingizni bosh menyudan «Holat tekshirish» orqali kiriting.\n\n"
            "*Adminga qo'shimcha ma'lumot yuborishim mumkinmi?*\n"
            "Ha! «Adminga javob yozish» tugmasi orqali yoki status tekshirishda «Javob yozish» tugmasini bosing.\n\n"
            "*Nechta fayl biriktirish mumkin?*\n"
            "Bitta murojaat uchun 5 tagacha fayl (har biri 20 MB gacha)."
        ),
        "ru": (
            "❓ *Часто задаваемые вопросы*\n\n"
            "*Раскроется ли моя личность?*\n"
            "Нет. Если вы выбрали анонимность, бот не сохраняет никаких личных данных.\n\n"
            "*Как долго рассматривается обращение?*\n"
            "• 🔴 Критический: в течение 24 часов\n"
            "• 🟠 Высокий: в течение 72 часов\n"
            "• 🟡 Средний: в течение 7 дней\n"
            "• 🟢 Низкий: в течение 30 дней\n\n"
            "*Можно ли отправить файлы?*\n"
            "Да, фото и документы (до 20 МБ).\n\n"
            "*Как узнать статус обращения?*\n"
            "Введите ID обращения через «Проверить статус» в главном меню.\n\n"
            "*Можно ли отправить дополнительную информацию?*\n"
            "Да! Через кнопку «Написать ответ администратору» или «Отправить ответ» при проверке статуса.\n\n"
            "*Сколько файлов можно прикрепить?*\n"
            "До 5 файлов на одно обращение (каждый до 20 МБ)."
        ),
        "en": (
            "❓ *Frequently Asked Questions*\n\n"
            "*Will my identity be revealed?*\n"
            "No. If you chose anonymity, the bot stores no personal data.\n\n"
            "*How long until my report is reviewed?*\n"
            "• 🔴 Critical: within 24 hours\n"
            "• 🟠 High: within 72 hours\n"
            "• 🟡 Medium: within 7 days\n"
            "• 🟢 Low: within 30 days\n\n"
            "*Can I send files?*\n"
            "Yes, photos and documents (up to 20 MB).\n\n"
            "*How do I check my report status?*\n"
            "Enter your report ID via «Check status» in the main menu.\n\n"
            "*Can I send additional info to admin?*\n"
            "Yes! Use «Reply to admin» button or «Send reply» when checking status.\n\n"
            "*How many files can I attach?*\n"
            "Up to 5 files per report (each up to 20 MB)."
        ),
    },

    # ── Contacts ──────────────────────────────────────────────────────────────
    "contacts": {
        "uz": (
            "📞 *Compliance Departamenti*\n\n"
            "📧 Email: compliance@company.uz\n"
            "📱 Telefon: +998 XX XXX XX XX\n\n"
            "🕐 Ish vaqti: Du-Ju, 09:00-18:00\n\n"
            "_Shoshilinch holatlarda 24/7 ushbu bot orqali murojaat qiling._"
        ),
        "ru": (
            "📞 *Отдел комплаенс*\n\n"
            "📧 Email: compliance@company.uz\n"
            "📱 Телефон: +998 XX XXX XX XX\n\n"
            "🕐 Рабочие часы: Пн-Пт, 09:00-18:00\n\n"
            "_В экстренных случаях обращайтесь через этот бот 24/7._"
        ),
        "en": (
            "📞 *Compliance Department*\n\n"
            "📧 Email: compliance@company.uz\n"
            "📱 Phone: +998 XX XXX XX XX\n\n"
            "🕐 Working hours: Mon-Fri, 09:00-18:00\n\n"
            "_For urgent matters, use this bot 24/7._"
        ),
    },

    # ── Murojaat holatlari (foydalanuvchi uchun) ──────────────────────────────
    "mycase_not_found": {
        "uz": "❌ Murojaat topilmadi.",
        "ru": "❌ Обращение не найдено.",
        "en": "❌ Report not found.",
    },

    "case_status_new": {
        "uz": "Yangi — ko'rib chiqilishini kuting",
        "ru": "Новое — ожидает рассмотрения",
        "en": "New — awaiting review",
    },

    "case_status_in_progress": {
        "uz": "Ko'rib chiqilmoqda",
        "ru": "Рассматривается",
        "en": "In progress",
    },

    "case_status_needs_info": {
        "uz": "Qo'shimcha ma'lumot kerak",
        "ru": "Требуется дополнительная информация",
        "en": "Additional info needed",
    },

    "case_status_completed": {
        "uz": "Yakunlandi",
        "ru": "Завершено",
        "en": "Completed",
    },

    "case_status_rejected": {
        "uz": "Rad etildi",
        "ru": "Отклонено",
        "en": "Rejected",
    },

    "case_status_archived": {
        "uz": "Arxivlandi",
        "ru": "Архивировано",
        "en": "Archived",
    },

    # ── Inline tugmalar ───────────────────────────────────────────────────────
    "btn_reply_admin": {
        "uz": "💬 Javob yozish",
        "ru": "💬 Написать ответ",
        "en": "💬 Send reply",
    },

    "btn_back": {
        "uz": "◀️ Orqaga",
        "ru": "◀️ Назад",
        "en": "◀️ Back",
    },

    "btn_submit_report": {
        "uz": "📝 Murojaat yuborish",
        "ru": "📝 Отправить обращение",
        "en": "📝 Submit report",
    },

    "mycase_list_title": {
        "uz": "📂 *Mening murojaatlarim* (so'nggi 10 ta):\n\nKo'rish uchun bosing:",
        "ru": "📂 *Мои обращения* (последние 10):\n\nНажмите для просмотра:",
        "en": "📂 *My reports* (last 10):\n\nTap to view:",
    },

    "case_detail_title": {
        "uz": "📋 *Murojaat: `{case_id}`*\n\n*Holat:* {status_emoji} {status_text}\n*Ustuvorlik:* {priority}\n*Kategoriya:* {category}\n*Yuborilgan:* {date}",
        "ru": "📋 *Обращение: `{case_id}`*\n\n*Статус:* {status_emoji} {status_text}\n*Приоритет:* {priority}\n*Категория:* {category}\n*Отправлено:* {date}",
        "en": "📋 *Report: `{case_id}`*\n\n*Status:* {status_emoji} {status_text}\n*Priority:* {priority}\n*Category:* {category}\n*Submitted:* {date}",
    },

    "case_deadline": {
        "uz": "\n*Muddat:* {date}",
        "ru": "\n*Срок:* {date}",
        "en": "\n*Deadline:* {date}",
    },

    "case_status_title": {
        "uz": "📋 *Murojaat holati*\n\n*Raqam:* `{case_id}`\n*Holat:* {status_emoji} {status_text}\n*Kategoriya:* {category}\n*Sana:* {date}",
        "ru": "📋 *Статус обращения*\n\n*Номер:* `{case_id}`\n*Статус:* {status_emoji} {status_text}\n*Категория:* {category}\n*Дата:* {date}",
        "en": "📋 *Report status*\n\n*ID:* `{case_id}`\n*Status:* {status_emoji} {status_text}\n*Category:* {category}\n*Date:* {date}",
    },

    "category_confirm": {
        "uz": (
            "✅ Kategoriya: *{cat_name}*\n\n"
            "📝 *Iltimos, muammo haqida batafsil yozing:*\n\n"
            "Quyidagilarni ko'rsating:\n"
            "• Kim, nima, qachon, qayerda\n"
            "• Dalillar (agar bo'lsa)\n"
            "• Qo'shimcha ma'lumotlar\n\n"
            "_Matnni quyida yozing (kamida 20 belgi):_"
        ),
        "ru": (
            "✅ Категория: *{cat_name}*\n\n"
            "📝 *Опишите проблему подробно:*\n\n"
            "Укажите:\n"
            "• Кто, что, когда, где\n"
            "• Доказательства (если есть)\n"
            "• Дополнительная информация\n\n"
            "_Введите текст ниже (минимум 20 символов):_"
        ),
        "en": (
            "✅ Category: *{cat_name}*\n\n"
            "📝 *Please describe the issue in detail:*\n\n"
            "Include:\n"
            "• Who, what, when, where\n"
            "• Evidence (if any)\n"
            "• Additional information\n\n"
            "_Type your message below (min 20 characters):_"
        ),
    },

    # ── Rate limit xabarlari (qo'shimcha) ─────────────────────────────────────
    "rate_limit_generic": {
        "uz": "⏳ Juda ko'p so'rov. {time_str}dan keyin urinib ko'ring.",
        "ru": "⏳ Слишком много запросов. Повторите через {time_str}.",
        "en": "⏳ Too many requests. Try again in {time_str}.",
    },

    "rate_limit_file": {
        "uz": "⏳ Juda ko'p fayl yuklandi. {retry_after} soniyadan keyin urinib ko'ring.",
        "ru": "⏳ Слишком много файлов. Повторите через {retry_after} секунд.",
        "en": "⏳ Too many files uploaded. Try again in {retry_after} seconds.",
    },

    # ── Fayl xabarlari ────────────────────────────────────────────────────────
    "max_files_reached": {
        "uz": "⚠️ Maksimal 5 ta fayl biriktirish mumkin.",
        "ru": "⚠️ Максимум 5 файлов.",
        "en": "⚠️ Maximum 5 files allowed.",
    },

    "blocked_file_type": {
        "uz": "❌ Bu turdagi fayl qabul qilinmaydi (.exe, .bat va boshqalar).\nRasm, PDF, Word, Excel fayllarini yuboring.",
        "ru": "❌ Этот тип файла не принимается (.exe, .bat и т.д.).\nОтправьте фото, PDF, Word или Excel.",
        "en": "❌ This file type is not accepted (.exe, .bat etc.).\nSend photos, PDF, Word or Excel files.",
    },

    "file_too_large": {
        "uz": "❌ Fayl hajmi 20 MB dan oshmasligi kerak.",
        "ru": "❌ Размер файла не должен превышать 20 МБ.",
        "en": "❌ File size must not exceed 20 MB.",
    },

    "file_added": {
        "uz": "✅ Fayl qo'shildi ({count}/5)\n\n{more_msg}\nDavom etish uchun tugmani bosing.",
        "ru": "✅ Файл добавлен ({count}/5)\n\n{more_msg}\nНажмите кнопку для продолжения.",
        "en": "✅ File added ({count}/5)\n\n{more_msg}\nPress the button to continue.",
    },

    "more_files_allowed": {
        "uz": "Yana {remaining} ta fayl qo'shishingiz mumkin.",
        "ru": "Можно добавить ещё {remaining} файл(а).",
        "en": "You can add {remaining} more file(s).",
    },

    "max_files_note": {
        "uz": "Maksimal songa yetdingiz.",
        "ru": "Вы достигли максимума.",
        "en": "You've reached the maximum.",
    },

    # ── Murojaat saqlash ──────────────────────────────────────────────────────
    "case_saving": {
        "uz": "⏳ Murojaat saqlanmoqda...",
        "ru": "⏳ Сохранение обращения...",
        "en": "⏳ Saving report...",
    },

    # ── Confirm summary ───────────────────────────────────────────────────────
    "confirm_summary": {
        "uz": (
            "📋 *Murojaat xulosasi*\n\n"
            "*Kategoriya:* {cat}\n"
            "*Anonimlik:* {anon}\n"
            "*Fayllar:* {att_count} ta\n\n"
            "*Tavsif:*\n_{desc}_\n\n"
            "Ushbu ma'lumotlar to'g'rimi?"
        ),
        "ru": (
            "📋 *Сводка обращения*\n\n"
            "*Категория:* {cat}\n"
            "*Анонимность:* {anon}\n"
            "*Файлы:* {att_count} шт.\n\n"
            "*Описание:*\n_{desc}_\n\n"
            "Данные верны?"
        ),
        "en": (
            "📋 *Report summary*\n\n"
            "*Category:* {cat}\n"
            "*Anonymity:* {anon}\n"
            "*Files:* {att_count}\n\n"
            "*Description:*\n_{desc}_\n\n"
            "Is this information correct?"
        ),
    },

    "anon_yes_label": {
        "uz": "✅ Anonim",
        "ru": "✅ Анонимно",
        "en": "✅ Anonymous",
    },

    "anon_no_label": {
        "uz": "❌ Anonim emas",
        "ru": "❌ Не анонимно",
        "en": "❌ Not anonymous",
    },

    "btn_confirm_send": {
        "uz": "✅ Tasdiqlash va yuborish",
        "ru": "✅ Подтвердить и отправить",
        "en": "✅ Confirm and submit",
    },

    "btn_edit_restart": {
        "uz": "✏️ Qayta tahrirlash",
        "ru": "✏️ Редактировать",
        "en": "✏️ Edit again",
    },

    "btn_cancel_all": {
        "uz": "❌ Bekor qilish",
        "ru": "❌ Отмена",
        "en": "❌ Cancel",
    },

    "invalid_description": {
        "uz": "✍️ Iltimos, murojaat matnini yozing (kamida 20 belgi).",
        "ru": "✍️ Пожалуйста, введите текст обращения (минимум 20 символов).",
        "en": "✍️ Please enter the report text (minimum 20 characters).",
    },

    "callback_error": {
        "uz": "😔 Texnik xato yuz berdi. /start bosing.",
        "ru": "😔 Техническая ошибка. Нажмите /start.",
        "en": "😔 Technical error. Press /start.",
    },

    # ── Follow-up ─────────────────────────────────────────────────────────────
    "followup_prompt": {
        "uz": (
            "💬 *Murojaat {case_id} bo'yicha xabar yozing:*\n\n"
            "Adminga qo'shimcha ma'lumot, tushuntirish yoki savolingizni yuboring.\n\n"
            "_Bekor qilish uchun /cancel yozing_"
        ),
        "ru": (
            "💬 *Напишите сообщение по обращению {case_id}:*\n\n"
            "Отправьте администратору дополнительную информацию, пояснение или вопрос.\n\n"
            "_Для отмены введите /cancel_"
        ),
        "en": (
            "💬 *Write a message about report {case_id}:*\n\n"
            "Send the admin additional info, clarification or a question.\n\n"
            "_Type /cancel to cancel_"
        ),
    },

    "followup_too_short": {
        "uz": "⚠️ Xabar juda qisqa. Iltimos, batafsil yozing.",
        "ru": "⚠️ Сообщение слишком короткое. Напишите подробнее.",
        "en": "⚠️ Message too short. Please write in more detail.",
    },

    "followup_case_missing": {
        "uz": "❌ Xatolik: murojaat ID si topilmadi. Qaytadan urinib ko'ring.",
        "ru": "❌ Ошибка: ID обращения не найден. Попробуйте снова.",
        "en": "❌ Error: report ID not found. Please try again.",
    },

    "followup_sent": {
        "uz": "✅ *Xabaringiz yuborildi!*\n\nMurojaat: `{case_id}`\n\nCompliance departamenti javob bilan siz bilan bog'lanadi.",
        "ru": "✅ *Сообщение отправлено!*\n\nОбращение: `{case_id}`\n\nОтдел комплаенс свяжется с вами.",
        "en": "✅ *Message sent!*\n\nReport: `{case_id}`\n\nThe compliance department will get back to you.",
    },

    # ── Check status xabarlari ─────────────────────────────────────────────────
    "case_status_wrong_format": {
        "uz": "⚠️ Noto'g'ri format. Masalan: `CASE-20251201-00001`",
        "ru": "⚠️ Неверный формат. Например: `CASE-20251201-00001`",
        "en": "⚠️ Invalid format. Example: `CASE-20251201-00001`",
    },

    "case_check_not_found": {
        "uz": "❌ Murojaat topilmadi. Raqamni to'g'ri kiritganingizni tekshiring.",
        "ru": "❌ Обращение не найдено. Проверьте правильность номера.",
        "en": "❌ Report not found. Please verify the report number.",
    },

    # ── Reminder xabarlari ────────────────────────────────────────────────────
    "reminder_needs_info": {
        "uz": (
            "🔔 *Eslatma — Murojaat {case_id}*\n\n"
            "Compliance departamenti sizdan qo'shimcha ma'lumot kutmoqda.\n\n"
            "Javob yuborish uchun:\n"
            "1️⃣ Bosh menyuga o'ting\n"
            "2️⃣ «Adminga javob yozish» ni bosing\n"
            "3️⃣ Murojaat raqamingizni kiriting: `{case_id}`\n\n"
            "_Agar javob 7 kun ichida kelmasa, murojaat yopilishi mumkin._"
        ),
        "ru": (
            "🔔 *Напоминание — Обращение {case_id}*\n\n"
            "Отдел комплаенс ожидает от вас дополнительную информацию.\n\n"
            "Чтобы ответить:\n"
            "1️⃣ Перейдите в главное меню\n"
            "2️⃣ Нажмите «Написать ответ администратору»\n"
            "3️⃣ Введите номер обращения: `{case_id}`\n\n"
            "_Если ответа не будет в течение 7 дней, обращение может быть закрыто._"
        ),
        "en": (
            "🔔 *Reminder — Report {case_id}*\n\n"
            "The compliance department is waiting for additional information from you.\n\n"
            "To reply:\n"
            "1️⃣ Go to the main menu\n"
            "2️⃣ Press «Reply to admin»\n"
            "3️⃣ Enter your report number: `{case_id}`\n\n"
            "_If no reply within 7 days, the report may be closed._"
        ),
    },

    "btn_write_reply": {
        "uz": "✍️ Javob yozish",
        "ru": "✍️ Написать ответ",
        "en": "✍️ Write reply",
    },

    "reminder_new_case": {
        "uz": (
            "📬 *Murojaat {case_id} haqida yangilik*\n\n"
            "Murojaatingiz hali ko'rib chiqilmoqda. "
            "Compliance departamenti tez orada siz bilan bog'lanadi.\n\n"
            "*Holat:* 🆕 Yangi\n"
            "*Yuborilgan:* {date}"
        ),
        "ru": (
            "📬 *Обновление по обращению {case_id}*\n\n"
            "Ваше обращение ещё рассматривается. "
            "Отдел комплаенс свяжется с вами в ближайшее время.\n\n"
            "*Статус:* 🆕 Новое\n"
            "*Отправлено:* {date}"
        ),
        "en": (
            "📬 *Update on report {case_id}*\n\n"
            "Your report is still under review. "
            "The compliance department will contact you soon.\n\n"
            "*Status:* 🆕 New\n"
            "*Submitted:* {date}"
        ),
    },

    # ── Admin menyu tugmalari ─────────────────────────────────────────────────
    "admin_menu_stats": {
        "uz": "📊 Statistika",
        "ru": "📊 Статистика",
        "en": "📊 Statistics",
    },

    "admin_menu_new_cases": {
        "uz": "🔔 Yangi murojaatlar",
        "ru": "🔔 Новые обращения",
        "en": "🔔 New cases",
    },

    "admin_menu_deadline": {
        "uz": "⏰ Deadline yaqin",
        "ru": "⏰ Дедлайн близко",
        "en": "⏰ Deadline near",
    },

    "admin_menu_overdue": {
        "uz": "🚨 Muddati o'tgan",
        "ru": "🚨 Просроченные",
        "en": "🚨 Overdue",
    },

    "admin_menu_my_cases": {
        "uz": "📋 Mening murojaatlarim",
        "ru": "📋 Мои обращения",
        "en": "📋 My cases",
    },

    "admin_menu_team": {
        "uz": "👥 Jamoam",
        "ru": "👥 Моя команда",
        "en": "👥 My team",
    },

    "admin_menu_report_settings": {
        "uz": "⚙️ Hisobot sozlamalari",
        "ru": "⚙️ Настройки отчётов",
        "en": "⚙️ Report settings",
    },

    "admin_menu_standard": {
        "uz": "🏠 Standart menyu",
        "ru": "🏠 Стандартное меню",
        "en": "🏠 Standard menu",
    },

    "investigator_menu_new_assign": {
        "uz": "🔔 Yangi tayinlovlar",
        "ru": "🔔 Новые назначения",
        "en": "🔔 New assignments",
    },

    "investigator_menu_my_stats": {
        "uz": "📊 Mening statistikam",
        "ru": "📊 Моя статистика",
        "en": "📊 My statistics",
    },

    # ── Admin callback xabarlari ──────────────────────────────────────────────
    "assign_no_users": {
        "uz": "⚠️ Tayinlash uchun faol admin/investigator topilmadi.",
        "ru": "⚠️ Нет доступных администраторов/следователей для назначения.",
        "en": "⚠️ No active admin/investigator found for assignment.",
    },

    "assign_cancel_btn": {
        "uz": "❌ Bekor qilish",
        "ru": "❌ Отмена",
        "en": "❌ Cancel",
    },

    "permission_denied": {
        "uz": "❌ Ruxsatingiz yo'q",
        "ru": "❌ Нет доступа",
        "en": "❌ No permission",
    },

    "assigning": {
        "uz": "⏳ Tayinlanmoqda...",
        "ru": "⏳ Назначение...",
        "en": "⏳ Assigning...",
    },

    "invalid_data": {
        "uz": "❌ Noto'g'ri ma'lumot",
        "ru": "❌ Неверные данные",
        "en": "❌ Invalid data",
    },

    "starting": {
        "uz": "⏳ Boshlanmoqda...",
        "ru": "⏳ Запуск...",
        "en": "⏳ Starting...",
    },

    "updating": {
        "uz": "⏳ O'zgartirilmoqda...",
        "ru": "⏳ Изменение...",
        "en": "⏳ Updating...",
    },

    "group_only": {
        "uz": "❌ Bu amal faqat guruhda ishlaydi",
        "ru": "❌ Это действие работает только в группе",
        "en": "❌ This action only works in a group",
    },

    "wrong_format": {
        "uz": "❌ Noto'g'ri format",
        "ru": "❌ Неверный формат",
        "en": "❌ Wrong format",
    },

    "invalid_status_transition": {
        "uz": "⚠️ Bu holatdan {old} → {new} ga o'tish mumkin emas",
        "ru": "⚠️ Переход {old} → {new} невозможен из текущего статуса",
        "en": "⚠️ Transition {old} → {new} is not allowed from current status",
    },

    "status_label_rejected": {
        "uz": "rad etish",
        "ru": "отклонение",
        "en": "rejection",
    },

    "status_label_completed": {
        "uz": "yakunlash",
        "ru": "завершение",
        "en": "completion",
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

