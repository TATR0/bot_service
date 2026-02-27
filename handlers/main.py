from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from keyboards import start_keyboard, admin_menu_keyboard
from config import SERVICE_NAMES, URGENCY_NAMES, STATUS_LABELS

router = Router()

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
            for req in requests[:5]:
                requests_list += f"  • {req['client_name']} - {req['status']}\n"
        else:
            requests_list += f"<b>{service['service_name']}</b> - нет заявок\n"

    await message.answer(requests_list, parse_mode="HTML")

@router.message(F.text == "📝 Зарегистрировать новый сервис")
async def register_new_service(message: Message, state: FSMContext):
    """Регистрация нового сервиса"""
    from handlers.register_service import RegisterService
    await message.answer(
        "🚗 <b>Регистрация автосервиса</b>\n\n"
        "Введите название вашего автосервиса:",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_name)

@router.message(F.text == "ℹ️ О моем сервисе")
async def service_info(message: Message):
    """Информация о сервисе"""
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

# ===== ОБРАБОТКА АДМИН-КНОПОК =====
@router.callback_query(F.data.startswith("status:"))
async def admin_status_handler(callback: CallbackQuery):
    """Обновление статуса заявки админом"""
    try:
        _, status, request_id = callback.data.split(":", 2)

        await db.update_request_status(request_id, status)

        new_text = callback.message.html_text + f"\n\n<b>📌 Статус:</b> {STATUS_LABELS[status]}"
        await callback.message.edit_text(new_text, parse_mode="HTML")

        await callback.answer("✅ Статус обновлён")

    except Exception as e:
        print(f"❌ Ошибка при обновлении статуса: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при обновлении", show_alert=True)

# ===== FALLBACK =====
@router.message()
async def fallback(message: Message):
    """Обработка неизвестных команд"""
    await message.answer(
        "❓ Неизвестная команда\n\n"
        "Используйте /start для начала",
        reply_markup=start_keyboard()
    )