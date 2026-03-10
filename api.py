from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from database import db

app = FastAPI(title="AutoService API")

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
    try:
        services = await db.get_services_by_city(city)
        return [dict(s) for s in services] if services else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ НОВЫЙ ЭНДПОИНТ: получить название сервиса по ID
@app.get("/api/service/{service_id}")
async def get_service(service_id: str):
    try:
        service = await db.get_service_by_id(service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        return dict(service)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=True)