import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import AsyncSessionLocal, User, Order
from app.keyboards import (
    language_keyboard, main_menu_keyboard, phone_number_keyboard,
    location_keyboard, confirm_keyboard, bottles_count_keyboard, back_keyboard
)

router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegistrationStates(StatesGroup):
    phone_number = State()
    location = State()
    bottles_count = State()
    confirm_order = State()
    order_by_id = State()  # Состояние для заказа по ID

# Обработчик команды /start
@router.message(F.text == "/start")
async def start_command(message: types.Message):
    welcome_text = (
        "🌟 Привет! Добро пожаловать в LaVita! 🌟\n"
        "🚰 Мы доставляем чистую воду прямо к вам домой или в офис.\n"
        "👇 Выберите язык:"
    )
    photo_url = "https://telegra.ph/file/a761e51a713289a2bfa28.jpg"
    await message.answer_photo(
        photo=photo_url,
        caption=welcome_text,
        reply_markup=language_keyboard()
    )

# Обработчик выбора языка
@router.callback_query(F.data.startswith("lang_"))
async def language_callback(callback_query: types.CallbackQuery, state: FSMContext):
    language = callback_query.data.split("_")[1]
    await state.update_data(language=language)
    await callback_query.message.answer("Выберите действие:", reply_markup=main_menu_keyboard(language))

# Обработчик кнопки "Заказать"
@router.message(F.text.in_(["Заказать", "Order"]))
async def order_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    async with AsyncSessionLocal() as session:
        # Проверяем, зарегистрирован ли пользователь
        user = await session.get(User, message.from_user.id)
        if not user:
            # Если пользователь не зарегистрирован, запрашиваем номер телефона
            await message.answer(
                "Пожалуйста, отправьте ваш номер телефона:" if language == "ru" else "Please share your phone number:",
                reply_markup=phone_number_keyboard(language)
            )
            await state.set_state(RegistrationStates.phone_number)
        else:
            # Если пользователь зарегистрирован, переходим к выбору количества бутылок
            await message.answer(
                "Введите количество бутылок:" if language == "ru" else "Enter the number of bottles:",
                reply_markup=bottles_count_keyboard(language)
            )
            await state.set_state(RegistrationStates.bottles_count)

# Обработчик номера телефона
@router.message(RegistrationStates.phone_number, F.contact | F.text.in_(["Назад", "Back"]))
async def process_phone_number(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["Назад", "Back"]:
        await message.answer("Выберите действие:", reply_markup=main_menu_keyboard(language))
        await state.clear()
        return

    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)

    # Запрашиваем геолокацию
    await message.answer(
        "Поделитесь своей геолокацией:" if language == "ru" else "Share your location:",
        reply_markup=location_keyboard(language)
    )
    await state.set_state(RegistrationStates.location)

# Обработчик геолокации
@router.message(RegistrationStates.location, F.location | F.text.in_(["Назад", "Back"]))
async def process_location(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["Назад", "Back"]:
        await message.answer("Пожалуйста, отправьте ваш номер телефона:", reply_markup=phone_number_keyboard(language))
        await state.set_state(RegistrationStates.phone_number)
        return

    location = message.location
    await state.update_data(location=location)

    # Регистрируем пользователя
    async with AsyncSessionLocal() as session:
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            phone_number=user_data["phone_number"],
            language=language
        )
        session.add(user)
        await session.commit()

    # Переходим к выбору количества бутылок
    await message.answer(
        "Введите количество бутылок:" if language == "ru" else "Enter the number of bottles:",
        reply_markup=bottles_count_keyboard(language)
    )
    await state.set_state(RegistrationStates.bottles_count)

# Обработчик ввода количества бутылок
@router.message(RegistrationStates.bottles_count, F.text)
async def process_bottles_count(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["Назад", "Back"]:
        await message.answer("Выберите действие:", reply_markup=main_menu_keyboard(language))
        await state.clear()
        return

    try:
        bottles_count = int(message.text)  # Пытаемся преобразовать введенный текст в число
        if bottles_count < 1:
            raise ValueError
    except ValueError:
        await message.answer(
            "Неверное количество бутылок. Введите число больше 0." if language == "ru" else "Invalid number of bottles. Enter a number greater than 0."
        )
        return

    # Сохраняем количество бутылок в состоянии
    await state.update_data(bottles_count=bottles_count)

    # Подтверждение заказа
    await message.answer(
        "Подтвердите заказ:" if language == "ru" else "Confirm the order:",
        reply_markup=confirm_keyboard(language)
    )
    await state.set_state(RegistrationStates.confirm_order)

# Обработчик подтверждения заказа
@router.message(RegistrationStates.confirm_order, F.text.in_(["Подтвердить", "Confirm", "Назад", "Back"]))
async def process_confirm_order(message: types.Message, state: FSMContext):
    if message.text in ["Назад", "Back"]:
        user_data = await state.get_data()
        language = user_data.get("language", "ru")
        await message.answer("Введите количество бутылок:", reply_markup=bottles_count_keyboard(language))
        await state.set_state(RegistrationStates.bottles_count)
        return

    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    async with AsyncSessionLocal() as session:
        # Создаем новый заказ
        order = Order(
            user_id=message.from_user.id,
            bottles_count=user_data["bottles_count"],
            location=str(user_data["location"])
        )
        session.add(order)
        await session.commit()

        # Текст после успешного заказа
        if language == "ru":
            success_message = (
                "✅ Ваш заказ успешно принят!\n"
                f"🧊 Количество бутылок: {user_data['bottles_count']}\n"
                f"📍 Адрес доставки: {user_data['location']}\n"
                "🙏 Спасибо за ваш заказ!"
            )
        else:
            success_message = (
                "✅ Your order has been successfully placed!\n"
                f"🧊 Number of bottles: {user_data['bottles_count']}\n"
                f"📍 Delivery address: {user_data['location']}\n"
                "🙏 Thank you for your order!"
            )

        await message.answer(success_message, reply_markup=main_menu_keyboard(language))
        await state.clear()

# Обработчик кнопки "Заказать по ID"
@router.message(F.text.in_(["Заказать по ID", "Order by ID"]))
async def order_by_id_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    await message.answer(
        "Введите ваш ID:" if language == "ru" else "Enter your ID:",
        reply_markup=back_keyboard(language)
    )
    await state.set_state(RegistrationStates.order_by_id)

# Обработчик ввода ID пользователя
@router.message(RegistrationStates.order_by_id, F.text)
async def process_order_by_id(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["Назад", "Back"]:
        await message.answer("Выберите действие:", reply_markup=main_menu_keyboard(language))
        await state.clear()
        return

    user_code = message.text.strip()  # Убираем лишние пробелы

    async with AsyncSessionLocal() as session:
        # Ищем пользователя по коду
        user = await session.execute(
            User.__table__.select().where(User.user_code == user_code)
        )
        user = user.scalars().first()

        if not user:
            await message.answer(
                "Пользователь с таким ID не найден." if language == "ru" else "User with this ID not found."
            )
            return

        # Сохраняем данные пользователя в состоянии
        await state.update_data(
            user_id=user.id,
            user_code=user_code
        )

        # Запрашиваем количество бутылок
        await message.answer(
            "Введите количество бутылок:" if language == "ru" else "Enter the number of bottles:",
            reply_markup=bottles_count_keyboard(language)
        )
        orders = orders.scalars().all()

        if not orders:
            await message.answer(
                "У вас нет активных заказов." if language == "ru" else "You have no active orders.",
                reply_markup=main_menu_keyboard(language)
            )
            return

        # Форматируем список активных заказов
        if language == "ru":
            orders_text = "📦 Ваши активные заказы:\n"
            for order in orders:
                orders_text += (
                    f"🆔 ID заказа: {order.id}\n"
                    f"🧊 Количество бутылок: {order.bottles_count}\n"
                    f"💸 Стоимость: {order.total_cost} сум\n"
                    f"📍 Адрес доставки: {order.location}\n\n"
                )
        else:
            orders_text = "📦 Your active orders:\n"
            for order in orders:
                orders_text += (
                    f"🆔 Order ID: {order.id}\n"
                    f"🧊 Number of bottles: {order.bottles_count}\n"
                    f"💸 Cost: {order.total_cost} UZS\n"
                    f"📍 Delivery address: {order.location}\n\n"
                )

        await message.answer(orders_text, reply_markup=main_menu_keyboard(language))


# Обработчик кнопки "Профиль"
@router.message(F.text.in_(["👤 Профиль", "👤 Profile"]))
async def profile_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    async with AsyncSessionLocal() as session:
        # Ищем пользователя в базе данных
        user = await session.get(User, message.from_user.id)
        if not user:
            await message.answer(
                "Вы еще не зарегистрированы." if language == "ru" else "You are not registered yet.",
                reply_markup=main_menu_keyboard(language)
            )
            return

        # Форматируем данные профиля
        if language == "ru":
            profile_text = (
                "📱 Ваш профиль:\n"
                f"👤 Имя: {user.full_name}\n"
                f"📞 Номер телефона: {user.phone_number}\n"
                f"📍 Адрес: {user.address}\n"
                f"🌐 Язык: {user.language}"
            )
        else:
            profile_text = (
                "📱 Your profile:\n"
                f"👤 Name: {user.full_name}\n"
                f"📞 Phone number: {user.phone_number}\n"
                f"📍 Address: {user.address}\n"
                f"🌐 Language: {user.language}"
            )

        await message.answer(profile_text, reply_markup=profile_keyboard(language))

# Обработчик кнопки "Изменить язык"
@router.message(F.text.in_(["🌐 Изменить язык", "🌐 Change language"]))
async def change_language_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    await message.answer(
        "Выберите язык:" if language == "ru" else "Choose language:",
        reply_markup=language_keyboard()
    )


# Обработчик ввода ID для заказа по ID
@router.message(RegistrationStates.order_by_id, F.text)
async def process_order_by_id(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["⬅️ Назад", "⬅️ Back"]:
        await message.answer(
            "Выберите действие:" if language == "ru" else "Choose action:",
            reply_markup=main_menu_keyboard(language)
        )
        await state.clear()
        return

    try:
        amount = float(message.text)  # Пытаемся преобразовать введенный текст в число
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Неверная сумма. Введите положительное число." if language == "ru" else "Invalid amount. Enter a positive number."
        )
        return

    # Пополняем баланс
    async with AsyncSessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            await message.answer(
                "Вы еще не зарегистрированы." if language == "ru" else "You are not registered yet.",
                reply_markup=main_menu_keyboard(language)
            )
            return

        user.balance += amount
        session.add(user)
        await session.commit()

        # Текст после успешного пополнения
        if language == "ru":
            success_message = f"✅ Баланс успешно пополнен на {amount} сум. Текущий баланс: {user.balance} сум."
        else:
            success_message = f"✅ Balance successfully topped up by {amount} UZS. Current balance: {user.balance} UZS."

        await message.answer(success_message, reply_markup=main_menu_keyboard(language))
        await state.clear()