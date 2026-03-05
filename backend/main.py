"""
Wealth Management Platform — FastAPI Application
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.database import engine, Base
from db.seed import seed_data
from routers import onboarding, portfolio, rm_copilot, voice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed data on startup."""
    logger.info("Starting Wealth Management Platform backend...")
    Base.metadata.create_all(bind=engine)
    try:
        seed_data()
    except Exception:
        logger.exception("Seed data failed — database may not be available yet")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Wealth Management Platform API",
    description="AI-powered wealth management platform with Gemini integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(onboarding.router)
app.include_router(portfolio.router)
app.include_router(rm_copilot.router)
app.include_router(voice.router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Wealth Management Platform API",
        "version": "1.0.0",
        "health": "/health",
        "docs": "/docs",
    }
