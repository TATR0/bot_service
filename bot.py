import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import db
from handlers import register_service, service_link, client_request, main
from api import create_app
import os

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot     = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(storage=storage)

# Порт для HTTP-сервера (index.html + API)
API_PORT = int(os.getenv("API_PORT", "8080"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")


async def on_startup():
    await db.connect()
    logger.info("✅ Бот запущен и БД подключена")


async def on_shutdown():
    await db.close()
    logger.info("❌ Бот остановлен и БД отключена")


def register_handlers():
    dp.include_routers(
        client_request.router,   # ← ПЕРВЫЙ (web_app_data)
        service_link.router,     # ← ВТОРОЙ (/start SVC_)
        register_service.router, # ← ТРЕТИЙ (регистрация)
        main.router              # ← ПОСЛЕДНИЙ (остальное)
    )
    logger.info("✅ Обработчики зарегистрированы")


async def run_api_server():
    """Запуск aiohttp HTTP-сервера"""
    app     = create_app()
    runner  = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, API_HOST, API_PORT)
    await site.start()
    logger.info(f"🌐 API-сервер запущен на http://{API_HOST}:{API_PORT}")
    # держим сервер живым вечно (завершится при отмене задачи)
    while True:
        await asyncio.sleep(3600)


async def main_async():
    await on_startup()
    register_handlers()

    try:
        logger.info("Polling started...")
        await asyncio.gather(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()),
            run_api_server()
        )
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main_async())