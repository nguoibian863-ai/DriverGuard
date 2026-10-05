from fastapi import FastAPI

from app.api import routes_health

app = FastAPI(title="DriverGuard API", version="0.1.0")
app.include_router(routes_health.router)
