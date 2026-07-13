from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Создать заявку")],
        [
            KeyboardButton(text="🛠 Открытые тикеты"),
            KeyboardButton(text="📊 Скачать отчет")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)
