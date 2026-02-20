import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import db
from handlers import register_service, service_link, client_request, main

# Логирование
logging.basicConfig(
    level=logging.DEBUG,  # ← ИЗМЕНЕНО НА DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    """Регистрация всех обработчиков - ВАЖНЫЙ ПОРЯДОК!"""
    # ⚠️ web_app_data ДОЛЖЕН БЫТЬ ПЕРВЫМ
    dp.include_routers(
        client_request.router,      # ← ПЕРВЫЙ (web_app_data)
        service_link.router,        # ← ВТОРОЙ (/start SVC_)
        register_service.router,    # ← ТРЕТИЙ (регистрация)
        main.router                 # ← ПОСЛЕДНИЙ (остальное)
    )
    logger.info("✅ Обработчики зарегистрированы")

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