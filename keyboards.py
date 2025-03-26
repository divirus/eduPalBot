from telegram import ReplyKeyboardMarkup, KeyboardButton

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📝 Сочинение"), KeyboardButton("🔢 Математика")],
        # [KeyboardButton("Подписка")], пока отключаем
    ],
    resize_keyboard=True
)

SECTION_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("🔄 Новый запрос"), KeyboardButton("🏠 В главное меню")]],
    resize_keyboard=True
)

ESSAY_TYPE_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("📚 Краткое содержание произведения"), KeyboardButton("✍️ Сочинение по теме")],
     [KeyboardButton("🔙 Назад")]],
    resize_keyboard=True
)

MATH_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("🏠 В главное меню")]],
    resize_keyboard=True
)