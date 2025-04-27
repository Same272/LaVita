import logging
import random
import string

import aiohttp
from aiogram import Router, types, F
from aiogram.fsm import state
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from datetime import datetime
from database.models import AsyncSessionLocal, User, Order
from app.keyboards import (
    language_keyboard, main_menu_keyboard, phone_number_keyboard,
    location_keyboard, confirm_keyboard, bottles_count_keyboard,
    back_keyboard, profile_keyboard, expenses_keyboard,wasabi_keyboard
)
from geopy.geocoders import Nominatim
from geopy.adapters import AioHTTPAdapter
import asyncio


router = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_user_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class RegistrationStates(StatesGroup):
    phone_number = State()      # Шаг 1: Номер телефона
    location = State()          # Шаг 2: Геолокация
    address_details = State()   # Шаг 3: Уточнение адреса
    bottles_count = State()     # Шаг 4: Количество бутылок
    confirm_order = State()     # Шаг 5: Подтверждение
    order_by_id = State()       # Для заказа по ID
    address = State()


async def get_address_from_coords(latitude: float, longitude: float, language: str = 'ru') -> str:
    """Получает читаемый адрес по координатам через Nominatim API"""
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&addressdetails=1&accept-language={language}"
    headers = {"User-Agent": "LaVitaWaterDeliveryBot/1.0 (contact@example.com)"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    address = data.get('address', {})

                    # Собираем основные компоненты адреса
                    components = []

                    # Улица + номер дома
                    if 'road' in address:
                        street = address['road']
                        if 'house_number' in address:
                            street += f" {address['house_number']}"
                        components.append(street)

                    # Район/микрорайон
                    for area in ['neighbourhood', 'suburb', 'city_district']:
                        if area in address:
                            components.append(address[area])
                            break

                    # Город/населенный пункт
                    if 'city' in address:
                        components.append(address['city'])
                    elif 'town' in address:
                        components.append(address['town'])
                    elif 'village' in address:
                        components.append(address['village'])

                    if components:
                        return ", ".join(components)

                    return "Адрес не определен" if language == 'ru' else "Address not found"

                return "Ошибка запроса к сервису" if language == 'ru' else "Service request error"

    except Exception as e:
        logger.error(f"Geocoding error: {str(e)}")
        return "Ошибка сервиса" if language == 'ru' else "Service error"


@router.message(RegistrationStates.location, F.location)
async def process_location(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    try:
        # Получаем координаты
        loc = message.location
        latitude = loc.latitude
        longitude = loc.longitude

        # Получаем базовый адрес
        base_address = await get_address_from_coords(latitude, longitude, language)

        if "не определен" in base_address or "not found" in base_address:
            raise ValueError("Адрес не определен")

        # Сохраняем данные
        await state.update_data(
            latitude=latitude,
            longitude=longitude,
            base_address=base_address
        )

        # Запрашиваем уточнения
        prompt = (
            "📍 <b>Базовый адрес определен:</b>\n"
            f"{base_address}\n\n"
            "🏠 Пожалуйста, уточните:\n"
            "• Номер дома (если не указан)\n"
            "• Номер квартиры/офиса\n\n"
            "<i>Пример: 15 или 15, кв 42</i>"
            if language == "ru" else
            "📍 <b>Base address detected:</b>\n"
            f"{base_address}\n\n"
            "🏠 Please specify:\n"
            "• House number (if missing)\n"
            "• Apartment/office number\n\n"
            "<i>Example: 15 or 15, apt 42</i>"
        )

        await message.answer(
            prompt,
            parse_mode="HTML",
            reply_markup=back_keyboard(language)
        )
        await state.set_state(RegistrationStates.address_details)

    except Exception as e:
        logger.error(f"Location processing error: {str(e)}")
        error_msg = (
            "❌ Не удалось определить адрес по локации\n"
            "Пожалуйста, попробуйте еще раз или введите адрес вручную"
            if language == "ru" else
            "❌ Could not determine address from location\n"
            "Please try again or enter address manually"
        )
        await message.answer(error_msg)

@router.message(F.text == "/start")
async def start_command(message: types.Message):
    # Отправка изображения с приветствием
    welcome_photo = types.FSInputFile("static/welcome.png")  # Путь к вашему изображению
    welcome_text = (
        "🌟 Привет! Добро пожаловать в LaVita! 🌟\n"
        "🚰 Мы доставляем чистую воду прямо к вам домой или в офис.\n"
        "👇 Выберите язык:"
    )
    await message.answer_photo(
        photo=welcome_photo,
        caption=welcome_text,
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def language_callback(callback_query: types.CallbackQuery, state: FSMContext):
    language = callback_query.data.split("_")[1]
    await state.update_data(language=language)

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


@router.message(F.text.in_(["🧊 Заказать", "🧊 Order"]))
async def order_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    # Всегда начинаем с номера телефона
    await message.answer(
        "Для оформления заказа нам нужен ваш номер телефона.\n"
        "Пожалуйста, нажмите кнопку ниже или введите номер вручную в формате +998XXYYYYYYY"
        if language == "ru" else
        "To place an order, we need your phone number.\n"
        "Please use the button below or enter manually in format +998XXYYYYYYY",
        reply_markup=phone_number_keyboard(language)
    )
    await state.set_state(RegistrationStates.phone_number)


# Обработка номера телефона (без изменений, кроме сохранения данных)
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

    if message.contact:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text

    phone_number = phone_number.replace(" ", "").replace("-", "")

    if not (phone_number.startswith("+") or phone_number.isdigit()):
        await message.answer(
            "Неверный формат. Используйте +998XXYYYYYYY или 998XXYYYYYYY"
            if language == "ru" else
            "Invalid format. Use +998XXYYYYYYY or 998XXYYYYYYY"
        )
        return

    await state.update_data(phone_number=phone_number)

    # После номера сразу запрашиваем локацию
    await message.answer(
        "Теперь поделитесь геолокацией:" if language == "ru" else "Now share your location:",
        reply_markup=location_keyboard(language)
    )
    await state.set_state(RegistrationStates.location)



@router.message(RegistrationStates.address, F.text)
async def process_address_details(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    # Обработка кнопки "Назад"
    if message.text in ["⬅️ Назад", "⬅️ Back"]:
        await message.answer(
            "📍 Отправьте вашу геолокацию:" if language == "ru" else "📍 Share your location:",
            reply_markup=location_keyboard(language)
        )
        await state.set_state(RegistrationStates.location)
        return

    # Проверка обязательных данных
    required_data = {
        'phone_number': "📱 Номер телефона" if language == "ru" else "📱 Phone number",
        'base_address': "📍 Базовый адрес" if language == "ru" else "📍 Base address"
    }

    missing_fields = [name for field, name in required_data.items() if field not in user_data]

    if missing_fields:
        error_msg = (
            "❌ <b>Недостаточно данных для регистрации</b>\n\n"
            f"Отсутствует: {', '.join(missing_fields)}\n\n"
            "Пожалуйста, начните процесс заново."
            if language == "ru" else
            "❌ <b>Registration data incomplete</b>\n\n"
            f"Missing: {', '.join(missing_fields)}\n\n"
            "Please start the process again."
        )
        await message.answer(error_msg, parse_mode="HTML", reply_markup=main_menu_keyboard(language))
        await state.clear()
        return

    # Обработка введенного адреса
    address_details = message.text.strip()

    # Валидация адреса
    if not address_details or not any(c.isdigit() for c in address_details):
        error_msg = (
            "❌ <b>Некорректный формат адреса</b>\n\n"
            "Пожалуйста, укажите:\n"
            "• Номер дома (обязательно)\n"
            "• Номер квартиры (если нужно)\n\n"
            "<i>Пример: <code>15</code> или <code>15, кв 42</code></i>"
            if language == "ru" else
            "❌ <b>Invalid address format</b>\n\n"
            "Please include:\n"
            "• House number (required)\n"
            "• Apartment number (if needed)\n\n"
            "<i>Example: <code>15</code> or <code>15, apt 42</code></i>"
        )
        await message.answer(error_msg, parse_mode="HTML")
        return

    # Формирование полного адреса
    full_address = f"{user_data['base_address']}, {address_details}"

    try:
        async with AsyncSessionLocal() as session:
            # Проверка существующего пользователя
            user = await session.get(User, message.from_user.id)

            if user:
                # Обновление данных существующего пользователя
                user.address = full_address
                user.phone_number = user_data['phone_number']
                status_msg = "обновлен" if language == "ru" else "updated"
            else:
                # Создание нового пользователя
                user_code = generate_user_code()
                user = User(
                    id=message.from_user.id,
                    user_code=user_code,
                    username=message.from_user.username,
                    full_name=message.from_user.full_name,
                    phone_number=user_data['phone_number'],
                    language=language,
                    address=full_address,
                    total_spent=0
                )
                session.add(user)
                status_msg = "зарегистрирован" if language == "ru" else "registered"

            await session.commit()

            # Красивое сообщение о успешном завершении
            success_template = (
                "✨ <b>Регистрация успешно завершена!</b>\n\n"
                "📋 <i>Ваши данные:</i>\n"
                "👤 {full_name}\n"
                "📱 {phone}\n"
                "🏠 {address}\n\n"
                "Теперь укажите количество бутылок:"
                if language == "ru" else
                "✨ <b>Registration completed!</b>\n\n"
                "📋 <i>Your details:</i>\n"
                "👤 {full_name}\n"
                "📱 {phone}\n"
                "🏠 {address}\n\n"
                "Now please enter bottles count:"
            )

            await message.answer(
                success_template.format(
                    full_name=message.from_user.full_name,
                    phone=user_data['phone_number'],
                    address=full_address
                ),
                parse_mode="HTML",
                reply_markup=bottles_count_keyboard(language)
            )

            await state.update_data(location=full_address)
            await state.set_state(RegistrationStates.bottles_count)

    except Exception as e:
        logger.error(f"Database error in address processing: {e}")
        error_msg = (
            "⚠️ <b>Ошибка сохранения данных</b>\n\n"
            "Пожалуйста, попробуйте позже."
            if language == "ru" else
            "⚠️ <b>Data save error</b>\n\n"
            "Please try again later."
        )
        await message.answer(error_msg, parse_mode="HTML", reply_markup=main_menu_keyboard(language))
        await state.clear()





@router.message(RegistrationStates.bottles_count, F.text.in_(["➕", "➖", "✅ Подтвердить", "✅ Confirm"]))
async def process_bottles_count(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    current_count = user_data.get("bottles_count", 0)

    if message.text == "➕":
        current_count += 1
    elif message.text == "➖":
        current_count = max(0, current_count - 1)
    elif message.text in ["✅ Подтвердить", "✅ Confirm"]:
        if current_count < 1:
            await message.answer(
                "Минимум 1 бутылка" if language == "ru" else "Minimum 1 bottle"
            )
            return

        await state.update_data(bottles_count=current_count)
        bottle_price = 20000
        total_cost = current_count * bottle_price
        await state.update_data(total_cost=total_cost)

        order_text = (
            f"🧊 Бутылок: {current_count}\n"
            f"💸 Сумма: {total_cost} сум\n"
            f"📍 Адрес: {user_data['location']}\n"
            "Подтверждаете заказ?"
            if language == "ru"
            else f"🧊 Bottles: {current_count}\n"
                 f"💸 Total: {total_cost} UZS\n"
                 f"📍 Address: {user_data['location']}\n"
                 "Confirm order?"
        )
        await message.answer(order_text, reply_markup=confirm_keyboard(language))
        await state.set_state(RegistrationStates.confirm_order)
        return

    await state.update_data(bottles_count=current_count)
    count_text = (
        f"Количество: {current_count}" if language == "ru"
        else f"Count: {current_count}"
    )
    await message.answer(count_text, reply_markup=bottles_count_keyboard(language))


@router.message(RegistrationStates.confirm_order, F.text.in_(["✅ Подтвердить", "✅ Confirm", "⬅️ Назад", "⬅️ Back"]))
async def process_confirm_order(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["⬅️ Назад", "⬅️ Back"]:
        await message.answer(
            "Введите количество бутылок:" if language == "ru" else "Enter the number of bottles:",
            reply_markup=bottles_count_keyboard(language)
        )
        await state.set_state(RegistrationStates.bottles_count)
        return

    async with AsyncSessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            await message.answer(
                "Ошибка: пользователь не найден" if language == "ru" else "Error: user not found",
                reply_markup=main_menu_keyboard(language)
            )
            return

        order = Order(
            user_id=message.from_user.id,
            bottles_count=user_data["bottles_count"],
            location=user_data["location"],
            status="active",
            total_cost=user_data["total_cost"]
        )
        session.add(order)
        user.total_spent += user_data["total_cost"]
        session.add(user)
        await session.commit()

        success_text = (
            f"✅ Заказ принят!\n"
            f"🧊 Бутылок: {user_data['bottles_count']}\n"
            f"💸 Сумма: {user_data['total_cost']} сум\n"
            f"📍 Адрес: {user_data['location']}\n"
            "Спасибо за заказ!"
            if language == "ru"
            else f"✅ Order accepted!\n"
                 f"🧊 Bottles: {user_data['bottles_count']}\n"
                 f"💸 Total: {user_data['total_cost']} UZS\n"
                 f"📍 Address: {user_data['location']}\n"
                 "Thank you for your order!"
        )
        await message.answer(success_text, reply_markup=main_menu_keyboard(language))
        await state.clear()


# Профиль и настройки
@router.message(F.text.in_(["👤 Профиль", "👤 Profile"]))
async def profile_callback(message: types.Message, state: FSMContext):
    await state.update_data(in_profile=True)
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    async with AsyncSessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            await message.answer(
                "Вы еще не зарегистрированы." if language == "ru" else "You are not registered yet.",
                reply_markup=main_menu_keyboard(language)
            )
            return

        profile_text = (
            f"👤 Профиль:\n"
            f"🆔 Код: {user.user_code}\n"
            f"📱 Имя: {user.full_name}\n"
            f"📞 Телефон: {user.phone_number}\n"
            f"📍 Адрес: {user.address}\n"
            f"💸 Всего потрачено: {user.total_spent} сум"
            if language == "ru"
            else f"👤 Profile:\n"
                 f"🆔 Code: {user.user_code}\n"
                 f"📱 Name: {user.full_name}\n"
                 f"📞 Phone: {user.phone_number}\n"
                 f"📍 Address: {user.address}\n"
                 f"💸 Total spent: {user.total_spent} UZS"
        )
        await message.answer(profile_text, reply_markup=profile_keyboard(language))


@router.message(F.text.in_(["🌐 Сменить язык", "🌐 Change language"]))
async def change_language_prompt(message: types.Message):
    await message.answer(
        "Выберите язык:" if "Сменить" in message.text else "Choose language:",
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def change_language_callback(callback_query: types.CallbackQuery, state: FSMContext):
    language = callback_query.data.split("_")[1]
    await state.update_data(language=language)

    async with AsyncSessionLocal() as session:
        user = await session.get(User, callback_query.from_user.id)
        if user:
            user.language = language
            session.add(user)
            await session.commit()

    await callback_query.message.answer(
        "Язык изменен!" if language == "ru" else "Language changed!"
    )
    await profile_callback(callback_query.message, state)


@router.message(F.text.in_(["⬅️ Назад", "⬅️ Back"]))
async def back_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if user_data.get('in_profile', False):
        await state.update_data(in_profile=False)
    await message.answer(
        "Главное меню" if language == "ru" else "Main menu",
        reply_markup=main_menu_keyboard(language)
    )


@router.message(F.text.in_(["💰 Траты", "💰 Expenses"]))
async def show_expenses(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    lang = user_data.get("language", "ru")

    async with AsyncSessionLocal() as session:
        # Получаем данные пользователя
        user = await session.get(User, message.from_user.id)
        if not user:
            return await message.answer(
                "❌ Пользователь не найден" if lang == "ru" else "❌ User not found"
            )

        # Получаем все заказы
        orders = await session.execute(
            select(Order)
            .where(Order.user_id == message.from_user.id)
        )
        orders = orders.scalars().all()

        total_spent = user.total_spent or 0
        order_count = len(orders)
        avg_order = total_spent / order_count if order_count > 0 else 0

        # Создаем "график" из emoji
        progress_bar = "🟢" * min(10, int(order_count / 2)) + "⚪️" * (10 - min(10, int(order_count / 2)))

        message_text = (
            "📊 <b>Ваши траты</b>\n"
            "────────────────────\n"
            f"💳 Всего потрачено: <b>{total_spent:,} сум</b>\n"
            f"📦 Количество заказов: <b>{order_count}</b>\n"
            f"📌 Средний чек: <b>{avg_order:,.0f} сум</b>\n\n"
            "🔢 Частота заказов:\n"
            f"{progress_bar}\n"
            "────────────────────"
            if lang == "ru" else
            "📊 <b>Your Expenses</b>\n"
            "────────────────────\n"
            f"💳 Total spent: <b>{total_spent:,} UZS</b>\n"
            f"📦 Orders count: <b>{order_count}</b>\n"
            f"📌 Average order: <b>{avg_order:,.0f} UZS</b>\n\n"
            "🔢 Order frequency:\n"
            f"{progress_bar}\n"
            "────────────────────"
        )

        await message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=expenses_keyboard(lang)
        )


@router.message(F.text.in_(["📦 Активные заказы", "📦 Active Orders"]))
async def active_orders(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    lang = user_data.get("language", "ru")

    async with AsyncSessionLocal() as session:
        orders = await session.execute(
            select(Order)
            .where(
                (Order.user_id == message.from_user.id) &
                (Order.status == "active")
            )
            .order_by(Order.created_at.desc())
        )
        orders = orders.scalars().all()

        if not orders:
            no_orders = (
                "🔄 Нет активных заказов\n"
                "Хотите оформить новый?"
                if lang == "ru" else
                "🔄 No active orders\n"
                "Would you like to place a new one?"
            )
            return await message.answer(no_orders, reply_markup=main_menu_keyboard(lang))

        # Формируем красивое сообщение
        header = (
            "🚚 <b>Ваши активные заказы</b>\n"
            "────────────────────"
            if lang == "ru" else
            "🚚 <b>Your Active Orders</b>\n"
            "────────────────────"
        )

        for order in orders:
            delivery_time = order.created_at.strftime("%H:%M %d.%m")
            header += (
                f"\n\n🆔 <b>Заказ #{order.id}</b>\n"
                f"⏱ Время оформления: {delivery_time}\n"
                f"📦 Бутылок: {order.bottles_count} шт.\n"
                f"💵 Сумма: {order.total_cost:,} сум\n"
                f"📍 Адрес: {order.location[:30]}..."
                if lang == "ru" else
                f"\n\n🆔 <b>Order #{order.id}</b>\n"
                f"⏱ Order time: {delivery_time}\n"
                f"📦 Bottles: {order.bottles_count} pcs\n"
                f"💵 Amount: {order.total_cost:,} UZS\n"
                f"📍 Address: {order.location[:30]}..."
            )

        await message.answer(
            header,
            parse_mode="HTML",
            reply_markup=back_keyboard(lang)
        )


# Заказ по ID
@router.message(F.text.in_(["🆔 Заказать по ID", "🆔 Order by ID"]))
async def order_by_id_callback(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    await message.answer(
        "Введите ваш код:" if language == "ru" else "Enter your code:",
        reply_markup=back_keyboard(language)
    )
    await state.set_state(RegistrationStates.order_by_id)


@router.message(RegistrationStates.order_by_id, F.text)
async def process_order_by_id(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")

    if message.text in ["⬅️ Назад", "⬅️ Back"]:
        await message.answer(
            "Главное меню" if language == "ru" else "Main menu",
            reply_markup=main_menu_keyboard(language)
        )
        await state.clear()
        return

    user_code = message.text.upper().strip()

    async with AsyncSessionLocal() as session:
        user = await session.execute(
            select(User).where(User.user_code == user_code)
        )
        user = user.scalar_one_or_none()

        if not user:
            await message.answer(
                "Код не найден." if language == "ru" else "Code not found.",
                reply_markup=back_keyboard(language)
            )
            return

        await state.update_data(
            phone_number=user.phone_number,
            location=user.address
        )
        await message.answer(
            "Введите количество бутылок:" if language == "ru" else "Enter the number of bottles:",
            reply_markup=bottles_count_keyboard(language)
        )
        await state.set_state(RegistrationStates.bottles_count)


@router.message(F.text.in_(["📜 История заказов", "📜 Order History"]))
async def order_history(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        language = user_data.get("language", "ru")

        async with AsyncSessionLocal() as session:
            orders = await session.execute(
                select(Order)
                .where(Order.user_id == message.from_user.id)
                .order_by(Order.created_at.desc())
            )
            orders = orders.scalars().all()

            if not orders:
                no_orders_msg = (
                    "📭 У вас пока нет заказов.\n"
                    "Хотите сделать первый заказ?"
                    if language == "ru" else
                    "📭 You don't have any orders yet.\n"
                    "Would you like to place your first order?"
                )
                await message.answer(no_orders_msg, reply_markup=main_menu_keyboard(language))
                return

            # Формируем сообщение
            header = "📋 <b>Ваши заказы:</b>\n\n" if language == "ru" else "📋 <b>Your orders:</b>\n\n"
            message_text = header

            for order in orders:
                status_emoji = "✅" if order.status == "completed" else "🔄"
                order_date = order.created_at.strftime("%d.%m.%Y")

                message_text += (
                    f"{status_emoji} <b>Заказ #{order.id}</b>\n"
                    f"🗓 {order_date} | 🧊 {order.bottles_count} шт.\n"
                    f"💵 {order.total_cost:,} сум\n"
                    f"📍 {order.location[:30]}...\n\n"
                    if language == "ru" else
                    f"{status_emoji} <b>Order #{order.id}</b>\n"
                    f"🗓 {order_date} | 🧊 {order.bottles_count} pcs\n"
                    f"💵 {order.total_cost:,} UZS\n"
                    f"📍 {order.location[:30]}...\n\n"
                )

            await message.answer(
                message_text,
                parse_mode="HTML",
                reply_markup=wasabi_keyboard(language)
            )

    except Exception as e:
        logger.error(f"Error in order_history: {e}")
        error_msg = (
            "⚠️ Произошла ошибка при загрузке истории заказов."
            if language == "ru" else
            "⚠️ Error loading order history."
        )
        await message.answer(error_msg)