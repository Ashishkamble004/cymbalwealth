"""
Portfolio Router — holdings, analytics, and AI commentary
"""

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.database import get_db
from models.client import Client
from services.portfolio_service import get_portfolio_summary, format_client_json, format_portfolio_json
from services.market_service import get_market_summary
from services.gemini_service import stream_portfolio_commentary
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Optional Redis caching
_redis = None
try:
    import redis as redis_lib
    if settings.REDIS_HOST:
        _redis = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        _redis.ping()
except Exception:
    _redis = None
    logger.info("Redis not available — commentary caching disabled")


@router.get("/{client_id}")
async def get_portfolio(client_id: int, db: Session = Depends(get_db)):
    """Return full portfolio summary for a client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return get_portfolio_summary(client)


@router.get("/{client_id}/commentary")
async def get_commentary(client_id: int, db: Session = Depends(get_db)):
    """Stream AI-generated portfolio commentary via SSE."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    today = date.today().isoformat()
    cache_key = f"commentary:{client_id}:{today}"

    # Check cache
    if _redis:
        try:
            cached = _redis.get(cache_key)
            if cached:
                async def cached_stream():
                    yield f"data: {cached}\n\n"
                    yield "data: [DONE]\n\n"
                return StreamingResponse(cached_stream(), media_type="text/event-stream")
        except Exception:
            pass

    summary = get_portfolio_summary(client)
    client_json = format_client_json(client)
    portfolio_json = format_portfolio_json(summary)
    market_summary = get_market_summary()

    async def event_stream():
        full_text = ""
        async for token in stream_portfolio_commentary(client_json, portfolio_json, market_summary):
            full_text += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"
        # Cache the final commentary
        if _redis:
            try:
                _redis.setex(cache_key, 86400, full_text)
            except Exception:
                pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")
