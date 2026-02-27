from aiogram import Router, F
from aiogram.types import Message
import json
import logging
from datetime import datetime
from database import db
from keyboards import admin_keyboard
from config import SERVICE_NAMES, URGENCY_NAMES, MASTER_CHAT_ID

logger = logging.getLogger(__name__)
router = Router()

# Временное хранилище д��я заявок (связь: request_id -> service_id)
REQUESTS_CACHE = {}

@router.message(F.web_app_data)
async def webapp_handler(message: Message):
    """Обработка данных из web app с service_id"""
    logger.info("🔴 ВХОД В webapp_handler")
    try:
        logger.info(f"📨 Получены данные из web app")
        data = json.loads(message.web_app_data.data)
        logger.info(f"✅ JSON распарсен: {data}")
        
        # Получаем service_id из данных web app
        service_id = data.get("service_id") or ""
        logger.info(f"🔍 Service ID: '{service_id}'")
        
        # Безопасно достаём данные
        name = data.get("client_name") or "Не указано"
        phone = data.get("phone") or "—"
        brand = data.get("brand", "—")
        model = data.get("model", "—")
        plate = data.get("plate", "—")
        service_key = data.get("service")
        urgency_key = data.get("urgency")
        comment = data.get("comment", "")

        service_name = SERVICE_NAMES.get(service_key, service_key or "—")
        urgency_name = URGENCY_NAMES.get(urgency_key, urgency_key or "—")

        logger.info(f"📝 Данные заявки: {name}, {phone}, {brand}, {model}")

        # ✅ СОХРАНЯЕМ В БД с service_id
        request_id = await db.add_request(
            idservice=service_id,
            client_name=name,
            phone=phone,
            brand=brand,
            model=model,
            plate=plate,
            service_type=service_key,
            urgency=urgency_key,
            comment=comment,
            client_tg_id=message.from_user.id
        )
        logger.info(f"✅ Заявка сохранена в БД. Request ID: {request_id}")

        # Кешируем для быстрого доступа
        REQUESTS_CACHE[str(request_id)] = {
            "user_id": message.from_user.id,
            "name": name,
            "phone": phone,
            "service_id": service_id
        }

        # ✅ ФОРМИРУЕМ КРАСИВОЕ СООБЩЕНИЕ ДЛЯ АДМИНА
        admin_message = (
            "<b>═══ 🚗 НОВАЯ ЗАЯВКА ═══</b>\n\n"
            "<b>👤 КЛИЕНТ</b>\n"
            f"Имя: <b>{name}</b>\n"
            f"Телефон: <code>{phone}</code>\n"
            f"Telegram: <code>{message.from_user.id}</code>\n\n"
            "<b>🚙 АВТОМОБИЛЬ</b>\n"
            f"Марка: <b>{brand}</b>\n"
            f"Модель: <b>{model}</b>\n"
            f"Гос номер: <code>{plate}</code>\n\n"
            "<b>🔧 УСЛУГА</b>\n"
            f"Тип работы: {service_name}\n"
            f"Срочность: {urgency_name}\n"
        )

        if comment:
            admin_message += f"\n<b>💬 Комментарий</b>\n<i>{comment}</i>\n"

        admin_message += f"\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        admin_message += f"<b>ID заявки:</b> <code>{request_id}</code>"

        # ✅ ПОЛУЧАЕМ ВСЕХ АДМИНОВ ЭТОГО СЕРВИСА И ОТПРАВЛЯЕМ ИМ ЗАЯВКУ
        if service_id:
            logger.info(f"🔎 Ищу админов для сервиса: '{service_id}'")
            admins = await db.get_admins_by_service(service_id)
            logger.info(f"📊 Найдено админов: {len(admins) if admins else 0}")
            
            if admins:
                for admin in admins:
                    try:
                        admin_id = admin['idusertg']
                        logger.info(f"📤 Отправляю заявку админу {admin_id}")
                        await message.bot.send_message(  # ← ИСПОЛЬЗУЕМ message.bot
                            admin_id,
                            admin_message,
                            parse_mode="HTML",
                            reply_markup=admin_keyboard(request_id)
                        )
                        logger.info(f"✅ Заявка отправлена админу {admin_id}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки админу {admin['idusertg']}: {e}", exc_info=True)
            else:
                logger.warning(f"⚠️ Для сервиса '{service_id}' нет админов")
                if MASTER_CHAT_ID:
                    logger.info(f"📤 Отправляю заявку в MASTER_CHAT: {MASTER_CHAT_ID}")
                    try:
                        await message.bot.send_message(  # ← ИСПОЛЬЗУЕМ message.bot
                            MASTER_CHAT_ID,
                            f"⚠️ <b>ЗАЯВКА БЕЗ СЕРВИСА</b>\n\n{admin_message}",
                            parse_mode="HTML"
                        )
                        logger.info(f"✅ Заявка отправлена в MASTER_CHAT")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки в MASTER_CHAT: {e}", exc_info=True)
        else:
            logger.warning(f"⚠️ service_id не передан, отправляю в MASTER_CHAT")
            if MASTER_CHAT_ID:
                try:
                    await message.bot.send_message(  # ← ИСПОЛЬЗУЕМ message.bot
                        MASTER_CHAT_ID,
                        f"⚠️ <b>ЗАЯВКА БЕЗ СЕРВИСА</b>\n\n{admin_message}",
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Заявка отправлена в MASTER_CHAT")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки в MASTER_CHAT: {e}", exc_info=True)

        # ✅ ОТПРАВЛЯЕМ ПОДТВЕРЖДЕНИЕ КЛИЕНТУ
        await message.answer(
            "✅ <b>Заявка отправлена!</b>\n\n"
            "📞 Администратор свяжется с вами в ближайшее время\n\n"
            f"<b>Номер заявки:</b> <code>{request_id}</code>",
            parse_mode="HTML"
        )
        logger.info(f"🟢 ВЫХОД ИЗ webapp_handler - ВСЕ ОК")

    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка при парсинге JSON: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке данных")
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке заявки: {type(e).__name__}: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при отправке заявки: {str(e)}")