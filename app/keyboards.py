from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Инлайн-кнопки для выбора языка
def language_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
        ]
    )

# Главное меню (обычные кнопки)
def main_menu_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🧊 Заказать")],
                [KeyboardButton(text="🆔 Заказать по ID")],
                [KeyboardButton(text="👤 Профиль")],
                [KeyboardButton(text="📦 Активные заказы")],
                [KeyboardButton(text="📜 История заказов")],
                [KeyboardButton(text="💰 Баланс и траты")]
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
                [KeyboardButton(text="💰 Balance & Expenses")]
            ],
            resize_keyboard=True
        )

# Кнопки для изменения количества бутылок
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

# Кнопка для отправки номера телефона
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

# Кнопка для отправки геолокации
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

# Кнопка для подтверждения заказа
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

# Кнопка "Назад"
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

# Клавиатура для профиля
def profile_keyboard(language="ru"):
    if language == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🌐 Изменить язык"), KeyboardButton(text="⬅️ Назад")],
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🌐 Change language"), KeyboardButton(text="⬅️ Back")],
            ],
            resize_keyboard=True
        )