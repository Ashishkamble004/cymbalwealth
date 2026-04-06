"""Compliance monitor — debounced Gemini analysis of call-centre conversation."""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a compliance monitor for a bank call center. "
    "Analyze the conversation and identify any compliance violations, "
    "particularly around credit card offers and financial product pushing."
)

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "speaker": {"type": "string", "enum": ["agent", "customer"]},
                    "text": {"type": "string"},
                },
                "required": ["id", "speaker", "text"],
            },
        },
        "alerts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                    "segment_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["title", "description", "severity", "segment_ids"],
            },
        },
    },
    "required": ["segments", "alerts"],
}

_DEBOUNCE_SECONDS = 3.0


class ComplianceMonitor:
    """Accumulates STT segments and runs debounced Gemini compliance analysis."""

    def __init__(self, client: genai.Client, llm_model: str):
        self._client = client
        self._llm_model = llm_model
        self._segments: list[str] = []
        self._last_analysis_time: float = 0.0
        self._seen_alerts: set[tuple[str, str]] = set()

    async def analyze(self, segment_text: str) -> dict[str, Any] | None:
        """Add a final transcript segment and run analysis if debounce window has passed."""
        self._segments.append(segment_text)

        now = time.monotonic()
        if now - self._last_analysis_time < _DEBOUNCE_SECONDS:
            return None

        self._last_analysis_time = now
        numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(self._segments))

        try:
            response = await self._client.aio.models.generate_content(
                model=self._llm_model,
                contents=numbered,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=_RESPONSE_SCHEMA,
                ),
            )
            raw = response.text or "{}"
            data: dict[str, Any] = json.loads(raw)
        except Exception as exc:
            logger.error("Compliance analysis failed: %s", exc)
            return None

        # Deduplicate alerts
        new_alerts = []
        for alert in data.get("alerts", []):
            key = (alert.get("title", ""), alert.get("description", ""))
            if key not in self._seen_alerts:
                self._seen_alerts.add(key)
                alert["id"] = str(uuid.uuid4())
                alert["timestamp"] = datetime.now(timezone.utc).isoformat()
                new_alerts.append(alert)

        return {
            "segments": data.get("segments", []),
            "alerts": new_alerts,
        }
