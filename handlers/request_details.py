"""
handlers/request_details.py

Фичи:
  1. Детальный просмотр заявки (клиент и admin/owner)
  2. Фильтрация заявок по статусу для admin/owner
  3. Отмена заявки клиентом (только статус 'new')
  4. Напоминания: фоновая задача — если заявка висит в 'new' > N часов,
     уведомляет всех активных админов сервиса
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import SERVICE_NAMES, URGENCY_NAMES, STATUS_LABELS
import logging
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = Router()

# Порог для напоминания (в часах)
REMINDER_THRESHOLD_HOURS = 2
# Интервал проверки фоновой задачи (в секундах)
REMINDER_CHECK_INTERVAL = 60 * 30  # каждые 30 минут


# ══════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════

def format_request_detail(req: dict, service_name: str = "") -> str:
    """Форматирует полную карточку заявки"""
    status_label = STATUS_LABELS.get(req['status'], req['status'])
    service_type_label = SERVICE_NAMES.get(req['service_type'], req['service_type'] or "—")
    urgency_label = URGENCY_NAMES.get(req['urgency'], req['urgency'] or "—")
    created = req['createdate'].strftime('%d.%m.%Y %H:%M') if req.get('createdate') else "—"

    text = (
        f"<b>═══ 🔍 ЗАЯВКА ═══</b>\n\n"
        f"<b>ID:</b> <code>{req['idrequests']}</code>\n"
        f"<b>Статус:</b> {status_label}\n"
        f"<b>Дата:</b> {created}\n\n"
        f"<b>👤 КЛИЕНТ</b>\n"
        f"Имя: <b>{req['client_name']}</b>\n"
        f"Телефон: <code>{req['phone']}</code>\n"
    )
    if service_name:
        text += f"\n<b>🏪 СЕРВИС</b>\n{service_name}\n"
    text += (
        f"\n<b>🚙 АВТОМОБИЛЬ</b>\n"
        f"Марка: <b>{req.get('brand', '—')}</b>\n"
        f"Модель: <b>{req.get('model', '—')}</b>\n"
        f"Гос. номер: <code>{req.get('plate', '—')}</code>\n\n"
        f"<b>🔧 УСЛУГА</b>\n"
        f"Тип: {service_type_label}\n"
        f"Срочность: {urgency_label}\n"
    )
    comment = req.get('comment', '')
    if comment:
        text += f"\n<b>💬 Комментарий</b>\n<i>{comment}</i>\n"
    return text


def filter_keyboard(current: str = "all") -> InlineKeyboardMarkup:
    """Инлайн-кнопки для фильтрации заявок по статусу"""
    statuses = [
        ("all", "📋 Все"),
        ("new", "🆕 Новые"),
        ("accepted", "✅ Принятые"),
        ("called", "📞 Звонок"),
        ("rejected", "❌ Отказ"),
    ]
    buttons = []
    row = []
    for key, label in statuses:
        mark = "·" if key == current else ""
        row.append(InlineKeyboardButton(
            text=f"{mark}{label}{mark}",
            callback_data=f"filter_req:{key}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def client_cancel_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отменить заявку", callback_data=f"cancel_req:{request_id}"),
        InlineKeyboardButton(text="✅ Оставить", callback_data="cancel_req_no")
    ]])


def request_list_keyboard(requests: list, filter_key: str = "all") -> InlineKeyboardMarkup:
    """Список заявок как кнопки + кнопки фильтра"""
    buttons = []
    for req in requests[:15]:
        status_icon = {
            "new": "🆕", "accepted": "✅", "called": "📞", "rejected": "❌"
        }.get(req['status'], "❓")
        short_id = str(req['idrequests'])[:8]
        label = f"{status_icon} {req['client_name'][:14]} · {short_id}…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"view_req:{req['idrequests']}"
        )])

    # Кнопки фильтра внизу
    filter_row = []
    for key, icon in [("all", "📋"), ("new", "🆕"), ("accepted", "✅"), ("called", "📞"), ("rejected", "❌")]:
        mark = "·" if key == filter_key else ""
        filter_row.append(InlineKeyboardButton(
            text=f"{mark}{icon}{mark}",
            callback_data=f"filter_req:{key}"
        ))
    buttons.append(filter_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ══════════════════════════════════════════════════════════
#  1. ДЕТАЛЬНЫЙ ПРОСМОТР — КЛИЕНТ
# ══════════════════════════════════════════════════════════

@router.message(Command("request"))
async def cmd_view_request(message: Message):
    """
    /request <ID> — просмотр конкретной заявки.
    Клиент видит только свои заявки.
    Admin/owner видит любую заявку своего сервиса.
    """
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "ℹ️ Укажите ID заявки:\n<code>/request xxxxxxxx-xxxx-...</code>",
            parse_mode="HTML"
        )
        return

    req_id = parts[1].strip()
    req = await db.get_request(req_id)

    if not req:
        await message.answer("❌ Заявка не найдена.")
        return

    user_id = message.from_user.id
    is_owner = await db.is_owner(user_id)
    is_admin_user = await db.is_admin(user_id)

    # Проверяем доступ
    if not (is_owner or is_admin_user):
        # Обычный клиент — только свои заявки
        if req['idclienttg'] != user_id:
            await message.answer("❌ У вас нет доступа к этой заявке.")
            return
        svc = await db.get_service_by_id(req['idservice']) if req.get('idservice') else None
        svc_name = svc['service_name'] if svc else ""
        text = format_request_detail(req, svc_name)
        markup = None
        if req['status'] == 'new':
            markup = client_cancel_keyboard(str(req['idrequests']))
        await message.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        # Admin / owner
        svc = await db.get_service_by_id(req['idservice']) if req.get('idservice') else None
        svc_name = svc['service_name'] if svc else ""
        text = format_request_detail(req, svc_name)
        await message.answer(text, parse_mode="HTML")


# ══════════════════════════════════════════════════════════
#  2. ФИЛЬТРАЦИЯ ЗАЯВОК (admin / owner)
# ══════════════════════════════════════════════════════════

@router.message(Command("filter_requests"))
@router.message(F.text == "🔎 Фильтр заявок")
async def cmd_filter_requests(message: Message):
    user_id = message.from_user.id
    is_owner = await db.is_owner(user_id)
    is_admin_user = await db.is_admin(user_id)

    if not (is_owner or is_admin_user):
        await message.answer("❌ Команда доступна только сотрудникам сервиса.")
        return

    if is_owner:
        services = await db.get_owned_services(user_id)
    else:
        services = await db.get_admin_services(user_id)

    if not services:
        await message.answer("❌ У вас нет сервисов.")
        return

    # Собираем заявки по всем сервисам, фильтр — все
    all_requests = []
    for svc in services:
        reqs = await db.get_service_requests(svc['idservice'])
        all_requests.extend(reqs)

    # Сортируем по дате
    all_requests.sort(key=lambda r: r['createdate'] or datetime.min, reverse=True)

    if not all_requests:
        await message.answer("📋 Заявок пока нет.")
        return

    await message.answer(
        f"<b>📋 Заявки ({len(all_requests)} шт.)</b>\n"
        f"Выберите заявку для просмотра или фильтр по статусу:",
        parse_mode="HTML",
        reply_markup=request_list_keyboard(all_requests, "all")
    )


@router.callback_query(F.data.startswith("filter_req:"))
async def cb_filter_requests(callback: CallbackQuery):
    filter_key = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    is_owner = await db.is_owner(user_id)
    is_admin_user = await db.is_admin(user_id)

    if not (is_owner or is_admin_user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    if is_owner:
        services = await db.get_owned_services(user_id)
    else:
        services = await db.get_admin_services(user_id)

    all_requests = []
    for svc in services:
        reqs = await db.get_service_requests(svc['idservice'])
        all_requests.extend(reqs)

    all_requests.sort(key=lambda r: r['createdate'] or datetime.min, reverse=True)

    if filter_key != "all":
        filtered = [r for r in all_requests if r['status'] == filter_key]
    else:
        filtered = all_requests

    count = len(filtered)
    status_title = {
        "all": "Все", "new": "Новые 🆕", "accepted": "Принятые ✅",
        "called": "Звонок 📞", "rejected": "Отказ ❌"
    }.get(filter_key, filter_key)

    if not filtered:
        await callback.message.edit_text(
            f"<b>📋 {status_title} — 0 заявок</b>\n\nВыберите другой фильтр:",
            parse_mode="HTML",
            reply_markup=request_list_keyboard([], filter_key)
        )
    else:
        await callback.message.edit_text(
            f"<b>📋 {status_title} ({count} шт.)</b>\n\nВыберите заявку для просмотра:",
            parse_mode="HTML",
            reply_markup=request_list_keyboard(filtered, filter_key)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("view_req:"))
async def cb_view_request(callback: CallbackQuery):
    req_id = callback.data.split(":", 1)[1]
    req = await db.get_request(req_id)

    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    svc = await db.get_service_by_id(req['idservice']) if req.get('idservice') else None
    svc_name = svc['service_name'] if svc else ""
    text = format_request_detail(req, svc_name)

    # Admin видит кнопки смены статуса под карточкой
    from keyboards import admin_keyboard
    await callback.message.answer(text, parse_mode="HTML", reply_markup=admin_keyboard(req_id))
    await callback.answer()


# ══════════════════════════════════════════════════════════
#  3. ОТМЕНА ЗАЯВКИ КЛИЕНТОМ
# ══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cancel_req:"))
async def cb_cancel_request(callback: CallbackQuery):
    req_id = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    req = await db.get_request(req_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if req['idclienttg'] != user_id:
        await callback.answer("❌ Это не ваша заявка", show_alert=True)
        return

    if req['status'] != 'new':
        await callback.answer(
            "⚠️ Заявку нельзя отменить — она уже обрабатывается.",
            show_alert=True
        )
        return

    await db.update_request_status(req_id, 'cancelled')

    # Уведомляем администраторов сервиса
    if req.get('idservice'):
        admins = await db.get_admins_by_service(req['idservice'])
        svc = await db.get_service_by_id(req['idservice'])
        svc_name = svc['service_name'] if svc else "сервис"
        for admin in admins:
            try:
                await callback.bot.send_message(
                    admin['idusertg'],
                    f"🚫 <b>Клиент отменил заявку</b>\n\n"
                    f"Клиент: <b>{req['client_name']}</b>\n"
                    f"Телефон: <code>{req['phone']}</code>\n"
                    f"Сервис: {svc_name}\n"
                    f"ID: <code>{req_id}</code>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить админа {admin['idusertg']}: {e}")

    await callback.message.edit_text(
        f"✅ Заявка <code>{req_id[:8]}…</code> отменена.",
        parse_mode="HTML"
    )
    await callback.answer("Заявка отменена")


@router.callback_query(F.data == "cancel_req_no")
async def cb_cancel_req_no(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Заявка сохранена")


# ══════════════════════════════════════════════════════════
#  4. ФОНОВАЯ ЗАДАЧА — НАПОМИНАНИЯ
# ══════════════════════════════════════════════════════════

async def reminder_loop(bot):
    """
    Каждые REMINDER_CHECK_INTERVAL секунд проверяет заявки в статусе 'new',
    которые старше REMINDER_THRESHOLD_HOURS часов,
    и отправляет напоминание всем активным администраторам сервиса.

    Чтобы не спамить повторно — добавляем локальный set уже уведомлённых.
    Сет сбрасывается при рестарте (при необходимости можно вынести в БД).
    """
    notified: set = set()

    while True:
        try:
            stale = await db.get_stale_requests(REMINDER_THRESHOLD_HOURS)
            for req in stale:
                req_id = str(req['idrequests'])
                if req_id in notified:
                    continue

                admins = await db.get_admins_by_service(req['idservice'])
                if not admins:
                    continue

                svc = await db.get_service_by_id(req['idservice'])
                svc_name = svc['service_name'] if svc else "—"
                age_hours = int((datetime.now() - req['createdate']).total_seconds() // 3600)

                text = (
                    f"⏰ <b>Напоминание: необработанная заявка</b>\n\n"
                    f"Заявка висит <b>{age_hours} ч.</b> без ответа.\n\n"
                    f"<b>Клиент:</b> {req['client_name']}\n"
                    f"<b>Телефон:</b> <code>{req['phone']}</code>\n"
                    f"<b>Сервис:</b> {svc_name}\n"
                    f"<b>ID:</b> <code>{req_id}</code>"
                )

                for admin in admins:
                    try:
                        from keyboards import admin_keyboard
                        await bot.send_message(
                            admin['idusertg'],
                            text,
                            parse_mode="HTML",
                            reply_markup=admin_keyboard(req_id)
                        )
                        logger.info(f"⏰ Напоминание отправлено {admin['idusertg']} по заявке {req_id[:8]}")
                    except Exception as e:
                        logger.warning(f"Не удалось отправить напоминание {admin['idusertg']}: {e}")

                notified.add(req_id)

        except Exception as e:
            logger.error(f"❌ Ошибка в reminder_loop: {e}", exc_info=True)

        await asyncio.sleep(REMINDER_CHECK_INTERVAL)


def start_reminder_task(bot):
    """Запускает фоновую задачу напоминаний. Вызывать из on_startup."""
    asyncio.create_task(reminder_loop(bot))
    logger.info(f"✅ Фоновая задача напоминаний запущена (порог: {REMINDER_THRESHOLD_HOURS}ч, интервал: {REMINDER_CHECK_INTERVAL//60}мин)")
