"""
RM Copilot Router — Pre-call briefs and follow-up chat
"""

import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from models.client import Client
from models.transaction import Transaction, Interaction
from services.portfolio_service import get_portfolio_summary, format_client_json, format_portfolio_json
from services.gemini_service import generate_rm_brief, rm_followup_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rm/copilot", tags=["rm_copilot"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    client_id: int
    messages: list[ChatMessage]


@router.get("/brief/{client_id}")
async def get_brief(client_id: int, db: Session = Depends(get_db)):
    """Generate a pre-call brief for the RM."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    summary = get_portfolio_summary(client)
    client_json = format_client_json(client)
    portfolio_json = format_portfolio_json(summary)

    # Get recent interactions
    recent_interactions = (
        db.query(Interaction)
        .filter(Interaction.client_id == client_id)
        .order_by(Interaction.interaction_date.desc())
        .limit(3)
        .all()
    )
    interactions_data = [
        {
            "type": i.interaction_type,
            "summary": i.summary,
            "date": i.interaction_date.isoformat() if i.interaction_date else None,
        }
        for i in recent_interactions
    ]

    # Get large recent transactions (> 5 lakhs in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    large_txns = (
        db.query(Transaction)
        .filter(
            Transaction.client_id == client_id,
            Transaction.amount > 500000,
            Transaction.transaction_date >= thirty_days_ago.date(),
        )
        .all()
    )
    txn_data = [
        {
            "instrument": t.instrument_name,
            "type": t.transaction_type,
            "amount": t.amount,
            "date": str(t.transaction_date),
        }
        for t in large_txns
    ]

    interaction_history = json.dumps(
        {"recent_interactions": interactions_data, "large_recent_transactions": txn_data},
        indent=2,
    )

    brief = await generate_rm_brief(client_json, portfolio_json, interaction_history)
    return {"client_id": client_id, "brief": brief}


@router.post("/chat")
async def copilot_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Follow-up chat about a specific client."""
    client = db.query(Client).filter(Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Prepend client context to the conversation
    summary = get_portfolio_summary(client)
    context_msg = {
        "role": "user",
        "content": (
            f"Context: I'm the RM for {client.name} ({client.segment}, "
            f"{client.risk_profile} risk, AUM ₹{client.aum:,.0f}). "
            f"Portfolio return: {summary['total_return_pct']}%. "
            f"Answer questions about this client."
        ),
    }
    messages = [context_msg] + [m.model_dump() for m in request.messages]
    response = await rm_followup_chat(messages)
    return {"response": response}


@router.get("/clients-summary")
async def clients_summary(db: Session = Depends(get_db)):
    """Return a summary of all clients for the RM dashboard."""
    clients = db.query(Client).all()
    result = []
    for c in clients:
        summary = get_portfolio_summary(c)
        result.append({
            "id": c.id,
            "name": c.name,
            "segment": c.segment,
            "risk_profile": c.risk_profile,
            "aum": c.aum,
            "total_return_pct": summary["total_return_pct"],
            "goals_count": len(summary["goals"]),
            "holdings_count": len(summary["holdings"]),
        })
    return result
