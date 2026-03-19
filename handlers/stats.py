"""
handlers/stats.py

Статистика сервиса для admin и owner:
  - Общее кол-во заявок и разбивка по статусам
  - За сегодня / неделю / месяц
  - Топ-3 популярных услуги
  - Конверсия (принято / всего)
  - Визуальный ASCII-прогресс-бар
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from config import SERVICE_NAMES, STATUS_LABELS
import logging

logger = logging.getLogger(__name__)
router = Router()


def progress_bar(value: int, total: int, width: int = 10) -> str:
    """Возвращает ASCII прогресс-бар, например: ████░░░░░░ 40%"""
    if total == 0:
        return "░" * width + " 0%"
    filled = round(value / total * width)
    pct = round(value / total * 100)
    return "█" * filled + "░" * (width - filled) + f" {pct}%"


def format_stats(service_name: str, stats: dict) -> str:
    total = stats["total"]
    by_status = stats["by_status"]

    # Порядок и иконки статусов
    status_order = [
        ("new",       "🆕 Новые"),
        ("accepted",  "✅ Принятые"),
        ("called",    "📞 Звонили"),
        ("rejected",  "❌ Отказы"),
        ("cancelled", "🚫 Отменены"),
    ]

    text = (
        f"<b>📊 Статистика сервиса</b>\n"
        f"<b>{service_name}</b>\n\n"
        f"<b>📅 Период</b>\n"
        f"  Сегодня:   <b>{stats['today']}</b>\n"
        f"  Эта неделя: <b>{stats['week']}</b>\n"
        f"  Этот месяц: <b>{stats['month']}</b>\n\n"
        f"<b>📋 Всего заявок: {total}</b>\n"
    )

    if total > 0:
        text += "\n"
        for key, label in status_order:
            cnt = by_status.get(key, 0)
            if cnt > 0:
                bar = progress_bar(cnt, total)
                text += f"  {label}: <b>{cnt}</b>\n  {bar}\n"

        text += f"\n<b>🎯 Конверсия:</b> {stats['conversion']}%\n"
        text += "<i>(принято + звонили / всего без отмен)</i>\n"

    if stats["top_services"]:
        text += "\n<b>🔧 Популярные услуги:</b>\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (stype, cnt) in enumerate(stats["top_services"]):
            sname = SERVICE_NAMES.get(stype, stype or "—")
            medal = medals[i] if i < len(medals) else "•"
            text += f"  {medal} {sname}: <b>{cnt}</b>\n"

    if total == 0:
        text += "\n<i>Заявок пока нет — статистика появится после первой записи.</i>"

    return text


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    is_owner = await db.is_owner(user_id)
    is_admin_user = await db.is_admin(user_id)

    if not (is_owner or is_admin_user):
        await message.answer("❌ Статистика доступна только сотрудникам сервиса.")
        return

    if is_owner:
        services = await db.get_owned_services(user_id)
    else:
        services = await db.get_admin_services(user_id)

    if not services:
        await message.answer("❌ У вас нет сервисов.")
        return

    for svc in services:
        stats = await db.get_service_stats(svc['idservice'])
        text = format_stats(svc['service_name'], stats)
        await message.answer(text, parse_mode="HTML")
