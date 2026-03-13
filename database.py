import asyncpg
from config import PG_USER, PG_PASSWORD, PG_HOST, PG_PORT, PG_DB, BOT_USERNAME
from uuid import uuid4

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=PG_USER, password=PG_PASSWORD, database=PG_DB,
            host=PG_HOST, port=PG_PORT, min_size=5, max_size=20
        )
        print("✅ БД подключена")

    async def close(self):
        if self.pool:
            await self.pool.close()
            print("❌ БД отключена")

    # ===== СЕРВИСЫ =====
    async def add_service(self, service_name: str, phone: str, owner_id: int,
                          location: str = "", city: str = "") -> str:
        idservice = str(uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO services (idservice, service_name, service_number, owner_id,
                   location_service, city) VALUES ($1, $2, $3, $4, $5, $6)""",
                idservice, service_name.strip(), phone.strip(),
                owner_id, location.strip(), city.strip()
            )
        return idservice

    async def get_service_by_id(self, idservice: str):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """SELECT idservice, service_name, service_number,
                          location_service, city, owner_id
                   FROM services WHERE idservice = $1""",
                idservice
            )

    async def get_owned_services(self, owner_id: int) -> list:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT idservice, service_name, service_number, location_service, city
                   FROM services WHERE owner_id = $1 ORDER BY service_name""",
                owner_id
            )

    def generate_service_link(self, idservice: str) -> str:
        return f"https://t.me/{BOT_USERNAME.strip()}?start=SVC_{idservice}"

    def format_registration_message(self, service_name: str, phone: str,
                                    admin_name: str, idservice: str,
                                    city: str = "", location: str = "") -> str:
        link = self.generate_service_link(idservice)
        msg = (
            f"✅ <b>Сервис успешно зарегистрирован!</b>\n\n"
            f"<b>Название:</b> {service_name}\n"
            f"<b>Телефон:</b> {phone}\n"
        )
        if city:     msg += f"<b>Город:</b> {city}\n"
        if location: msg += f"<b>Адрес:</b> {location}\n"
        msg += (
            f"<b>Администратор:</b> {admin_name}\n\n"
            f"<b>ID сервиса:</b> <code>{idservice}</code>\n"
            f"<b>Ссылка на размещение:</b>\n<code>{link}</code>"
        )
        return msg

    # ===== АДМИНИСТРАТОРЫ =====
    async def add_admin(self, idservice: str, idusertg: int):
        """Upsert: восстанавливает запись если была удалена"""
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT idadmins FROM admins WHERE idservice = $1 AND idusertg = $2",
                idservice, idusertg
            )
            if existing:
                await conn.execute(
                    "UPDATE admins SET idrecstatus = 0 WHERE idservice = $1 AND idusertg = $2",
                    idservice, idusertg
                )
                return existing['idadmins']
            else:
                idadmin = str(uuid4())
                await conn.execute(
                    """INSERT INTO admins (idadmins, idservice, idusertg, idrecstatus)
                       VALUES ($1, $2, $3, 0)""",
                    idadmin, idservice, idusertg
                )
                return idadmin

    async def remove_admin(self, idservice: str, idusertg: int):
        """Мягкое удаление"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE admins SET idrecstatus = -1 WHERE idservice = $1 AND idusertg = $2",
                idservice, idusertg
            )

    async def get_admin_services(self, admin_id: int) -> list:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT s.idservice, s.service_name, s.service_number, s.location_service
                   FROM services s
                   JOIN admins a ON s.idservice = a.idservice
                   WHERE a.idusertg = $1 AND a.idrecstatus = 0""",
                admin_id
            )

    async def get_admins_by_service(self, service_id: str) -> list:
        """Активные администраторы — возвращает idusertg и first_name если сохранён"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT a.idadmins, a.idservice, a.idusertg, a.admin_name
                   FROM admins a
                   WHERE a.idservice = $1 AND a.idrecstatus = 0
                   ORDER BY a.admin_name NULLS LAST""",
                service_id
            )

    async def set_admin_name(self, idservice: str, idusertg: int, name: str):
        """Сохранить имя администратора при добавлении"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE admins SET admin_name = $1 WHERE idservice = $2 AND idusertg = $3",
                name, idservice, idusertg
            )

    # ===== ЗАЯВКИ =====
    async def add_request(self, idservice: str, client_name: str, phone: str,
                          brand: str, model: str, plate: str, service_type: str,
                          urgency: str, comment: str, client_tg_id: int) -> str:
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
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM requests WHERE idrequests = $1", idrequest
            )

    async def get_user_requests(self, client_tg_id: int, limit: int = 10) -> list:
        """Последние N заявок пользователя"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT r.idrequests, r.service_type, r.status, r.client_name,
                          r.brand, r.model, r.createdate, s.service_name
                   FROM requests r
                   LEFT JOIN services s ON r.idservice = s.idservice
                   WHERE r.idclienttg = $1
                   ORDER BY r.createdate DESC LIMIT $2""",
                client_tg_id, limit
            )

    async def update_request_status(self, idrequest: str, status: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE requests SET status = $1 WHERE idrequests = $2", status, idrequest
            )

    async def get_service_requests(self, idservice: str, limit: int = 10) -> list:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT * FROM requests WHERE idservice = $1
                   ORDER BY createdate DESC LIMIT $2""",
                idservice, limit
            )

    async def get_services_by_city(self, city: str) -> list:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """SELECT idservice, service_name, service_number, location_service, city
                   FROM services
                   WHERE LOWER(TRIM(city)) = LOWER(TRIM($1))
                   ORDER BY service_name""",
                city.strip()
            )

db = Database()