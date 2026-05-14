"""Compliance Agent API router — mounted into the main backend.

Provides a REST endpoint for the demo portal to query regulatory data.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from google.genai import types

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])

APP_NAME = "cymbal-compliance"

AGENT_ENGINE_ID = os.environ.get("COMPLIANCE_AGENT_ENGINE_ID", "")

try:
    from google.adk.runners import Runner
    from google.adk.memory import InMemoryMemoryService
    from .agent import compliance_agent

    if AGENT_ENGINE_ID:
        # Production: agent deployed to Agent Engine — use Vertex AI session service
        from google.adk.sessions import VertexAiSessionService
        session_service = VertexAiSessionService(project="general-ak", location="us-central1")
        app_name = AGENT_ENGINE_ID
        logger.info(f"[Compliance] Using VertexAiSessionService with engine {AGENT_ENGINE_ID}")
    else:
        # Dev/staging: use in-memory session service until Agent Engine deploy
        from google.adk.sessions import InMemorySessionService
        session_service = InMemorySessionService()
        app_name = APP_NAME
        logger.info("[Compliance] Using InMemorySessionService (no COMPLIANCE_AGENT_ENGINE_ID set)")

    memory_service = InMemoryMemoryService()
    runner = Runner(agent=compliance_agent, app_name=app_name, session_service=session_service)
    _adk_available = True
except (ImportError, Exception) as e:
    logger.warning(f"Compliance router degraded: {e}")
    _adk_available = False
    runner = None
    session_service = None
    memory_service = None


class ComplianceQuery(BaseModel):
    query: str
    session_id: str | None = None


class ComplianceResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    a2a_routed: bool
    gateway_enabled: bool


@router.post("/query", response_model=ComplianceResponse)
async def query_compliance(request: ComplianceQuery):
    """Query regulatory compliance data via the Compliance agent."""
    from fastapi import HTTPException
    if not _adk_available:
        raise HTTPException(status_code=503, detail="Compliance agent unavailable: google-adk not installed")

    from a2a_client import get_config

    config = get_config()
    user_id = "demo-user"
    session_id = request.session_id or str(uuid.uuid4())

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=request.query)],
        ),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    # Ingest the completed session into Vertex AI Memory Bank so that user
    # context (regulatory queries, prior decisions) persists across sessions.
    # Memory Bank ingestion (no-op with InMemoryMemoryService until Agent Engine deployed)
    try:
        if hasattr(memory_service, 'add_session_to_memory'):
            session_obj = await session_service.get_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )
            await memory_service.add_session_to_memory(session=session_obj)
    except Exception as e:
        logger.warning(f"Memory Bank ingestion skipped: {e}")

    return ComplianceResponse(
        response=response_text or "No response generated.",
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        a2a_routed=bool(config.get("regulatory_endpoint")),
        gateway_enabled=config.get("gateway_enabled", False),
    )


@router.get("/health")
async def compliance_health():
    from a2a_client import get_config

    config = get_config()
    return {
        "status": "ok",
        "service": "compliance-agent",
        "a2a_endpoint_configured": bool(config.get("regulatory_endpoint")),
        "gateway_enabled": config.get("gateway_enabled", False),
    }
