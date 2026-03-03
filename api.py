from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from database import db
import asyncio

app = FastAPI()

# Разрешаем CORS (отредактируйте origin под свой хост)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <- в продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.close()

@app.get("/api/services")
async def services_by_city(city: str = Query(..., min_length=1)):
    """Возвращает список сервисов по городу. Формат ответа:
       [{ "idservice": "...", "service_name": "...", "service_number": "...", "location_service": "...", "city": "..." }, ...]
    """
    try:
        services = await db.get_services_by_city(city)
        # Преобразуем в список словарей (asyncpg Record -> dict)
        result = [dict(s) for s in services] if services else []
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)