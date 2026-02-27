import asyncpg
from config import PG_USER, PG_PASSWORD, PG_HOST, PG_PORT, PG_DB, BOT_USERNAME
from uuid import uuid4
from datetime import datetime

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Подключение к БД"""
        self.pool = await asyncpg.create_pool(
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DB,
            host=PG_HOST,
            port=PG_PORT,
            min_size=5,
            max_size=20
        )
        print("✅ БД подключена")

    async def close(self):
        """Закрытие подключения к БД"""
        if self.pool:
            await self.pool.close()
            print("❌ БД отключена")

    # ===== СЕРВИСЫ =====
    async def add_service(self, service_name: str, phone: str, owner_id: int,
                          location: str = "", city: str = "") -> str:
        """Добавить новый сервис"""
        idservice = str(uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO services (idservice, service_name, service_number, owner_id,
                   location_service, city)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                idservice, service_name, phone, owner_id, location, city
            )
        return idservice

    async def get_service_by_owner(self, owner_id: int):
        """Получить сервис по owner_id"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT idservice FROM services WHERE owner_id = $1",
                owner_id
            )

    async def get_services_by_city(self, city: str) -> list:
        """Получить все сервисы по городу (регистронезависимый поиск)"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT idservice, service_name, service_number, location_service, city
                   FROM services
                   WHERE LOWER(city) = LOWER($1)
                   ORDER BY service_name""",
                city
            )

    async def get_all_cities(self) -> list:
        """Получить список всех городов с сервисами (уникальные, отсортированные)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT DISTINCT city FROM services
                   WHERE city IS NOT NULL AND city <> ''
                   ORDER BY city"""
            )
            return [row['city'] for row in rows]

    def generate_service_link(self, idservice: str) -> str:
        """Сгенерировать уникальную ссылку на сервис"""
        return f"https://t.me/{BOT_USERNAME}?start=SVC_{idservice}"

    def format_registration_message(self, service_name: str, phone: str,
                                    admin_name: str, idservice: str,
                                    location: str = "", city: str = "") -> str:
        """Форматировать сообщение об успешной регистрации сервиса"""
        link = self.generate_service_link(idservice)
        message = (
            f"✅ <b>Сервис успешно зарегистрирован!</b>\n\n"
            f"<b>Название:</b> {service_name}\n"
            f"<b>Телефон:</b> {phone}\n"
        )

        if city:
            message += f"<b>Город:</b> {city}\n"
        if location:
            message += f"<b>Адрес:</b> {location}\n"

        message += (
            f"<b>Администратор:</b> {admin_name}\n\n"
            f"<b>ID сервиса:</b> <code>{idservice}</code>\n"
            f"<b>Ваша ссылка на размещение</b>\n"
            f"<code>{link}</code>"
        )
        return message

    # ===== АДМИНИСТРАТОРЫ =====
    async def add_admin(self, idservice: str, idusertg: int):
        """Добавить администратора"""
        idadmin = str(uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO admins (idadmins, idservice, idusertg)
                   VALUES ($1, $2, $3)""",
                idadmin, idservice, idusertg
            )
        return idadmin

    async def get_admin_services(self, admin_id: int) -> list:
        """Получить все сервисы админа"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT s.idservice, s.service_name, s.service_number,
                          s.location_service, s.city
                   FROM services s
                   JOIN admins a ON s.idservice = a.idservice
                   WHERE a.idusertg = $1""",
                admin_id
            )

    async def get_admins_by_service(self, service_id: str) -> list:
        """Получить всех админов сервиса по service_id"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT a.idadmins, a.idservice, a.idusertg
                   FROM admins a
                   WHERE a.idservice = $1""",
                service_id
            )

    # ===== ЗАЯВКИ =====
    async def add_request(self, idservice: str, client_name: str, phone: str,
                        brand: str, model: str, plate: str, service_type: str,
                        urgency: str, comment: str, client_tg_id: int) -> str:
        """Добавить заявку"""
        idrequest = str(uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO requests (idrequests, idservice, client_name, phone, brand, model,
                plate, service_type, urgency, comment, idclienttg, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'new')""",
                idrequest, idservice, client_name, phone, brand, model, plate,
                service_type, urgency, comment, client_tg_id
            )
        return idrequest

    async def get_request(self, idrequest: str):
        """Получить заявку"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM requests WHERE idrequests = $1",
                idrequest
            )

    async def update_request_status(self, idrequest: str, status: str):
        """Обновить статус заявки"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE requests SET status = $1 WHERE idrequests = $2",
                status, idrequest
            )

    async def get_service_requests(self, idservice: str) -> list:
        """Получить все заявки по сервису"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM requests WHERE idservice = $1 ORDER BY createdate DESC",
                idservice
            )

db = Database()