from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.middleware import CorrelationMiddleware
from app.routes import auth, reports, schedules

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Perception AI", lifespan=lifespan)

# Correlation ID middleware (outermost so it wraps everything)
app.add_middleware(CorrelationMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(schedules.router)


@app.get("/api/health")
async def health():
    return {"message": "Perception AI backend is running"}
