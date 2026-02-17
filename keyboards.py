from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import URL_SITE

# ===== ОСНОВНЫЕ КНОПКИ =====
def start_keyboard():
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="🚗 Записаться в автосервис",
                web_app=WebAppInfo(url=URL_SITE)
            )
        ]],
        resize_keyboard=True
    )

def register_service_keyboard():
    """Меню для неавторизованного админа"""
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="📝 Зарегистрировать сервис")
        ]],
        resize_keyboard=True
    )

# ===== АДМИН КНОПКИ =====
def admin_keyboard(request_id: int):
    """Кнопки для обновления статуса заявки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принято", callback_data=f"status:accepted:{request_id}"),
            InlineKeyboardButton(text="📞 Связались", callback_data=f"status:called:{request_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"status:rejected:{request_id}")
        ]
    ])

def admin_menu_keyboard():
    """Главное меню админа"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои заявки")],
            [KeyboardButton(text="📝 Зарегистрировать новый сервис")],
            [KeyboardButton(text="ℹ️ О моем сервисе")]
        ],
        resize_keyboard=True
    )