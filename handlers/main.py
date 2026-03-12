from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import db
from keyboards import CLIENT_NOTIFY, admin_keyboard, owner_menu_keyboard, admin_menu_keyboard, user_menu_keyboard
from config import STATUS_LABELS, SERVICE_NAMES, URGENCY_NAMES
import logging

logger = logging.getLogger(__name__)
router = Router()

REQUESTS_LIMIT = 10  # последних заявок показываем


async def get_role(user_id: int):
    owned = await db.get_owned_services(user_id)
    if owned:
        return 'owner', owned
    services = await db.get_admin_services(user_id)
    if services:
        return 'admin', services
    return 'user', []


# ===== 📋 МОИ ЗАЯВКИ =====
@router.message(F.text == "📋 Мои заявки")
@router.message(Command("my_requests"))
async def my_requests(message: Message):
    role, services = await get_role(message.from_user.id)

    # ── Пользователь: его собственные заявки ──
    if role == 'user':
        requests = await db.get_user_requests(message.from_user.id, REQUESTS_LIMIT)
        if not requests:
            await message.answer(
                "📋 У вас пока нет заявок.\n\n"
                "Нажмите «🚗 Записаться в автосервис» чтобы подать первую заявку."
            )
            return

        text = f"<b>📋 Ваши последние заявки ({len(requests)}):</b>\n\n"
        for req in requests:
            status_label = STATUS_LABELS.get(req['status'], req['status'])
            svc = req['service_name'] or "—"
            service_label = SERVICE_NAMES.get(req['service_type'], req['service_type'] or "—")
            date_str = req['createdate'].strftime("%d.%m.%Y") if req.get('createdate') else "—"
            text += (
                f"🗓 <b>{date_str}</b> — {svc}\n"
                f"   Услуга: {service_label}\n"
                f"   Статус: {status_label}\n"
                f"   <code>{req['idrequests']}</code>\n\n"
            )
        await message.answer(text, parse_mode="HTML")
        return

    # ── Управляющий / Администратор: заявки по сервисам ──
    if not services:
        await message.answer("❌ У вас нет сервисов.")
        return

    for service in services:
        requests = await db.get_service_requests(service['idservice'], REQUESTS_LIMIT)
        svc_name = service['service_name']

        if not requests:
            await message.answer(f"<b>{svc_name}</b>\n\nЗаявок пока нет.", parse_mode="HTML")
            continue

        text = f"<b>📋 {svc_name} — последние {len(requests)} заявок:</b>\n\n"
        for req in requests:
            status_label = STATUS_LABELS.get(req['status'], req['status'])
            service_label = SERVICE_NAMES.get(req['service_type'], req['service_type'] or "—")
            urgency_label = URGENCY_NAMES.get(req['urgency'], req['urgency'] or "—")
            date_str = req['createdate'].strftime("%d.%m.%Y %H:%M") if req.get('createdate') else "—"
            text += (
                f"🗓 <b>{date_str}</b>\n"
                f"   👤 {req['client_name']} — <code>{req['phone']}</code>\n"
                f"   🚙 {req['brand']} {req['model']} / {req['plate']}\n"
                f"   🔧 {service_label} ({urgency_label})\n"
                f"   📌 {status_label}\n"
            )
            if req.get('comment'):
                text += f"   💬 {req['comment']}\n"
            text += f"   <code>{req['idrequests']}</code>\n\n"

        await message.answer(text, parse_mode="HTML")


# ===== 👥 МОИ АДМИНИСТРАТОРЫ =====
@router.message(F.text == "👥 Мои администраторы")
@router.message(Command("my_admins"))
async def my_admins(message: Message):
    role, services = await get_role(message.from_user.id)

    if role == 'user':
        await message.answer("❌ Эта команда недоступна.")
        return

    if not services:
        await message.answer("❌ У вас нет сервисов.")
        return

    text = "<b>👥 Администраторы сервисов:</b>\n\n"
    for service in services:
        admins = await db.get_admins_by_service(service['idservice'])
        text += f"<b>{service['service_name']}</b>\n"
        if admins:
            for a in admins:
                # Показываем имя если есть, иначе только ID
                name_part = f" — {a['admin_name']}" if a.get('admin_name') else ""
                text += f"  • <code>{a['idusertg']}</code>{name_part}\n"
        else:
            text += "  — нет администраторов\n"
        text += "\n"

    await message.answer(text, parse_mode="HTML")


# ===== ➕ ДОБАВИТЬ АДМИНА (кнопка) =====
@router.message(F.text == "➕ Добавить админа")
async def btn_add_admin(message: Message, state):
    from handlers.register_service import add_admin_start
    await add_admin_start(message, state)


# ===== ➖ УДАЛИТЬ АДМИНА (кнопка) =====
@router.message(F.text == "➖ Удалить админа")
async def btn_remove_admin(message: Message, state):
    from handlers.register_service import remove_admin_start
    await remove_admin_start(message, state)


# ===== 🚪 ПОКИНУТЬ РОЛЬ АДМИНИСТРАТОРА =====
@router.message(F.text == "🚪 Покинуть роль администратора")
@router.message(Command("leave_admin"))
async def leave_admin(message: Message):
    user_id = message.from_user.id
    services = await db.get_admin_services(user_id)
    owned_ids = {str(s['idservice']) for s in await db.get_owned_services(user_id)}

    # Нельзя покинуть сервисы где пользователь — владелец
    removable = [s for s in services if str(s['idservice']) not in owned_ids]

    if not removable:
        await message.answer(
            "❌ Нет сервисов из которых можно выйти.\n\n"
            "Управляющий не может покинуть собственный сервис."
        )
        return

    names = []
    for service in removable:
        await db.remove_admin(service['idservice'], user_id)
        names.append(service['service_name'])

        # Уведомляем управляющего
        try:
            svc = await db.get_service_by_id(service['idservice'])
            if svc and svc['owner_id']:
                await message.bot.send_message(
                    svc['owner_id'],
                    f"ℹ️ Администратор <code>{user_id}</code> покинул сервис "
                    f"<b>{svc['service_name']}</b>.",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.warning(f"Не удалось уведомить управляющего: {e}")

    svc_list = "\n".join([f"  • {n}" for n in names])
    await message.answer(
        f"✅ Вы покинули роль администратора:\n{svc_list}\n\n"
        f"Теперь вы обычный пользователь.",
        reply_markup=user_menu_keyboard()
    )

    # Обновляем команды меню на пользовательские
    from handlers.service_link import set_commands_for_user
    await set_commands_for_user(message.bot, user_id, 'user')


# ===== ℹ️ О МОЁМ СЕРВИСЕ =====
@router.message(F.text == "ℹ️ О моём сервисе")
async def service_info(message: Message):
    services = await db.get_admin_services(message.from_user.id)
    if not services:
        await message.answer("❌ У вас нет сервисов.")
        return

    text = "<b>ℹ️ Мои сервисы:</b>\n\n"
    for service in services:
        link = db.generate_service_link(service['idservice'])
        text += (
            f"<b>{service['service_name']}</b>\n"
            f"📞 {service['service_number']}\n"
        )
        if service.get('location_service'):
            text += f"📍 {service['location_service']}\n"
        text += (
            f"🆔 <code>{service['idservice']}</code>\n"
            f"🔗 <code>{link}</code>\n\n"
        )
    await message.answer(text, parse_mode="HTML")


# ===== ОБРАБОТКА СТАТУСОВ =====
@router.callback_query(F.data.startswith("status:"))
async def admin_status_handler(callback: CallbackQuery):
    try:
        _, status, request_id = callback.data.split(":", 2)
        await db.update_request_status(request_id, status)

        new_text = callback.message.html_text + f"\n\n<b>📌 Статус:</b> {STATUS_LABELS[status]}"
        await callback.message.edit_text(new_text, parse_mode="HTML")
        await callback.answer("✅ Статус обновлён")

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
            except Exception as e:
                logger.error(f"❌ Не удалось уведомить клиента: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка статуса: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обновлении", show_alert=True)


# ===== FALLBACK =====
@router.message()
async def fallback(message: Message):
    role, _ = await get_role(message.from_user.id)
    kb = owner_menu_keyboard() if role == 'owner' else (
         admin_menu_keyboard() if role == 'admin' else user_menu_keyboard()
    )
    await message.answer("❓ Неизвестная команда. Используйте /start.", reply_markup=kb)