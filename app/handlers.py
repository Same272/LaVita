import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.models import AsyncSessionLocal, User, Order
from app.keyboards import (
    language_keyboard, main_menu_keyboard, phone_number_keyboard,
    location_keyboard, confirm_keyboard, bottles_count_keyboard, back_keyboard, profile_keyboard
)
import aiohttp

router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegistrationStates(StatesGroup):
    phone_number = State()
    location = State()
    address = State()
    bottles_count = State()
    confirm_order = State()
    order_by_id = State()
    top_up_balance = State()  # Состояние для пополнения баланса


# Функция для получения адреса по координатам (Nominatim API)
async def get_address_from_coords(latitude: float, longitude: float) -> str:
    """
    Получает адрес по координатам с помощью OpenStreetMap Nominatim API.
    """
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
    headers = {
        "User-Agent": "LaVitaBot/1.0 (contact@example.com)"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if "display_name" in data:
                    return data["display_name"]
                else:
                    return "Адрес не найден."
            else:
                return "Ошибка при запросе к API."


# Обработчик команды /start
@router.message(F.text == "/start")
async def start_command(message: types.Message):
    welcome_text = (
        "🌟 Привет! Добро пожаловать в LaVita! 🌟\n"
        "🚰 Мы доставляем чистую воду прямо к вам домой или в офис.\n"
        "👇 Выберите язык:"
    )
    photo_url = "https://telegra.ph/file/a761e51a713289a2bfa28.jpg"  # Замените на реальный URL фото
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

    # Обновляем язык в базе данных
    async with AsyncSessionLocal() as session:
        user = await session.get(User, callback_query.from_user.id)
        if user:
            user.language = language
            session.add(user)
            await session.commit()

    await callback_query.message.answer(
        "Выберите действие:" if language == "ru" else "Choose action:",
        reply_markup=main_menu_keyboard(language)
    )


# Обработчик кнопки "Заказать"
@router.message(F.text.in_(["🧊 Заказать", "🧊 Order"]))
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
            # Если пользователь зарегистрирован, запрашиваем геолокацию
            await message.answer(
                "Поделитесь своей геолокацией:" if language == "ru" else "Share your location:",
                reply_markup=location_keyboard(language)
            )
            await state.set_state(RegistrationStates.location)


# Обработчик номера телефона
@router.message(RegistrationStates.phone_number, F.contact | F.text)
async def process_phone_number(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["⬅️ Назад", "⬅️ Back"]:
        await message.answer(
            "Выберите действие:" if language == "ru" else "Choose action:",
            reply_markup=main_menu_keyboard(language)
        )
        await state.clear()
        return

    # Проверяем, отправлен ли контакт
    if message.contact:
        phone_number = message.contact.phone_number
    else:
        # Если пользователь ввел номер вручную
        phone_number = message.text

    # Проверяем, что номер телефона введен корректно
    if not phone_number.startswith("+") and not phone_number.isdigit():
        await message.answer(
            "Неверный формат номера телефона. Введите номер в формате +998901234567."
            if language == "ru"
            else "Invalid phone number format. Enter the number in the format +998901234567."
        )
        return

    # Сохраняем номер телефона в состоянии
    await state.update_data(phone_number=phone_number)

    # Запрашиваем геолокацию
    await message.answer(
        "Поделитесь своей геолокацией:" if language == "ru" else "Share your location:",
        reply_markup=location_keyboard(language)
    )
    await state.set_state(RegistrationStates.location)


# Обработчик геолокации
@router.message(RegistrationStates.location, F.location | F.text.in_(["⬅️ Назад", "⬅️ Back"]))
async def process_location(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["⬅️ Назад", "⬅️ Back"]:
        await message.answer(
            "Пожалуйста, отправьте ваш номер телефона:" if language == "ru" else "Please share your phone number:",
            reply_markup=phone_number_keyboard(language)
        )
        await state.set_state(RegistrationStates.phone_number)
        return

    # Получаем координаты
    location = message.location
    latitude = location.latitude
    longitude = location.longitude

    # Получаем адрес по координатам
    address = await get_address_from_coords(latitude, longitude)

    # Сохраняем адрес в состоянии
    await state.update_data(location=address)

    # Регистрируем пользователя
    async with AsyncSessionLocal() as session:
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            phone_number=user_data["phone_number"],
            language=language,
            address=address  # Сохраняем адрес
        )
        session.add(user)
        await session.commit()

    # Переходим к выбору количества бутылок
    await message.answer(
        "Введите количество бутылок:" if language == "ru" else "Enter the number of bottles:",
        reply_markup=bottles_count_keyboard(language)
    )
    await state.set_state(RegistrationStates.bottles_count)


# Обработчик кнопок "+" и "-" для выбора количества бутылок
@router.message(RegistrationStates.bottles_count, F.text.in_(["➕", "➖", "✅ Подтвердить", "✅ Confirm"]))
async def process_bottles_count_buttons(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    current_count = user_data.get("bottles_count", 0)

    if message.text == "➕":
        current_count += 1
    elif message.text == "➖":
        if current_count > 0:
            current_count -= 1
    elif message.text in ["✅ Подтвердить", "✅ Confirm"]:
        if current_count < 1:
            await message.answer(
                "Количество бутылок должно быть больше 0." if language == "ru" else "Number of bottles must be greater than 0."
            )
            return
        await state.update_data(bottles_count=current_count)
        await message.answer(
            "Подтвердите заказ:" if language == "ru" else "Confirm the order:",
            reply_markup=confirm_keyboard(language)
        )
        await state.set_state(RegistrationStates.confirm_order)
        return

    await state.update_data(bottles_count=current_count)
    await message.answer(
        f"Количество бутылок: {current_count}" if language == "ru" else f"Number of bottles: {current_count}",
        reply_markup=bottles_count_keyboard(language)
    )


# Обработчик подтверждения заказа
@router.message(RegistrationStates.confirm_order, F.text.in_(["✅ Подтвердить", "✅ Confirm", "⬅️ Назад", "⬅️ Back"]))
async def process_confirm_order(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["⬅️ Назад", "⬅️ Back"]:
        await message.answer(
            "Выберите действие:" if language == "ru" else "Choose action:",
            reply_markup=main_menu_keyboard(language)
        )
        await state.clear()
        return

    # Стоимость одной бутылки
    bottle_price = 20000  # 20 000 сум за бутылку
    bottles_count = user_data["bottles_count"]
    total_cost = bottles_count * bottle_price  # Общая стоимость заказа

    async with AsyncSessionLocal() as session:
        # Ищем пользователя в базе данных
        user = await session.get(User, message.from_user.id)
        if not user:
            await message.answer(
                "Вы еще не зарегистрированы." if language == "ru" else "You are not registered yet.",
                reply_markup=main_menu_keyboard(language)
            )
            return

        # Проверяем, хватает ли баланса
        if user.balance < total_cost:
            await message.answer(
                "Недостаточно средств на балансе. Пожалуйста, пополните баланс."
                if language == "ru"
                else "Insufficient funds. Please top up your balance.",
                reply_markup=main_menu_keyboard(language)
            )
            return

        # Создаем новый заказ
        order = Order(
            user_id=message.from_user.id,
            bottles_count=bottles_count,
            location=user_data["location"],
            status="active",
            total_cost=total_cost
        )
        session.add(order)

        # Обновляем баланс и траты пользователя
        user.balance -= total_cost
        user.total_spent += total_cost
        session.add(user)

        await session.commit()

        # Текст после успешного заказа
        if language == "ru":
            success_message = (
                "✅ Ваш заказ успешно принят!\n"
                f"🧊 Количество бутылок: {bottles_count}\n"
                f"💸 Стоимость заказа: {total_cost} сум\n"
                f"📍 Адрес доставки: {user_data['location']}\n"
                f"💵 Остаток на балансе: {user.balance} сум\n"
                "🙏 Спасибо за ваш заказ!"
            )
        else:
            success_message = (
                "✅ Your order has been successfully placed!\n"
                f"🧊 Number of bottles: {bottles_count}\n"
                f"💸 Order cost: {total_cost} UZS\n"
                f"📍 Delivery address: {user_data['location']}\n"
                f"💵 Remaining balance: {user.balance} UZS\n"
                "🙏 Thank you for your order!"
            )

        await message.answer(success_message, reply_markup=main_menu_keyboard(language))
        await state.clear()


# Обработчик кнопки "Баланс и траты"
@router.message(F.text.in_(["💰 Баланс и траты", "💰 Balance & Expenses"]))
async def balance_and_expenses_callback(message: types.Message, state: FSMContext):
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

        # Форматируем данные о балансе и тратах
        if language == "ru":
            balance_text = (
                "💰 Ваш баланс:\n"
                f"💵 Текущий баланс: {user.balance} сум\n"
                f"💸 Всего потрачено: {user.total_spent} сум"
            )
        else:
            balance_text = (
                "💰 Your balance:\n"
                f"💵 Current balance: {user.balance} UZS\n"
                f"💸 Total spent: {user.total_spent} UZS"
            )

        await message.answer(balance_text, reply_markup=main_menu_keyboard(language))


# Обработчик кнопки "Пополнить баланс"
@router.message(F.text.in_(["💳 Пополнить баланс", "💳 Top Up Balance"]))
async def top_up_balance_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    await message.answer(
        "Введите сумму для пополнения баланса:" if language == "ru" else "Enter the amount to top up your balance:",
        reply_markup=back_keyboard(language)
    )
    await state.set_state(RegistrationStates.top_up_balance)


# Обработчик ввода суммы для пополнения баланса
@router.message(RegistrationStates.top_up_balance, F.text)
async def process_top_up_balance(message: types.Message, state: FSMContext):
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


# Обработчик кнопки "История заказов"
@router.message(F.text.in_(["📜 История заказов", "📜 Order History"]))
async def order_history_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    async with AsyncSessionLocal() as session:
        # Ищем все заказы пользователя
        orders = await session.execute(
            select(Order).where(Order.user_id == message.from_user.id)
        )
        orders = orders.scalars().all()

        if not orders:
            await message.answer(
                "У вас нет завершенных заказов." if language == "ru" else "You have no completed orders.",
                reply_markup=main_menu_keyboard(language)
            )
            return

        # Форматируем список заказов
        if language == "ru":
            orders_text = "📜 История ваших заказов:\n"
            for order in orders:
                status = "✅ Доставлен" if order.status == "completed" else "🔄 В процессе"
                orders_text += (
                    f"🆔 ID заказа: {order.id}\n"
                    f"🧊 Количество бутылок: {order.bottles_count}\n"
                    f"💸 Стоимость: {order.total_cost} сум\n"
                    f"📍 Адрес доставки: {order.location}\n"
                    f"📅 Дата: {order.created_at}\n"
                    f"📦 Статус: {status}\n\n"
                )
        else:
            orders_text = "📜 Your order history:\n"
            for order in orders:
                status = "✅ Delivered" if order.status == "completed" else "🔄 In progress"
                orders_text += (
                    f"🆔 Order ID: {order.id}\n"
                    f"🧊 Number of bottles: {order.bottles_count}\n"
                    f"💸 Cost: {order.total_cost} UZS\n"
                    f"📍 Delivery address: {order.location}\n"
                    f"📅 Date: {order.created_at}\n"
                    f"📦 Status: {status}\n\n"
                )

        await message.answer(orders_text, reply_markup=main_menu_keyboard(language))


# Обработчик кнопки "Активные заказы"
@router.message(F.text.in_(["📦 Активные заказы", "📦 Active Orders"]))
async def active_orders_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    async with AsyncSessionLocal() as session:
        # Ищем активные заказы пользователя
        orders = await session.execute(
            select(Order).where(Order.user_id == message.from_user.id, Order.status == "active")
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
                "👤 Ваш профиль:\n"
                f"📱 Имя: {user.full_name}\n"
                f"📞 Номер телефона: {user.phone_number}\n"
                f"📍 Адрес: {user.address}\n"
                f"💵 Баланс: {user.balance} сум\n"
                f"💸 Всего потрачено: {user.total_spent} сум"
            )
        else:
            profile_text = (
                "👤 Your profile:\n"
                f"📱 Name: {user.full_name}\n"
                f"📞 Phone number: {user.phone_number}\n"
                f"📍 Address: {user.address}\n"
                f"💵 Balance: {user.balance} UZS\n"
                f"💸 Total spent: {user.total_spent} UZS"
            )

        await message.answer(profile_text, reply_markup=profile_keyboard(language))


# Обработчик кнопки "Заказать по ID"
@router.message(F.text.in_(["🆔 Заказать по ID", "🆔 Order by ID"]))
async def order_by_id_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    await message.answer(
        "Введите ваш ID:" if language == "ru" else "Enter your ID:",
        reply_markup=back_keyboard(language)
    )
    await state.set_state(RegistrationStates.order_by_id)


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
        user_id = int(message.text)  # Пытаемся преобразовать введенный текст в число (ID)
    except ValueError:
        await message.answer(
            "Неверный ID. Введите число." if language == "ru" else "Invalid ID. Enter a number."
        )
        return

    # Переходим к выбору количества бутылок
    await message.answer(
        "Введите количество бутылок:" if language == "ru" else "Enter the number of bottles:",
        reply_markup=bottles_count_keyboard(language)
    )
    await state.update_data(user_id=user_id)
    await state.set_state(RegistrationStates.bottles_count)