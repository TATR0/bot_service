"""
Небольшой HTTP-сервер для обслуживания index.html и API-эндпоинтов.
Запускается вместе с ботом через asyncio.

Маршруты:
  GET  /               → index.html
  GET  /api/cities     → {"cities": ["Москва", "СПб", ...]}
  GET  /api/services   → {"services": [{id, name, phone, address}, ...]}
                         ?city=Москва
"""

from aiohttp import web
import pathlib
import logging
from database import db

logger = logging.getLogger(__name__)

HTML_PATH = pathlib.Path(__file__).parent / "index.html"


async def handle_index(request: web.Request) -> web.Response:
    """Отдаём index.html"""
    return web.FileResponse(HTML_PATH)


async def handle_cities(request: web.Request) -> web.Response:
    """Список городов со зарегистрированными сервисами"""
    try:
        cities = await db.get_all_cities()
        return web.json_response({"cities": cities})
    except Exception as e:
        logger.error(f"Ошибка /api/cities: {e}", exc_info=True)
        return web.json_response({"cities": [], "error": str(e)}, status=500)


async def handle_services(request: web.Request) -> web.Response:
    """Список сервисов по городу"""
    city = request.rel_url.query.get("city", "").strip()
    if not city:
        return web.json_response({"services": [], "error": "city param required"}, status=400)

    try:
        rows = await db.get_services_by_city(city)
        services = [
            {
                "id":      str(row["idservice"]),
                "name":    row["service_name"],
                "phone":   row["service_number"] or "",
                "address": row["location_service"] or "",
                "city":    row["city"] or "",
            }
            for row in rows
        ]
        return web.json_response({"services": services})
    except Exception as e:
        logger.error(f"Ошибка /api/services: {e}", exc_info=True)
        return web.json_response({"services": [], "error": str(e)}, status=500)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/cities", handle_cities)
    app.router.add_get("/api/services", handle_services)
    # Статика рядом с index.html (если нужна)
    static_dir = pathlib.Path(__file__).parent / "static"
    if static_dir.exists():
        app.router.add_static("/static", static_dir)
    return app