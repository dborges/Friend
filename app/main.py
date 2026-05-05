import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.database import init_db
from app.scheduler import start_scheduler
from app.dashboard.routes import router as dashboard_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    init_db()
    scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(title="Friend", lifespan=lifespan)
app.include_router(dashboard_router, prefix="/dashboard")


@app.get("/")
async def root():
    return RedirectResponse("/dashboard")
