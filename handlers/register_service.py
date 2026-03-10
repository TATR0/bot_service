from aiogram import Router, F
from aiogram.types import Message, User
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from database import db
from keyboards import start_keyboard
import re

router = Router()

class RegisterService(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_city = State()
    waiting_location = State()
    waiting_admin_id = State()

@router.message(Command("register_service"))
async def register_service_start(message: Message, state: FSMContext):
    """Начало регистрации сервиса"""
    await message.answer(
        "🚗 <b>Регистрация автосервиса</b>\n\n"
        "Введите название вашего автосервиса:",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_name)

@router.message(RegisterService.waiting_name)
async def process_service_name(message: Message, state: FSMContext):
    """Получение названия сервиса"""
    service_name = message.text.strip()
    
    if len(service_name) < 3:
        await message.answer("❌ Название должно быть не менее 3 символов")
        return
    
    await state.update_data(service_name=service_name)
    await message.answer(
        "📞 Введите номер телефона автосервиса:\n\n"
        "<i>Пример: +7 (999) 123-45-67</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_phone)

@router.message(RegisterService.waiting_phone)
async def process_service_phone(message: Message, state: FSMContext):
    """Получение номера телефона"""
    phone = message.text.strip()
    
    if len(phone) < 10:
        await message.answer("❌ Некорректный номер телефона. Попробуйте ещё раз")
        return
    
    await state.update_data(phone=phone)
    await message.answer(
        "🏙 Введите город, в котором находится автосервис:\n\n"
        "<i>Пример: Москва</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_city)

@router.message(RegisterService.waiting_city)
async def process_service_city(message: Message, state: FSMContext):
    """Получение города сервиса"""
    city = message.text.strip()
    
    if len(city) < 2:
        await message.answer("❌ Название города должно быть не менее 2 символов")
        return
    
    await state.update_data(city=city)
    await message.answer(
        "📍 Введите адрес автосервиса (улица, дом):\n\n"
        "<i>Пример: ул. Пушкина, д. 10</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_location)

@router.message(RegisterService.waiting_location)
async def process_service_location(message: Message, state: FSMContext):
    """Получение адреса сервиса"""
    location = message.text.strip()
    
    if len(location) < 5:
        await message.answer("❌ Адрес должен быть не менее 5 символов")
        return
    
    await state.update_data(location=location)
    await message.answer(
        "👤 <b>Введите администратора сервиса:</b>\n\n"
        "Способы ввода:\n"
        "• <code>@username</code> (если есть username)\n"
        "• <code>123456789</code> (user ID из @userinfobot)\n\n"
        "<i>Как найти user ID?</i>\n"
        "Напишите боту @userinfobot и он выведет ваш ID",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_admin_id)

@router.message(RegisterService.waiting_admin_id)
async def process_admin_id(message: Message, state: FSMContext, bot):
    """Получение ID администратора"""
    user_input = message.text.strip()
    admin_id = None
    admin_display_name = None

    # Проверка на @username
    username_match = re.match(r"^@(\w+)$", user_input)
    if username_match:
        username = username_match.group(1)
        try:
            user = await bot.get_chat(username)
            admin_id = user.id
            admin_display_name = f"ID: {admin_id}"
        except Exception as e:
            await message.answer(
                f"❌ Не удалось найти пользователя <code>@{username}</code>\n\n"
                "Проверьте username или используйте user ID",
                parse_mode="HTML"
            )
            return
    # Проверка на user ID
    elif user_input.isdigit():
        admin_id = int(user_input)
        try:
            user = await bot.get_chat(admin_id)
            admin_display_name = f"ID: {admin_id}"
        except Exception:
            await message.answer(
                f"❌ Пользователь с ID <code>{admin_id}</code> не найден\n\n"
                "Проверьте ID или используйте username",
                parse_mode="HTML"
            )
            return
    else:
        await message.answer(
            "❌ Некорректный формат\n\n"
            "Используйте:\n"
            "• <code>@username</code>\n"
            "• <code>123456789</code> (только цифры для ID)",
            parse_mode="HTML"
        )
        return

    # Сохранение в БД
    try:
        data = await state.get_data()
        idservice = await db.add_service(
            data['service_name'],
            data['phone'],
            message.from_user.id,  # owner_id — тот кто регистрирует
            data['location'],  # адрес
            data['city']       # ← ДОБАВЛЯЕМ ГОРОД
        )
        await db.add_admin(idservice, admin_id)

        # Используем новый метод для форматирования сообщения
        success_message = db.format_registration_message(
            data['service_name'],
            data['phone'],
            admin_display_name,
            idservice,
            data['city'],      # ← ГОРОД
            data['location']   # ← АДРЕС
        )

        await message.answer(
            success_message,
            parse_mode="HTML",
            reply_markup=start_keyboard()
        )

        # Уведомление администратору
        try:
            await bot.send_message(
                admin_id,
                f"👋 Вас добавили администратором автосервиса!\n\n"
                f"<b>Название:</b> {data['service_name']}\n"
                f"<b>Телефон:</b> {data['phone']}\n"
                f"<b>Город:</b> {data['city']}\n"
                f"<b>Адрес:</b> {data['location']}\n\n"
                f"Теперь вы можете управлять заявками. Нажмите /start",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление админу: {e}")

    except Exception as e:
        print(f"Ошибка при регистрации: {e}")
        await message.answer(
            f"❌ Ошибка при регистрации сервиса\n\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )

    await state.clear()
    