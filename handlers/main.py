from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from database import db
from keyboards import (
    start_keyboard, CLIENT_NOTIFY
)
from config import SERVICE_NAMES, STATUS_LABELS
import logging

logger = logging.getLogger(__name__)
router = Router()


# ===== ПРОСМОТР ЗАЯВОК =====

@router.message(Command("my_requests"))
@router.message(F.text == "📋 Мои заявки")
async def my_requests(message: Message):
    user_id = message.from_user.id
    is_owner = await db.is_owner(user_id)
    is_admin = await db.is_admin(user_id)

    # Управляющий или администратор — смотрит заявки сервисов
    if is_owner or is_admin:
        if is_owner:
            services = await db.get_owned_services(user_id)
        else:
            services = await db.get_admin_services(user_id)

        if not services:
            await message.answer("❌ У вас нет зарегистрированных сервисов")
            return

        requests_list = "<b>📋 Заявки сервиса:</b>\n\n"
        total = 0
        for service in services:
            requests = await db.get_service_requests(service['idservice'])
            requests_list += f"<b>🏪 {service['service_name']}</b>\n"
            if requests:
                for req in requests[:10]:
                    status_label = STATUS_LABELS.get(req['status'], req['status'])
                    service_name = SERVICE_NAMES.get(req['service_type'], req['service_type'] or '—')
                    requests_list += (
                        f"  • <code>{req['idrequests'][:8]}…</code> "
                        f"{req['client_name']} | {service_name} | {status_label}\n"
                    )
                    total += 1
            else:
                requests_list += "  <i>Нет заявок</i>\n"
            requests_list += "\n"

        if total == 0:
            requests_list += "<i>Заявок пока нет</i>"

        await message.answer(requests_list, parse_mode="HTML")

    else:
        # Обычный пользователь — смотрит свои личные заявки
        requests = await db.get_client_requests(user_id)
        if not requests:
            await message.answer(
                "📋 <b>Ваши заявки</b>\n\n<i>У вас пока нет заявок.</i>",
                parse_mode="HTML"
            )
            return

        text = "<b>📋 Ваши заявки:</b>\n\n"
        for req in requests[:10]:
            status_label = STATUS_LABELS.get(req['status'], req['status'])
            service_name_label = SERVICE_NAMES.get(req['service_type'], req['service_type'] or '—')
            svc = req['service_name'] if req.get('service_name') else '—'
            text += (
                f"🔹 <b>{svc}</b>\n"
                f"   Услуга: {service_name_label}\n"
                f"   Статус: {status_label}\n"
                f"   ID: <code>{req['idrequests']}</code>\n\n"
            )
        await message.answer(text, parse_mode="HTML")


# ===== ПРОСМОТР АДМИНИСТРАТОРОВ =====

@router.message(Command("my_admins"))
@router.message(F.text == "👥 Администраторы")
async def my_admins(message: Message):
    user_id = message.from_user.id
    is_owner = await db.is_owner(user_id)
    is_admin = await db.is_admin(user_id)

    if not (is_owner or is_admin):
        await message.answer("❌ Эта команда доступна только для сотрудников сервиса.")
        return

    if is_owner:
        services = await db.get_owned_services(user_id)
    else:
        services = await db.get_admin_services(user_id)

    if not services:
        await message.answer("❌ У вас нет сервисов.")
        return

    text = "<b>👥 Администраторы сервиса:</b>\n\n"
    for service in services:
        admins = await db.get_admins_by_service(service['idservice'])
        text += f"<b>🏪 {service['service_name']}</b>\n"
        if admins:
            for a in admins:
                text += f"  • <code>{a['idusertg']}</code>\n"
        else:
            text += "  <i>Нет администраторов</i>\n"
        text += "\n"

    await message.answer(text, parse_mode="HTML")


# ===== ИНФОРМАЦИЯ О СЕРВИСЕ =====

@router.message(F.text == "ℹ️ О моем сервисе")
async def service_info(message: Message):
    user_id = message.from_user.id
    if not await db.is_owner(user_id):
        await message.answer("❌ Эта функция доступна только управляющим.")
        return

    services = await db.get_owned_services(user_id)
    if not services:
        await message.answer("❌ У вас нет сервисов")
        return

    info = "<b>ℹ️ Информация о ваших сервисах:</b>\n\n"
    for service in services:
        service_link = db.generate_service_link(service['idservice'])
        info += (
            f"<b>Название:</b> {service['service_name']}\n"
            f"<b>Телефон:</b> {service['service_number']}\n"
        )
        if service.get('location_service'):
            info += f"<b>Адрес:</b> {service['location_service']}\n"
        if service.get('city'):
            info += f"<b>Город:</b> {service['city']}\n"
        info += (
            f"<b>ID:</b> <code>{service['idservice']}</code>\n"
            f"<b>Ссылка на размещение:</b>\n"
            f"<code>{service_link}</code>\n\n"
        )
    await message.answer(info, parse_mode="HTML")


# ===== КНОПКИ УПРАВЛЯЮЩЕГО (редирект на команды) =====

@router.message(F.text == "➕ Добавить админа")
async def btn_add_admin(message: Message, state: FSMContext):
    if not await db.is_owner(message.from_user.id):
        await message.answer("❌ Только управляющий может добавлять администраторов.")
        return
    from handlers.register_service import add_admin_start
    await add_admin_start(message, state)


@router.message(F.text == "➖ Удалить админа")
async def btn_remove_admin(message: Message, state: FSMContext):
    if not await db.is_owner(message.from_user.id):
        await message.answer("❌ Только управляющий может удалять администраторов.")
        return
    from handlers.register_service import remove_admin_start
    await remove_admin_start(message, state)


# ===== ПОКИНУТЬ СЕРВИС (для администраторов) =====

@router.message(Command("leave_service"))
@router.message(F.text == "🚪 Покинуть сервис")
async def leave_service(message: Message):
    user_id = message.from_user.id

    if await db.is_owner(user_id):
        await message.answer(
            "⚠️ Вы являетесь <b>управляющим</b> сервиса и не можете покинуть его как администратор.\n\n"
            "Если хотите передать управление — обратитесь в поддержку.",
            parse_mode="HTML"
        )
        return

    services = await db.get_admin_services(user_id)
    if not services:
        await message.answer("❌ Вы не являетесь администратором ни одного сервиса.")
        return

    if len(services) == 1:
        svc = services[0]
        from keyboards import confirm_leave_keyboard
        await message.answer(
            f"⚠️ Вы уверены, что хотите покинуть сервис <b>{svc['service_name']}</b>?",
            parse_mode="HTML",
            reply_markup=confirm_leave_keyboard(svc['idservice'])
        )
    else:
        # Несколько сервисов — показываем список для выбора
        text = "<b>Выберите сервис, который хотите покинуть:</b>\n\n"
        for svc in services:
            text += f"• <code>{svc['idservice']}</code> — {svc['service_name']}\n"
        text += "\nОтправьте ID сервиса:"

        from aiogram.fsm.context import FSMContext
        await message.answer(text, parse_mode="HTML")
        # Здесь можно добавить FSM если нужно, пока оставляем inline для одного сервиса


@router.callback_query(F.data.startswith("leave_confirm:"))
async def leave_confirm(callback: CallbackQuery):
    service_id = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    await db.remove_admin(service_id, user_id)

    # Обновляем команды меню — теперь пользователь
    try:
        from bot import set_commands_for_user
        await set_commands_for_user(user_id)
    except Exception as e:
        logger.warning(f"Не удалось обновить команды: {e}")

    service = await db.get_service_by_id(service_id)
    svc_name = service['service_name'] if service else "сервис"

    await callback.message.edit_text(
        f"✅ Вы покинули сервис <b>{svc_name}</b>.",
        parse_mode="HTML"
    )
    await callback.answer()

    await callback.message.answer(
        "Вы вернулись в режим пользователя.",
        reply_markup=start_keyboard()
    )


@router.callback_query(F.data == "leave_cancel")
async def leave_cancel(callback: CallbackQuery):
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()


# ===== ОБРАБОТКА СТАТУСОВ ЗАЯВОК =====

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


# ===== CONFIRM/CANCEL УДАЛЕНИЯ АДМИНА =====

@router.callback_query(F.data.startswith("remove_confirm:"))
async def remove_confirm_callback(callback: CallbackQuery):
    _, service_id, admin_id_str = callback.data.split(":", 2)
    admin_id = int(admin_id_str)

    await db.remove_admin(service_id, admin_id)

    # Уведомляем удалённого
    try:
        service = await db.get_service_by_id(service_id)
        svc_name = service['service_name'] if service else "сервис"
        await callback.bot.send_message(
            admin_id,
            f"ℹ️ Вы были удалены из администраторов сервиса <b>{svc_name}</b>.",
            parse_mode="HTML"
        )
        # Обновляем меню у удалённого
        try:
            from bot import set_commands_for_user
            await set_commands_for_user(admin_id)
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Не удалось уведомить удалённого админа: {e}")

    await callback.message.edit_text(
        f"✅ Администратор <code>{admin_id}</code> удалён.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "remove_cancel")
async def remove_cancel_callback(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()


# ===== FALLBACK =====

@router.message()
async def fallback(message: Message):
    await message.answer(
        "❓ Неизвестная команда\n\n"
        "Используйте /start для начала",
        reply_markup=start_keyboard()
    )