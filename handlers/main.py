from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from keyboards import start_keyboard, admin_menu_keyboard, CLIENT_NOTIFY
from config import SERVICE_NAMES, URGENCY_NAMES, STATUS_LABELS
import logging

logger = logging.getLogger(__name__)
router = Router()

# ===== АДМИН КОМАНДЫ =====
@router.message(F.text == "📋 Мои заявки")
async def my_requests(message: Message):
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
            for req in requests[:5]:
                status_label = STATUS_LABELS.get(req['status'], req['status'])
                requests_list += f"  • {req['client_name']} — {status_label}\n"
        else:
            requests_list += f"<b>{service['service_name']}</b> — нет заявок\n"

    await message.answer(requests_list, parse_mode="HTML")

@router.message(F.text == "📝 Зарегистрировать новый сервис")
async def register_new_service(message: Message, state: FSMContext):
    from handlers.register_service import RegisterService
    await message.answer(
        "🚗 <b>Регистрация автосервиса</b>\n\n"
        "Введите название вашего автосервиса:",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_name)

@router.message(F.text == "ℹ️ О моем сервисе")
async def service_info(message: Message):
    services = await db.get_admin_services(message.from_user.id)
    if not services:
        await message.answer("❌ У вас нет сервисов")
        return

    info = "<b>ℹ️ Информация о моих сервисах:</b>\n\n"
    for service in services:
        service_link = db.generate_service_link(service['idservice'])
        info += (
            f"<b>Название:</b> {service['service_name']}\n"
            f"<b>Телефон:</b> {service['service_number']}\n"
        )
        if service.get('location_service'):
            info += f"<b>Адрес:</b> {service['location_service']}\n"
        info += (
            f"<b>ID:</b> <code>{service['idservice']}</code>\n"
            f"<b>Ссылка на размещение:</b>\n"
            f"<code>{service_link}</code>\n\n"
        )
    await message.answer(info, parse_mode="HTML")

# ===== ОБРАБОТКА СТАТУСОВ =====
@router.callback_query(F.data.startswith("status:"))
async def admin_status_handler(callback: CallbackQuery):
    try:
        _, status, request_id = callback.data.split(":", 2)

        await db.update_request_status(request_id, status)

        new_text = callback.message.html_text + f"\n\n<b>📌 Статус:</b> {STATUS_LABELS[status]}"
        await callback.message.edit_text(new_text, parse_mode="HTML")
        await callback.answer("✅ Статус обновлён")

        # Уведомляем клиента
        request = await db.get_request(request_id)
        if request and request['idclienttg']:
            try:
                client_id = int(request['idclienttg'])
                notify_text = CLIENT_NOTIFY.get(status, "")
                if notify_text:
                    service = await db.get_service_by_id(request['idservice'])
                    svc_name = service['service_name'] if service else "Автосервис"
                    await callback.bot.send_message(
                        client_id,
                        f"{notify_text}\n\n"
                        f"<b>Сервис:</b> {svc_name}\n"
                        f"<b>Номер заявки:</b> <code>{request_id}</code>",
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Уведомление отправлено клиенту {client_id}")
            except Exception as e:
                logger.error(f"❌ Не удалось уведомить клиента: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении статуса: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обновлении", show_alert=True)

# ===== FALLBACK =====
@router.message()
async def fallback(message: Message):
    await message.answer(
        "❓ Неизвестная команда\n\n"
        "Используйте /start для начала",
        reply_markup=start_keyboard()
    )