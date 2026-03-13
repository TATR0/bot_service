from aiogram import Router, F
from aiogram.types import Message, WebAppInfo
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import URL_SITE
from database import db
import logging

logger = logging.getLogger(__name__)
router = Router()


async def _refresh_commands(message: Message):
    """Обновить команды меню для пользователя по его роли"""
    try:
        from bot import set_commands_for_user
        await set_commands_for_user(message.from_user.id)
    except Exception as e:
        logger.warning(f"Не удалось обновить команды: {e}")


@router.message(CommandStart())
async def start_with_service_link(message: Message):
    """Обработка /start [SVC_xxxx]"""
    logger.info(f"📥 Получена команда /start: {message.text}")

    arg = None
    if message.text and message.text.startswith("/start "):
        parts = message.text.strip().split(' ', 1)
        if len(parts) == 2:
            arg = parts[1]

    logger.info(f"🔍 Параметр: {arg}")

    # ── Ссылка на конкретный сервис ──────────────────────────────
    if arg and arg.startswith("SVC_"):
        service_id = arg[4:]
        logger.info(f"🎯 Обнаружена ссылка сервиса: {service_id}")

        web_app_url = f"{URL_SITE}?service_id={service_id}"
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(
                    text="🚗 Записаться онлайн",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            "🔧 <b>Добро пожаловать в автосервис!</b>\n\n"
            "Чтобы отправить заявку на обслуживание, нажмите кнопку ниже 👇",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info(f"✅ Кнопка web app отправлена пользователю {message.from_user.id}")
        return

    # ── Стандартный /start — определяем роль ─────────────────────
    user_id = message.from_user.id
    logger.info(f"👤 Пользователь {user_id} нажал /start без параметра")

    # Обновляем команды меню под роль
    await _refresh_commands(message)

    is_owner = await db.is_owner(user_id)
    is_admin = await db.is_admin(user_id)

    if is_owner:
        from keyboards import owner_menu_keyboard
        owned = await db.get_owned_services(user_id)
        svc_names = ", ".join(s['service_name'] for s in owned)
        await message.answer(
            f"👑 <b>Добро пожаловать, управляющий!</b>\n\n"
            f"Ваши сервисы: <b>{svc_names}</b>\n\n"
            f"Используйте меню команд или кнопки ниже 👇",
            parse_mode="HTML",
            reply_markup=owner_menu_keyboard()
        )
    elif is_admin:
        from keyboards import admin_menu_keyboard
        services = await db.get_admin_services(user_id)
        svc_names = ", ".join(s['service_name'] for s in services)
        await message.answer(
            f"👋 <b>Добро пожаловать, администратор!</b>\n\n"
            f"Ваши сервисы: <b>{svc_names}</b>\n\n"
            f"Используйте меню команд или кнопки ниже 👇",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard()
        )
    else:
        from keyboards import start_keyboard
        await message.answer(
            "🚗 <b>Добро пожаловать в систему записи автосервиса!</b>\n\n"
            "Вы можете:\n"
            "• Записаться в автосервис через кнопку ниже\n"
            "• Зарегистрировать свой сервис командой /register_service\n"
            "• Проверить статус заявок командой /my_requests",
            parse_mode="HTML",
            reply_markup=start_keyboard()
        )