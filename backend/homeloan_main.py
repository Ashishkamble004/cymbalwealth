"""Cymbal Wealth — Home Loan Service (Cloud Run).

Handles document uploads to GCS.
Verification is routed to Vertex AI Agent Engine (multi-agent orchestration).
"""

import asyncio
import logging
import os
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "general-ak"))
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_REGION", "us-central1"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from home_loan_api import router as home_loan_router, _pool

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm Agent Engine session pool on startup (non-blocking — runs in background)
    asyncio.create_task(_pool.warmup())
    yield


app = FastAPI(
    title="Cymbal Wealth — Home Loan Service",
    version="2.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "https://cymbalwealth.ak-demos.com").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home_loan_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "homeloan-backend", "mode": "agent-engine-proxy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
