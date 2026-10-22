from telegram import ReplyKeyboardMarkup, KeyboardButton

ESSAY_BUTTON = "📝 Сочинение"
MATH_BUTTON = "🔢 Математика"

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton(ESSAY_BUTTON), KeyboardButton(MATH_BUTTON)]
    ],
    resize_keyboard=True
)

SECTION_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔄 Новый запрос"), KeyboardButton("🏠 В главное меню")],
        [KeyboardButton(ESSAY_BUTTON), KeyboardButton(MATH_BUTTON)],
    ],
    resize_keyboard=True
)

ESSAY_TYPE_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("📚 Краткое содержание произведения"), KeyboardButton("✍️ Сочинение по теме")],
     [KeyboardButton("🔙 Назад")],
     [KeyboardButton(ESSAY_BUTTON), KeyboardButton(MATH_BUTTON)]],
    resize_keyboard=True
)

MATH_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🏠 В главное меню")],
        [KeyboardButton(ESSAY_BUTTON), KeyboardButton(MATH_BUTTON)],
    ],
    resize_keyboard=True
)

# Navigation used by the alternative handlers module.
SUBSECTION_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("Назад"), KeyboardButton("В главное меню")]],
    resize_keyboard=True,
)
