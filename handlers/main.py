from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import json
from datetime import datetime
from database import db
from keyboards import start_keyboard, admin_menu_keyboard, admin_keyboard
from config import SERVICE_NAMES, URGENCY_NAMES, STATUS_LABELS

router = Router()

# Временное хранилище для заявок (в реальном проекте данные из БД)
REQUESTS_CACHE = {}

# ===== /start =====
@router.message(Command("start"))
async def start_command(message: Message):
    """Команда /start"""
    # Проверяем, админ ли это
    user_services = await db.get_admin_services(message.from_user.id)
    
    if user_services:
        await message.answer(
            "👋 <b>Добро пожаловать, администратор!</b>",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard()
        )
    else:
        await message.answer(
            "🚗 <b>Добро пожаловать в систему записи автосервиса!</b>",
            parse_mode="HTML",
            reply_markup=start_keyboard()
        )

# ===== ПРИЁМ ЗАЯВКИ ОТ WEB ПРИЛОЖЕНИЯ =====
@router.message(F.web_app_data)
async def webapp_handler(message: Message):
    """Обработка данных из web app"""
    try:
        data = json.loads(message.web_app_data.data)
        
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

        # Пока заявка отправляется всем админам (в будущем нужна привязка к сервису)
        # Для теста используем заранее определённый сервис или первый доступный
        
        # Сохраняем в БД (нужно определить idservice, может быть из параметров)
        # Пока используем пустую строку, впоследствии нужно связать с конкретным сервисом
        request_id = await db.add_request(
            idservice="",  # TODO: получить от клиента или из web app
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

        # Кешируем для быстрого доступа
        REQUESTS_CACHE[str(request_id)] = {
            "user_id": message.from_user.id,
            "name": name,
            "phone": phone
        }

        admin_message = (
            "<b>═══ 🚗 НОВАЯ ЗАЯВКА ═══</b>\n\n"
            "<b>👤 КЛИЕНТ</b>\n"
            f"Имя: <b>{name}</b>\n"
            f"Телефон: <code>{phone}</code>\n\n"
            "<b>🚙 АВТО</b>\n"
            f"Марка: {brand}\n"
            f"Модель: {model}\n"
            f"Гос номер: <code>{plate}</code>\n\n"
            "<b>🔧 УСЛУГА</b>\n"
            f"Тип: {service_name}\n"
            f"Срочность: {urgency_name}\n"
        )

        if comment:
            admin_message += f"\n<b>💬 Комментарий</b>\n{comment}\n"

        admin_message += f"\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        # Отправляем уведомление всем админам сервиса
        # TODO: реализовать отправку конкретным админам по сервису
        admins = await db.get_admin_services(message.from_user.id)

        await message.answer(
            "✅ <b>Заявка отправлена!</b>\n\nМы скоро с вами свяжемся 📞",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка при обработке заявки: {e}")
        await message.answer("❌ Ошибка при отправке заявки")

# ===== ОБРАБОТКА АДМИН-КНОПОК =====
@router.callback_query(F.data.startswith("status:"))
async def admin_status_handler(callback: CallbackQuery):
    """Обновление статуса заявки админом"""
    try:
        _, status, request_id = callback.data.split(":")
        request_id = int(request_id)

        # Обновляем в БД
        await db.update_request_status(request_id, status)

        # Обновляем сообщение админу
        new_text = callback.message.html_text + f"\n\n<b>📌 Статус:</b> {STATUS_LABELS[status]}"
        await callback.message.edit_text(new_text, parse_mode="HTML")

        # Уведомление клиенту
        request = REQUESTS_CACHE.get(str(request_id))
        if request and request.get("user_id"):
            try:
                await callback.bot.send_message(
                    request["user_id"],
                    f"📢 <b>Статус вашей заявки обновлён</b>\n\n"
                    f"<b>Статус:</b> {STATUS_LABELS[status]}\n\n"
                    f"📞 Свяжитесь с сервисом для уточнений",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Ошибка отправки клиенту: {e}")

        await callback.answer("✅ Статус обновлён")

    except Exception as e:
        print(f"Ошибка при обновлении статуса: {e}")
        await callback.answer("❌ Ошибка при обновлении", show_alert=True)

# ===== АДМИН КОМАНДЫ =====
@router.message(F.text == "📋 Мои заявки")
async def my_requests(message: Message):
    """Показать заявки админа"""
    services = await db.get_admin_services(message.from_user.id)
    
    if not services:
        await message.answer(
            "❌ У вас нет зарегистрированных сервисов\n\n"
            "Используйте команду /register_service для регистрации",
            reply_markup=start_keyboard()
        )
        return

    requests_list = "<b>📋 Мои заявки:</b>\n\n"
    
    for service in services:
        requests = await db.get_service_requests(service['idservice'])
        if requests:
            requests_list += f"<b>{service['service_name']}</b>\n"
            for req in requests[:5]:  # Последние 5 заявок
                requests_list += f"  • {req['client_name']} - {req['status']}\n"
        else:
            requests_list += f"<b>{service['service_name']}</b> - нет заявок\n"

    await message.answer(requests_list, parse_mode="HTML")

@router.message(F.text == "ℹ️ О моем сервисе")
async def service_info(message: Message):
    """Информация о сервисе"""
    services = await db.get_admin_services(message.from_user.id)
    
    if not services:
        await message.answer("❌ У вас нет сервисов")
        return

    info = "<b>ℹ️ Информация о моих сервисах:</b>\n\n"
    for service in services:
        info += (
            f"<b>Название:</b> {service['service_name']}\n"
            f"<b>Телефон:</b> {service['service_number']}\n"
            f"<b>ID:</b> <code>{service['idservice']}</code>\n\n"
        )

    await message.answer(info, parse_mode="HTML")

# ===== FALLBACK =====
@router.message()
async def fallback(message: Message):
    """Обработка неизвестных команд"""
    await message.answer(
        "❓ Неизвестная команда\n\n"
        "Используйте /start для начала",
        reply_markup=start_keyboard()
    )