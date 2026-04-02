from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.core.logging import setup_logging
from app.middleware import CorrelationMiddleware
from app.routes import auth, reports, usage

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Brand Intelligence", lifespan=lifespan)

# Correlation ID middleware (outermost so it wraps everything)
app.add_middleware(CorrelationMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(usage.router)


@app.get("/api/health")
async def health():
    return {"message": "Brand Intelligence backend is running"}
