import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import db
from handlers import main, register_service

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def on_startup():
    """Инициализация при запуске"""
    await db.connect()
    logger.info("✅ Бот запущен и БД подключена")

async def on_shutdown():
    """Завершение работы"""
    await db.close()
    logger.info("❌ Бот остановлен и БД отключена")

def register_handlers():
    """Регистрация всех обработчиков"""
    dp.include_routers(
        register_service.router,
        main.router
    )

async def main_async():
    """Основной цикл"""
    await on_startup()
    register_handlers()
    
    try:
        logger.info("Polling started...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main_async())