from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MASTER_CHAT_ID = int(os.getenv("MASTER_CHAT_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== СЛОВАРИ =====
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

REQUESTS = {}

# ===== КНОПКИ АДМИНКИ =====
def admin_keyboard(request_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принято", callback_data=f"status:accepted:{request_id}"),
            InlineKeyboardButton(text="📞 Связались", callback_data=f"status:called:{request_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"status:rejected:{request_id}")
        ]
    ])

# ===== /start =====
@dp.message(F.text == "/start")
async def start(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="🚗 Записаться в автосервис",
                web_app=WebAppInfo(url="https://tatr0.github.io/bot_telegram/")

            )
        ]],
        resize_keyboard=True
    )
    await message.answer("Запишитесь в автосервис онлайн 👇", reply_markup=keyboard)

# ===== ПРИЁМ ЗАЯВКИ =====
@dp.message(F.web_app_data)
async def webapp_handler(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        request_id = str(int(datetime.now().timestamp()))

        # безопасно достаём данные
        name = data.get("client_name") or "Не указано"
        phone = data.get("phone") or "—"
        user = data.get("user") or {}
        user_id = user.get("id")

        # сохраняем заявку
        REQUESTS[request_id] = {            
            "user_id": message.from_user.id,  # ← ВОТ КЛЮЧ
            "name": name,
            "phone": phone
        }

        service_key = data.get("service")
        urgency_key = data.get("urgency")

        service_name = SERVICE_NAMES.get(service_key, service_key or "—")
        urgency_name = URGENCY_NAMES.get(urgency_key, urgency_key or "—")

        admin_message = (
            "<b>═══ 🚗 НОВАЯ ЗАЯВКА ═══</b>\n\n"
            "<b>👤 КЛИЕНТ</b>\n"
            f"Имя: <b>{name}</b>\n"
            f"Телефон: <code>{phone}</code>\n\n"
            "<b>🚙 АВТО</b>\n"
            f"Марка: {data.get('brand', '—')}\n"
            f"Модель: {data.get('model', '—')}\n"
            f"Гос номер: <code>{data.get('plate', '—')}</code>\n\n"
            "<b>🔧 УСЛУГА</b>\n"
            f"Тип: {service_name}\n"
            f"Срочность: {urgency_name}\n"
        )

        if data.get("comment"):
            admin_message += f"\n<b>💬 Комментарий</b>\n{data.get('comment')}\n"

        admin_message += f"\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        await bot.send_message(
            MASTER_CHAT_ID,
            admin_message,
            parse_mode="HTML",
            reply_markup=admin_keyboard(request_id)
        )

        await message.answer(
            "✅ <b>Заявка отправлена!</b>\n\nМы скоро с вами свяжемся 📞",
            parse_mode="HTML"
        )

    except Exception as e:
        print("Ошибка:", e)
        await message.answer("❌ Ошибка при отправке заявки")


# ===== ОБРАБОТКА АДМИН-КНОПОК =====
@dp.callback_query(F.data.startswith("status:"))
async def admin_status_handler(callback: CallbackQuery):
    if callback.from_user.id != MASTER_CHAT_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    _, status, request_id = callback.data.split(":")

    # обновляем сообщение админу
    new_text = callback.message.html_text + f"\n\n<b>📌 Статус:</b> {STATUS_LABELS[status]}"
    await callback.message.edit_text(new_text, parse_mode="HTML")

    # уведомление клиенту
    request = REQUESTS.get(request_id)
    if request and request.get("user_id"):
        try:
            await bot.send_message(
                request["user_id"],
                f"📢 <b>Статус вашей заявки обновлён</b>\n\n"
                f"<b>Статус:</b> {STATUS_LABELS[status]}\n\n"
                f"📞 Телефон сервиса: уточняйте при звонке",
                parse_mode="HTML"
            )
        except Exception as e:
            print("Ошибка отправки клиенту:", e)

    await callback.answer("Статус обновлён")


# ===== FALLBACK =====
@dp.message()
async def fallback(message: Message):
    await message.answer(
        "Нажмите кнопку ниже 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(
                    text="🚗 Записаться в автосервис",
                    web_app=WebAppInfo(url="https://tatr0.github.io/bot_telegram/")
                )
            ]],
            resize_keyboard=True
        )
    )

# ===== MAIN =====
async def main():
    print("✅ Бот с админкой запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())