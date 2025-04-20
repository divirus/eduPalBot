from telegram import ReplyKeyboardMarkup

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📚 Русский язык"],
        ["🔢 Математика"],
        # ["💳 Subscribe"],
    ],
    resize_keyboard=True
)

SECTION_MENU = ReplyKeyboardMarkup(
    [
        ["➡️ Новый запрос"],
        ["🔙 В главное меню"],
    ],
    resize_keyboard=True
)

ESSAY_TYPE_MENU = ReplyKeyboardMarkup(
    [
        ["📚 Объяснить правила"],
        ["✍️ Написать сочинение"],
        ["🔙 Назад"],
    ],
    resize_keyboard=True
)

MATH_TYPE_MENU = ReplyKeyboardMarkup(
    [
        ["📚 Объяснить решение"],
        ["📖 Решебник"],
        ["🔙 Назад"],
    ],
    resize_keyboard=True
)