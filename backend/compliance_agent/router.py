"""Compliance Agent API router — mounted into the main backend.

Provides a REST endpoint for the demo portal to query regulatory data.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import compliance_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])

session_service = InMemorySessionService()
APP_NAME = "cymbal-compliance"

runner = Runner(
    agent=compliance_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


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
