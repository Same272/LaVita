import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.handlers import router
from database.models import init_db

API_TOKEN = "7608526208:AAGTkbX8PkVBeWNsmMy8Zwzm1jItKuopZvI"

async def main():
    bot = Bot(token=API_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(router)  # Подключаем роутер

    await init_db()  # Инициализация базы данных
    await dp.start_polling(bot)  # Запуск бота

if __name__ == "__main__":
    asyncio.run(main())