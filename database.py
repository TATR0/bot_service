import asyncpg
from config import PG_USER, PG_PASSWORD, PG_HOST, PG_PORT, PG_DB
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
    async def add_service(self, service_name: str, phone: str, owner_id: int) -> str:
        """Добавить новый сервис"""
        idservice = str(uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO services (idservice, service_name, service_number, owner_id)
                   VALUES ($1, $2, $3, $4)""",
                idservice, service_name, phone, owner_id
            )
        return idservice

    async def get_service_by_owner(self, owner_id: int):
        """Получить сервис по owner_id"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT idservice FROM services WHERE owner_id = $1",
                owner_id
            )

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
                """SELECT s.idservice, s.service_name, s.service_number
                   FROM services s
                   JOIN admins a ON s.idservice = a.idservice
                   WHERE a.idusertg = $1""",
                admin_id
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
                VALUES ($1, null, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'new')""",# вернуть idservice
                idrequest, client_name, phone, brand, model, plate,
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