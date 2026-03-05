"""
Onboarding Router — KYC document analysis & risk profiling
"""

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import google.generativeai as genai

from db.database import get_db
from models.client import Client
from services.gemini_service import analyze_kyc_documents, generate_risk_questionnaire

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class RiskScoreRequest(BaseModel):
    client_id: int
    answers: list[int]  # list of scores (1, 2, or 3)


class RiskScoreResponse(BaseModel):
    risk_profile: str
    total_score: int


@router.post("/analyze-docs")
async def analyze_docs(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Accept multipart KYC document upload and analyze with Gemini."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one document is required")

    # Build file parts for Gemini multimodal
    file_parts = []
    for f in files:
        content = await f.read()
        mime = f.content_type or "application/octet-stream"
        file_parts.append({"mime_type": mime, "data": content})

    # Analyze with Gemini
    result = await analyze_kyc_documents(file_parts)

    # Calculate age for questionnaire
    age = 35  # default
    if result.get("dob"):
        try:
            dob = date.fromisoformat(result["dob"])
            age = (date.today() - dob).days // 365
        except (ValueError, TypeError):
            pass

    income = result.get("annual_income_estimate", 0)
    if income > 5000000:
        income_band = "above 50 lakhs"
    elif income > 1500000:
        income_band = "15-50 lakhs"
    else:
        income_band = "below 15 lakhs"

    questionnaire = generate_risk_questionnaire(age, income_band)

    return {
        "kyc_data": result,
        "risk_questionnaire": questionnaire,
    }


@router.post("/risk-score", response_model=RiskScoreResponse)
async def score_risk_profile(
    request: RiskScoreRequest,
    db: Session = Depends(get_db),
):
    """Score risk profiling answers and update client profile."""
    client = db.query(Client).filter(Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    total = sum(request.answers)
    count = len(request.answers) if request.answers else 1
    avg = total / count

    if avg <= 1.5:
        profile = "Conservative"
    elif avg <= 2.3:
        profile = "Moderate"
    else:
        profile = "Aggressive"

    client.risk_profile = profile
    client.kyc_status = "verified"
    db.commit()

    return RiskScoreResponse(risk_profile=profile, total_score=total)


@router.get("/clients")
async def list_clients(db: Session = Depends(get_db)):
    """List all clients."""
    clients = db.query(Client).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "segment": c.segment,
            "risk_profile": c.risk_profile,
            "kyc_status": c.kyc_status,
            "aum": c.aum,
        }
        for c in clients
    ]


@router.get("/clients/{client_id}")
async def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a single client by ID."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {
        "id": client.id,
        "name": client.name,
        "email": client.email,
        "phone": client.phone,
        "dob": str(client.dob) if client.dob else None,
        "pan": client.pan,
        "aadhaar_last4": client.aadhaar_last4,
        "address": client.address,
        "segment": client.segment,
        "risk_profile": client.risk_profile,
        "kyc_status": client.kyc_status,
        "annual_income": client.annual_income,
        "aum": client.aum,
        "rm_name": client.rm_name,
    }
