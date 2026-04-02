"""Cymbal Wealth — Home Loan Service (Cloud Run).

Handles document uploads to GCS.
Verification is routed to Vertex AI Agent Engine (multi-agent orchestration).
"""

import logging
import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "general-ak"))
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_REGION", "us-central1"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from home_loan_api import router as home_loan_router

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

app = FastAPI(title="Cymbal Wealth — Home Loan Service", version="2.0.0")

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "https://cymbalwealth.ak-demos.com,https://homeloan-gateway-9t9witd8.uc.gateway.dev").split(",")
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
