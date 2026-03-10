from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from database import db  # использует config.py для чтения переменных окружения

app = FastAPI(title="AutoService API")

# Разрешаем CORS только для GitHub Pages (укажите свой origin в Railway env GHPAGES_ORIGIN)
GHPAGES_ORIGIN = os.getenv("GHPAGES_ORIGIN", "https://mometsrofl.github.io")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[GHPAGES_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
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
    """
    Возвращает список сервисов по городу (case-insensitive).
    Формат ответа: [{ "idservice": "...", "service_name": "...", "service_number": "...", "location_service": "...", "city": "..." }, ...]
    """
    try:
        services = await db.get_services_by_city(city)
        result = [dict(s) for s in services] if services else []
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
    