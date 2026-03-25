import os
from dotenv import load_dotenv

load_dotenv()

# Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
URL_SITE = os.getenv("BASE_WEBAPP_URL")
MASTER_CHAT_ID = int(os.getenv("MASTER_CHAT_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "CitatAlcw_bot")  # ← НОВОЕ

# Database
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "password")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "auto_service")

# Service names
SERVICE_NAMES = {
    "diagnostic": "Диагностика",
    "oil-change": "Замена масла",
    "tires": "Шины и диски",
    "brake": "Тормозная система",
    "engine": "Ремонт двигателя",
    "transmission": "Коробка передач",
    "suspension": "Подвеска",
    "body": "Кузовные работы",
    "other": "Другое"
}


URGENCY_NAMES = {
    "low": "Обычный (7+ дней)",
    "medium": "Средний (3-5 дней)",
    "high": "Срочный (1-2 дня)",
    "urgent": "Очень срочный (сегодня)"
}

STATUS_LABELS = {
    "accepted": "✅ Принято",
    "called": "📞 Связались",
    "rejected": "❌ Отказ"
}
