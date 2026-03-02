from aiogram import Router, F
from aiogram.types import Message, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import URL_SITE
from database import db
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def start_with_service_link(message: Message):
    """Обработка /start SVC_xxxx"""
    logger.info(f"📥 Получена команда /start: {message.text}")
    
    # Получаем параметр из /start
    arg = None
    if message.text.startswith("/start "):
        parts = message.text.strip().split(' ', 1)
        if len(parts) == 2:
            arg = parts[1]
    
    logger.info(f"🔍 Параметр: {arg}")
    
    # ✅ Если пришла ссылка с SVC_ — показываем форму для этого сервиса
    if arg and arg.startswith("SVC_"):
        service_id = arg[4:]  # Убираем префикс "SVC_"
        logger.info(f"🎯 Обнаружена ссылка сервиса: {service_id}")
        
        web_app_url = f"{URL_SITE}?service_id={service_id}"
        logger.info(f"🌐 URL web app: {web_app_url}")
        
        # ✅ ПРАВИЛЬНЫЙ СПОСОБ: ReplyKeyboardMarkup с KeyboardButton
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
            f"🔧 <b>Добро пожаловать в автосервис!</b>\n\n"
            f"Чтобы отправить заявку на обслуживание, нажмите кнопку ниже 👇",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info(f"✅ Кнопка web app отправлена пользователю {message.from_user.id}")
        return
    
    # ===== СТАНДАРТНАЯ ЛОГИКА /start (если нет параметра SVC_) =====
    logger.info(f"👤 Пользователь {message.from_user.id} нажал /start без параметра")
    
    # Проверяем, админ ли это
    user_services = await db.get_admin_services(message.from_user.id)
    
    if user_services:
        from keyboards import admin_menu_keyboard
        logger.info(f"✅ Пользователь {message.from_user.id} - администратор")
        await message.answer(
            "👋 <b>Добро пожаловать, администратор!</b>",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard()
        )
    else:
        from keyboards import start_keyboard
        logger.info(f"👥 Пользователь {message.from_user.id} - клиент")
        await message.answer(
            "🚗 <b>Добро пожаловать в систему записи автосервиса!</b>\n\n"
            "🔧 Чтобы подключить автосервис — нажмите /register_service",
            parse_mode="HTML",
            reply_markup=start_keyboard()
        )