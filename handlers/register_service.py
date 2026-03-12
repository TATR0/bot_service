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
        "🚗 <b>Регистрация автосервиса</b>\n\nВведите название вашего автосервиса:",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_name)

@router.message(RegisterService.waiting_name)
async def process_service_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Название должно быть не менее 3 символов")
        return
    await state.update_data(service_name=name)
    await message.answer(
        "📞 Введите номер телефона автосервиса:\n\n<i>Пример: +7 (999) 123-45-67</i>",
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
        "🏙 Введите город:\n\n<i>Пример: Москва</i>",
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
        "📍 Введите адрес (улица, дом):\n\n<i>Пример: ул. Пушкина, д. 10</i>",
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
        "• <code>@username</code>\n"
        "• <code>123456789</code> (user ID из @userinfobot)",
        parse_mode="HTML"
    )
    await state.set_state(RegisterService.waiting_admin_id)

@router.message(RegisterService.waiting_admin_id)
async def process_admin_id(message: Message, state: FSMContext, bot):
    admin_id, admin_display_name = await resolve_user(message, bot, message.text.strip())
    if admin_id is None:
        return

    try:
        data = await state.get_data()
        idservice = await db.add_service(
            data['service_name'], data['phone'],
            message.from_user.id, data['location'], data['city']
        )
        await db.add_admin(idservice, admin_id)

        await message.answer(
            db.format_registration_message(
                data['service_name'], data['phone'],
                admin_display_name, idservice,
                data['city'], data['location']
            ),
            parse_mode="HTML", reply_markup=start_keyboard()
        )
        try:
            await bot.send_message(
                admin_id,
                f"👋 Вас добавили администратором автосервиса!\n\n"
                f"<b>Название:</b> {data['service_name']}\n"
                f"<b>Телефон:</b> {data['phone']}\n"
                f"<b>Город:</b> {data['city']}\n"
                f"<b>Адрес:</b> {data['location']}\n\n"
                f"Нажмите /start для управления заявками.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Не удалось уведомить админа: {e}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при регистрации\n\n<code>{e}</code>", parse_mode="HTML")

    await state.clear()


# ===== ДОБАВЛЕНИЕ АДМИНА =====
class AddAdmin(StatesGroup):
    waiting_service_id = State()
    waiting_admin_id   = State()

@router.message(Command("add_admin"))
async def add_admin_start(message: Message, state: FSMContext):
    owned = await db.get_owned_services(message.from_user.id)
    if not owned:
        await message.answer(
            "❌ У вас нет сервисов, которыми вы управляете.\n\n"
            "Добавлять администраторов может только управляющий.",
            parse_mode="HTML"
        )
        return

    valid_ids = [str(s["idservice"]) for s in owned]
    await state.update_data(valid_ids=valid_ids)

    svc_list = "\n".join([f"• <code>{s['idservice']}</code>\n  {s['service_name']}" for s in owned])
    await message.answer(
        f"👥 <b>Добавление администратора</b>\n\n"
        f"Ваши сервисы:\n{svc_list}\n\n"
        f"Отправьте <b>ID сервиса</b>:",
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
            f"❌ ID не найден.\n\nВы отправили: <code>{service_id}</code>\n\n"
            f"Доступные ID:\n{ids_str}",
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
    admin_id, _ = await resolve_user(message, bot, message.text.strip())
    if admin_id is None:
        return

    data = await state.get_data()
    service_id = data['service_id']

    # Проверяем активных администраторов
    existing = await db.get_admins_by_service(service_id)
    if any(a['idusertg'] == admin_id for a in existing):
        await message.answer("⚠️ Этот пользователь уже является администратором.")
        await state.clear()
        return

    await db.add_admin(service_id, admin_id)

    try:
        service = await db.get_service_by_id(service_id)
        svc_name = service['service_name'] if service else "сервис"
        await bot.send_message(
            admin_id,
            f"👋 Вас добавили администратором!\n\n<b>Сервис:</b> {svc_name}\n\nНажмите /start.",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить нового админа: {e}")

    await message.answer(f"✅ Администратор <code>{admin_id}</code> успешно добавлен!", parse_mode="HTML")
    await state.clear()


# ===== УДАЛЕНИЕ АДМИНА =====
class RemoveAdmin(StatesGroup):
    waiting_service_id = State()
    waiting_admin_id   = State()

@router.message(Command("remove_admin"))
async def remove_admin_start(message: Message, state: FSMContext):
    owned = await db.get_owned_services(message.from_user.id)
    if not owned:
        await message.answer(
            "❌ У вас нет сервисов, которыми вы управляете.",
            parse_mode="HTML"
        )
        return

    valid_ids = [str(s["idservice"]) for s in owned]
    await state.update_data(valid_ids=valid_ids)

    svc_list = "\n".join([f"• <code>{s['idservice']}</code>\n  {s['service_name']}" for s in owned])
    await message.answer(
        f"🗑 <b>Удаление администратора</b>\n\n"
        f"Ваши сервисы:\n{svc_list}\n\n"
        f"Отправьте <b>ID сервиса</b>:",
        parse_mode="HTML"
    )
    await state.set_state(RemoveAdmin.waiting_service_id)

@router.message(RemoveAdmin.waiting_service_id)
async def remove_admin_service_id(message: Message, state: FSMContext):
    service_id = message.text.strip()
    data = await state.get_data()
    valid_ids = data.get('valid_ids', [])

    if service_id not in valid_ids:
        await message.answer(f"❌ ID не найден: <code>{service_id}</code>", parse_mode="HTML")
        return

    # Показываем список активных администраторов
    admins = await db.get_admins_by_service(service_id)
    if not admins:
        await message.answer("❌ У этого сервиса нет администраторов.")
        await state.clear()
        return

    await state.update_data(service_id=service_id)

    admin_list = "\n".join([f"• <code>{a['idusertg']}</code>" for a in admins])
    await message.answer(
        f"👥 <b>Администраторы сервиса:</b>\n\n{admin_list}\n\n"
        f"Введите <b>Telegram ID</b> администратора для удаления:",
        parse_mode="HTML"
    )
    await state.set_state(RemoveAdmin.waiting_admin_id)

@router.message(RemoveAdmin.waiting_admin_id)
async def remove_admin_finish(message: Message, state: FSMContext, bot):
    user_input = message.text.strip()
    if not user_input.isdigit():
        await message.answer("❌ Введите числовой Telegram ID администратора.")
        return

    admin_id = int(user_input)
    data = await state.get_data()
    service_id = data['service_id']

    # Проверяем что такой админ есть
    admins = await db.get_admins_by_service(service_id)
    if not any(a['idusertg'] == admin_id for a in admins):
        await message.answer(f"❌ Администратор <code>{admin_id}</code> не найден в этом сервисе.", parse_mode="HTML")
        await state.clear()
        return

    await db.remove_admin(service_id, admin_id)

    # Уведомляем удалённого админа
    try:
        service = await db.get_service_by_id(service_id)
        svc_name = service['service_name'] if service else "сервис"
        await bot.send_message(
            admin_id,
            f"ℹ️ Вы были удалены из администраторов сервиса <b>{svc_name}</b>.",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить удалённого админа: {e}")

    await message.answer(
        f"✅ Администратор <code>{admin_id}</code> удалён.", parse_mode="HTML"
    )
    await state.clear()


# ===== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ =====
async def resolve_user(message: Message, bot, user_input: str):
    """Получить Telegram ID из @username или числового ID. Возвращает (id, display_name) или (None, None)"""
    username_match = re.match(r"^@(\w+)$", user_input)
    if username_match:
        try:
            # ✅ FIX: используем get_chat для получения ID по username
            user = await bot.get_chat(f"@{username_match.group(1)}")
            return user.id, f"@{username_match.group(1)} (ID: {user.id})"
        except Exception:
            await message.answer(
                f"❌ Не удалось найти пользователя <code>@{username_match.group(1)}</code>\n\n"
                "Убедитесь что пользователь писал боту хотя бы раз, или используйте числовой ID.",
                parse_mode="HTML"
            )
            return None, None
    elif user_input.isdigit():
        admin_id = int(user_input)
        try:
            await bot.get_chat(admin_id)
            return admin_id, f"ID: {admin_id}"
        except Exception:
            await message.answer(
                f"❌ Пользователь с ID <code>{admin_id}</code> не найден.",
                parse_mode="HTML"
            )
            return None, None
    else:
        await message.answer(
            "❌ Некорректный формат.\n\n"
            "• <code>@username</code>\n"
            "• <code>123456789</code> (числовой ID)",
            parse_mode="HTML"
        )
        return None, None
    