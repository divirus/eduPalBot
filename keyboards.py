from telegram import ReplyKeyboardMarkup, KeyboardButton

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📝 Русский язык"), KeyboardButton("🔢 Математика")],
        # [KeyboardButton("Подписка")], пока отключаем
    ],
    resize_keyboard=True
)

SECTION_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("🔄 Новый запрос"), KeyboardButton("🏠 В главное меню")]],
    resize_keyboard=True
)

ESSAY_TYPE_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("📚 Объяснить правила"), KeyboardButton("✍️ Написать сочинение")],
     [KeyboardButton("🔙 Назад")]],
    resize_keyboard=True
)

MATH_TYPE_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("📚 Объяснить решение"), KeyboardButton("📖 Решебник")],
     [KeyboardButton("🔙 Назад")]],
    resize_keyboard=True
)

MATH_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("🏠 В главное меню")]],
    resize_keyboard=True
)