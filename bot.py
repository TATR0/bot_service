import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import db
from handlers import register_service, service_link, client_request, main
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def on_startup():
    await db.connect()

    # ✅ Проверка переменных окружения при старте
    url = os.getenv("BASE_WEBAPP_URL")
    bot_username = os.getenv("BOT_USERNAME")
    master_chat = os.getenv("MASTER_CHAT_ID")

    logger.info("========== КОНФИГУРАЦИЯ ==========")
    logger.info(f"BASE_WEBAPP_URL  = {repr(url)}")
    logger.info(f"BOT_USERNAME     = {repr(bot_username)}")
    logger.info(f"MASTER_CHAT_ID   = {repr(master_chat)}")
    logger.info("===================================")

    if not url:
        logger.error("❌ BASE_WEBAPP_URL не задана! Кнопка WebApp работать не будет.")
    elif not url.startswith("https://"):
        logger.error(f"❌ BASE_WEBAPP_URL должна начинаться с https://. Текущее значение: {repr(url)}")
    else:
        logger.info("✅ BASE_WEBAPP_URL корректна")

    logger.info("✅ Бот запущен и БД подключена")

async def on_shutdown():
    await db.close()
    logger.info("❌ Бот остановлен и БД отключена")

def register_handlers():
    dp.include_routers(
        client_request.router,
        service_link.router,
        register_service.router,
        main.router
    )
    logger.info("✅ Обработчики зарегистрированы")

async def main_async():
    await on_startup()
    register_handlers()
    try:
        logger.info("Polling started...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main_async())