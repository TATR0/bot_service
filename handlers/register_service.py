from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from database import db
from keyboards import start_keyboard
import re

router = Router()

# ===== РЕГИСТРАЦИЯ СЕРВИСА =====
class RegisterService(StatesGroup):
    waiting_name     = State()
    waiting_phone    = State()
    waiting_city     = State()
    waiting_location = State()
    waiting_admin_id = State()

@router.message(Command("register_service"))
async def register_service_start(message: Message, state: FSMContext):
    await message.answer(
        "🚗 <b>Регистрация автосервиса</b>\n\n"
        "Введите название вашего автосервиса:",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_name)

@router.message(RegisterService.waiting_name)
async def process_service_name(message: Message, state: FSMContext):
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
    user_input = message.text.strip()
    admin_id = None
    admin_display_name = None

    username_match = re.match(r"^@(\w+)$", user_input)
    if username_match:
        username = username_match.group(1)
        try:
            user = await bot.get_chat(username)
            admin_id = user.id
            admin_display_name = f"ID: {admin_id}"
        except Exception:
            await message.answer(
                f"❌ Не удалось найти пользователя <code>@{username}</code>\n\n"
                "Проверьте username или используйте user ID",
                parse_mode="HTML"
            )
            return
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

    try:
        data = await state.get_data()
        idservice = await db.add_service(
            data['service_name'], data['phone'],
            message.from_user.id, data['location'], data['city']
        )
        await db.add_admin(idservice, admin_id)

        success_message = db.format_registration_message(
            data['service_name'], data['phone'],
            admin_display_name, idservice,
            data['city'], data['location']
        )
        await message.answer(success_message, parse_mode="HTML", reply_markup=start_keyboard())

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
            f"❌ Ошибка при регистрации сервиса\n\n<code>{str(e)}</code>",
            parse_mode="HTML"
        )

    await state.clear()


# ===== ДОБАВЛЕНИЕ АДМИНА К СУЩЕСТВУЮЩЕМУ СЕРВИСУ =====
class AddAdmin(StatesGroup):
    waiting_service_id = State()
    waiting_admin_id   = State()

@router.message(Command("add_admin"))
async def add_admin_start(message: Message, state: FSMContext):
    services = await db.get_admin_services(message.from_user.id)
    if not services:
        await message.answer(
            "❌ У вас нет зарегистрированных сервисов\n\n"
            "Сначала зарегистрируйте сервис через /register_service",
            parse_mode="HTML"
        )
        return

    # Сохраняем список ID чтобы потом проверять
    valid_ids = [str(s["idservice"]) for s in services]
    await state.update_data(valid_ids=valid_ids)

    svc_list = "\n".join([
        f"• <code>{s['idservice']}</code>\n  {s['service_name']}"
        for s in services
    ])
    await message.answer(
        f"👥 <b>Добавление администратора</b>\n\n"
        f"Ваши сервисы:\n{svc_list}\n\n"
        f"Отправьте <b>ID сервиса</b> (нажмите на него чтобы скопировать):",
        parse_mode="HTML"
    )
    await state.set_state(AddAdmin.waiting_service_id)

@router.message(AddAdmin.waiting_service_id)
async def add_admin_service_id(message: Message, state: FSMContext):
    service_id = message.text.strip()
    data = await state.get_data()
    valid_ids = data.get('valid_ids', [])

    if service_id not in valid_ids:
        ids_str = "\n".join([f"<code>{i}</code>" for i in valid_ids])
        await message.answer(
            f"❌ ID не найден.\n\n"
            f"Вы отправили: <code>{service_id}</code>\n\n"
            f"Доступные ID:\n{ids_str}\n\n"
            f"Скопируйте ID точно из этого списка.",
            parse_mode="HTML"
        )
        return

    await state.update_data(service_id=service_id)
    await message.answer(
        "👤 Введите нового администратора:\n\n"
        "• <code>@username</code>\n"
        "• <code>123456789</code> (user ID из @userinfobot)",
        parse_mode="HTML"
    )
    await state.set_state(AddAdmin.waiting_admin_id)

@router.message(AddAdmin.waiting_admin_id)
async def add_admin_finish(message: Message, state: FSMContext, bot):
    user_input = message.text.strip()
    admin_id = None

    username_match = re.match(r"^@(\w+)$", user_input)
    if username_match:
        try:
            user = await bot.get_chat(username_match.group(1))
            admin_id = user.id
        except Exception:
            await message.answer("❌ Пользователь не найден. Проверьте username.")
            return
    elif user_input.isdigit():
        admin_id = int(user_input)
        try:
            await bot.get_chat(admin_id)
        except Exception:
            await message.answer("❌ Пользователь с таким ID не найден.")
            return
    else:
        await message.answer("❌ Некорректный формат. Используйте @username или числовой ID.")
        return

    data = await state.get_data()
    service_id = data['service_id']

    # Проверяем что ещё не администратор
    existing = await db.get_admins_by_service(service_id)
    if any(a['idusertg'] == admin_id for a in existing):
        await message.answer("⚠️ Этот пользователь уже является администратором этого сервиса.")
        await state.clear()
        return

    await db.add_admin(service_id, admin_id)

    # Уведомляем нового админа
    try:
        service = await db.get_service_by_id(service_id)
        svc_name = service['service_name'] if service else "сервис"
        await bot.send_message(
            admin_id,
            f"👋 Вас добавили администратором!\n\n"
            f"<b>Сервис:</b> {svc_name}\n\n"
            f"Нажмите /start для управления заявками.",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить нового админа: {e}")

    await message.answer(
        f"✅ Администратор <code>{admin_id}</code> успешно добавлен!",
        parse_mode="HTML"
    )
    await state.clear()