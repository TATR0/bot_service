from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import URL_SITE

# ===== УВЕДОМЛЕНИЯ КЛИЕНТУ =====
CLIENT_NOTIFY = {
    "accepted": "✅ <b>Ваша заявка принята!</b>\n\nАвтосервис подтвердил запись. Ожидайте звонка для уточнения деталей.",
    "called":   "📞 <b>С вами пытаются связаться!</b>\n\nАвтосервис звонит вам для уточнения деталей заявки. Проверьте телефон.",
    "rejected": "❌ <b>Ваша заявка отклонена.</b>\n\nК сожалению, автосервис не может принять вашу заявку. Попробуйте обратиться позже или выбрать другой сервис.",
}

# ===== ПОЛЬЗОВАТЕЛЬ =====
def start_keyboard():
    """Главное меню обычного пользователя"""
    if URL_SITE:
        return ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(
                    text="🚗 Записаться в автосервис",
                    web_app=WebAppInfo(url=URL_SITE)
                )
            ]],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🚗 Записаться в автосервис")]],
            resize_keyboard=True
        )

# ===== АДМИНИСТРАТОР =====
def admin_menu_keyboard():
    """Меню администратора (назначенного управляющим)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои заявки"), KeyboardButton(text="👥 Администраторы")],
            [KeyboardButton(text="🚪 Покинуть сервис")],
        ],
        resize_keyboard=True
    )

# ===== УПРАВЛЯЮЩИЙ =====
def owner_menu_keyboard():
    """Меню управляющего (зарегистрировавшего сервис)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои заявки"), KeyboardButton(text="👥 Администраторы")],
            [KeyboardButton(text="➕ Добавить админа"), KeyboardButton(text="➖ Удалить админа")],
            [KeyboardButton(text="ℹ️ О моем сервисе")],
        ],
        resize_keyboard=True
    )

def register_service_keyboard():
    """Меню для неавторизованного пользователя"""
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="📝 Зарегистрировать сервис")
        ]],
        resize_keyboard=True
    )

# ===== ОБЩИЕ INLINE-КНОПКИ =====
def admin_keyboard(request_id: str):
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

def confirm_remove_admin_keyboard(service_id: str, admin_id: int):
    """Подтверждение удаления администратора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Удалить", callback_data=f"remove_confirm:{service_id}:{admin_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="remove_cancel")
        ]
    ])