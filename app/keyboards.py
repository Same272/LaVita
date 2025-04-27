from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def language_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
        ]
    )

def main_menu_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🧊 Заказать")],
                [KeyboardButton(text="🆔 Заказать по ID")],
                [KeyboardButton(text="👤 Профиль")],
                [KeyboardButton(text="📦 Активные заказы")],
                [KeyboardButton(text="📜 История заказов")],
                [KeyboardButton(text="💰 Траты")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🧊 Order")],
                [KeyboardButton(text="🆔 Order by ID")],
                [KeyboardButton(text="👤 Profile")],
                [KeyboardButton(text="📦 Active Orders")],
                [KeyboardButton(text="📜 Order History")],
                [KeyboardButton(text="💰 Expenses")]
            ],
            resize_keyboard=True
        )

def bottles_count_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➖"), KeyboardButton(text="➕")],
                [KeyboardButton(text="✅ Подтвердить")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➖"), KeyboardButton(text="➕")],
                [KeyboardButton(text="✅ Confirm")]
            ],
            resize_keyboard=True
        )

def phone_number_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Отправить номер телефона", request_contact=True)],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Share Phone Number", request_contact=True)],
                [KeyboardButton(text="⬅️ Back")]
            ],
            resize_keyboard=True
        )

def location_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📍 Share Location", request_location=True)],
                [KeyboardButton(text="⬅️ Back")]
            ],
            resize_keyboard=True
        )

def confirm_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Подтвердить")],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Confirm")],
                [KeyboardButton(text="⬅️ Back")]
            ],
            resize_keyboard=True
        )

def back_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⬅️ Back")]
            ],
            resize_keyboard=True
        )

def profile_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🌐 Сменить язык")],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🌐 Change language")],
                [KeyboardButton(text="⬅️ Back")]
            ],
            resize_keyboard=True
        )

def expenses_keyboard(language: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Назад" if language == "ru" else "⬅️ Back")]
        ],
        resize_keyboard=True
    )

def wasabi_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⬅️ Back")]
            ],
            resize_keyboard=True
        )