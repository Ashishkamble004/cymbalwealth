"""
Voice Router — WebSocket endpoint for Gemini Live voice interaction
"""

import json
import logging
import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from models.client import Client
from services.gemini_service import build_voice_system_prompt
from services.portfolio_service import get_portfolio_summary
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket, client_id: int = Query(...)):
    """Bidirectional WebSocket for Gemini Live voice interaction."""
    await websocket.accept()

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            await websocket.send_json({"error": "Client not found"})
            await websocket.close()
            return

        summary = get_portfolio_summary(client)
        goals_summary = "; ".join(
            f"{g['name']} (₹{g['target_amount']:,.0f} by {g['target_year']})"
            for g in summary["goals"]
        )
        aum_crores = round(client.aum / 1e7, 2) if client.aum else 0

        system_prompt = build_voice_system_prompt(
            client_name=client.name,
            segment=client.segment or "",
            risk_profile=client.risk_profile or "",
            aum=aum_crores,
            return_pct=summary["total_return_pct"],
            goals_summary=goals_summary,
        )

        transcript = []
        session_start = datetime.utcnow()

        await websocket.send_json({
            "type": "session_start",
            "client_name": client.name,
            "system_prompt": system_prompt,
            "model": settings.GEMINI_VOICE_MODEL,
        })

        # Main message loop
        retry_count = 0
        while True:
            try:
                data = await websocket.receive()

                if data.get("type") == "websocket.disconnect":
                    break

                if "text" in data:
                    msg = json.loads(data["text"])

                    if msg.get("type") == "end_session":
                        break

                    if msg.get("type") == "transcript":
                        transcript.append({
                            "role": msg.get("role", "user"),
                            "text": msg.get("text", ""),
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        await websocket.send_json({
                            "type": "transcript_ack",
                            "role": msg.get("role"),
                        })

                    if msg.get("type") == "audio_chunk":
                        # In production, this would forward PCM audio to Gemini Live API
                        # For the prototype, acknowledge receipt
                        await websocket.send_json({
                            "type": "audio_ack",
                            "status": "received",
                        })

                elif "bytes" in data:
                    # Binary audio data — would be forwarded to Gemini Live
                    await websocket.send_json({
                        "type": "audio_ack",
                        "status": "received",
                    })

                retry_count = 0  # Reset on successful message

            except WebSocketDisconnect:
                break
            except Exception as e:
                retry_count += 1
                logger.exception(f"Voice WebSocket error (attempt {retry_count})")
                if retry_count >= 2:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Connection failed after retry. Please reconnect.",
                    })
                    break
                await websocket.send_json({
                    "type": "error",
                    "message": "Temporary issue. Retrying...",
                })
                await asyncio.sleep(1)

        # Save transcript
        session_end = datetime.utcnow()
        session_data = {
            "client_id": client.id,
            "client_name": client.name,
            "session_start": session_start.isoformat(),
            "session_end": session_end.isoformat(),
            "duration_seconds": (session_end - session_start).total_seconds(),
            "transcript": transcript,
        }

        await websocket.send_json({
            "type": "session_end",
            "duration_seconds": session_data["duration_seconds"],
            "transcript_count": len(transcript),
        })

    except WebSocketDisconnect:
        logger.info(f"Voice session disconnected for client {client_id}")
    except Exception:
        logger.exception("Voice stream error")
    finally:
        db.close()
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/health")
async def voice_health():
    """Voice service health check."""
    return {"status": "ok", "model": settings.GEMINI_VOICE_MODEL}
