from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS
from app.core.database import init_db  # async — creates MongoDB indexes
from app.core.logging import setup_logging
from app.middleware import CorrelationMiddleware
from app.routes import auth, reports

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
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reports.router)


@app.get("/api/health")
async def health():
    return {"message": "Perception AI backend is running"}
