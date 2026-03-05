"""
Portfolio Service — calculations, analytics, and data formatting
"""

import json
from datetime import date
from sqlalchemy.orm import Session

from models.client import Client, Holding, Goal


def get_portfolio_summary(client: Client) -> dict:
    """Compute a full portfolio summary for a client."""
    holdings_data = []
    total_invested = 0.0
    total_current = 0.0

    for h in client.holdings:
        invested = h.quantity * h.purchase_price
        current = h.quantity * h.current_price
        pnl = current - invested
        ret = (pnl / invested * 100) if invested > 0 else 0.0
        total_invested += invested
        total_current += current
        holdings_data.append({
            "instrument_name": h.instrument_name,
            "instrument_type": h.instrument_type,
            "quantity": h.quantity,
            "purchase_price": h.purchase_price,
            "current_price": h.current_price,
            "invested_value": round(invested, 2),
            "current_value": round(current, 2),
            "unrealized_pnl": round(pnl, 2),
            "return_pct": round(ret, 2),
        })

    total_pnl = total_current - total_invested
    total_return_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    # Allocation breakdown by instrument type
    allocation = {}
    for h in holdings_data:
        t = h["instrument_type"] or "Other"
        allocation[t] = allocation.get(t, 0) + h["current_value"]
    allocation_pct = {k: round(v / total_current * 100, 2) if total_current > 0 else 0 for k, v in allocation.items()}

    # Goals
    goals_data = []
    for g in client.goals:
        progress = min((g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0, 100)
        goals_data.append({
            "name": g.name,
            "target_amount": g.target_amount,
            "current_amount": g.current_amount,
            "target_year": g.target_year,
            "progress_pct": round(progress, 2),
        })

    # Sort holdings by current value descending
    holdings_data.sort(key=lambda x: x["current_value"], reverse=True)

    return {
        "client_id": client.id,
        "client_name": client.name,
        "segment": client.segment,
        "risk_profile": client.risk_profile,
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "total_unrealized_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "holdings": holdings_data,
        "allocation": allocation_pct,
        "goals": goals_data,
    }


def format_client_json(client: Client) -> str:
    """Format client data as JSON string for Gemini prompts."""
    goals_summary = "; ".join(
        f"{g.name} (₹{g.target_amount:,.0f} by {g.target_year})" for g in client.goals
    )
    return json.dumps({
        "name": client.name,
        "segment": client.segment,
        "risk_profile": client.risk_profile,
        "aum_crores": round(client.aum / 1e7, 2) if client.aum else 0,
        "kyc_status": client.kyc_status,
        "goals": goals_summary,
    }, indent=2)


def format_portfolio_json(summary: dict) -> str:
    """Format portfolio summary as JSON string for Gemini prompts."""
    return json.dumps({
        "total_invested": summary["total_invested"],
        "total_current_value": summary["total_current_value"],
        "total_return_pct": summary["total_return_pct"],
        "allocation": summary["allocation"],
        "top_holdings": summary["holdings"][:5],
        "goals": summary["goals"],
    }, indent=2)
