from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import create_database_tables
from backend.api.health import router as health_router
from backend.api.plans import router as plans_router
from backend.api.estimation import router as estimation_router
from backend.api.boq import router as boq_router
from backend.api.auth import router as auth_router
from backend.api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any missing database tables on startup.
    create_database_tables()
    yield


app = FastAPI(
    title="ZimBuild AI API",
    description=(
        "Backend API for automated bill of quantities "
        "and cost estimation for residential buildings "
        "in Zimbabwe."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# Allow the React/Vite frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://zimbuild-ai.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(plans_router)
app.include_router(estimation_router)
app.include_router(boq_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {
        "name": "ZimBuild AI API",
        "version": "1.0.0",
        "status": "running",
    }
