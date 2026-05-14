"""
Shared A2A (Agent-to-Agent) protocol adapter for AWS Lambda agents.

This module is packaged as a Lambda Layer so both the Credit Intelligence
and Regulatory Reporting agents can import it directly:

    from a2a_adapter import route_request

It implements the JSON-RPC 2.0 subset defined by the A2A spec:
  - GET  /.well-known/agent-card.json  -> agent card
  - GET  /ping                         -> health check
  - POST /                             -> message/send (JSON-RPC 2.0)
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Callable


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def build_api_response(status_code: int, body: dict) -> dict:
    """Build an API Gateway HTTP API (v2) Lambda proxy response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body),
    }


# ---------------------------------------------------------------------------
# A2A endpoint handlers
# ---------------------------------------------------------------------------

def handle_agent_card(agent_card: dict) -> dict:
    """Return 200 response containing the agent card JSON."""
    return build_api_response(200, agent_card)


def handle_ping() -> dict:
    """Return 200 health-check response with an ISO-8601 timestamp."""
    return build_api_response(200, {
        "status": "Healthy",
        "time_of_last_update": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 request parsing
# ---------------------------------------------------------------------------

def parse_a2a_request(event: dict) -> dict | None:
    """Parse a JSON-RPC 2.0 body from an API Gateway HTTP API (v2) event.

    Handles the ``isBase64Encoded`` flag transparently.  Returns the parsed
    dict on success or *None* if the body is missing / malformed.
    """
    raw_body = event.get("body")
    if raw_body is None:
        return None

    if event.get("isBase64Encoded", False):
        try:
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        except Exception:
            return None

    try:
        return json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return None


def extract_user_message(rpc_body: dict) -> str | None:
    """Extract the first text part from a ``message/send`` JSON-RPC request.

    Expected structure (A2A spec)::

        {
          "jsonrpc": "2.0",
          "method": "message/send",
          "id": "...",
          "params": {
            "message": {
              "parts": [
                {"kind": "text", "text": "user question here"}
              ]
            }
          }
        }

    Returns the text string or *None* if the structure doesn't match.
    """
    try:
        params = rpc_body.get("params", {})
        message = params.get("message", {})
        parts = message.get("parts", [])
        for part in parts:
            if part.get("kind") == "text":
                return part.get("text")
    except (AttributeError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 response builders
# ---------------------------------------------------------------------------

def build_a2a_response(rpc_id: str, agent_text: str, task_id: str | None = None) -> dict:
    """Build a JSON-RPC 2.0 success response wrapping agent output as an artifact.

    Returns the full API Gateway response dict (status 200).

    Response payload follows the A2A spec::

        {
          "jsonrpc": "2.0",
          "id": "<rpc_id>",
          "result": {
            "id": "<task_id>",
            "status": {"state": "completed"},
            "artifacts": [
              {
                "parts": [{"kind": "text", "text": "<agent_text>"}],
                "index": 0
              }
            ]
          }
        }
    """
    if task_id is None:
        task_id = str(uuid.uuid4())

    rpc_response = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [
                {
                    "parts": [{"kind": "text", "text": agent_text}],
                    "index": 0,
                }
            ],
        },
    }
    return build_api_response(200, rpc_response)


def build_a2a_error(rpc_id: str, code: int, message: str) -> dict:
    """Build a JSON-RPC 2.0 error response.

    Returns the full API Gateway response dict (status 200 — per JSON-RPC,
    transport status is always 200; errors are conveyed inside the envelope).
    """
    rpc_error = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
    return build_api_response(200, rpc_error)


# ---------------------------------------------------------------------------
# Top-level router
# ---------------------------------------------------------------------------

def route_request(
    event: dict,
    agent_card: dict,
    handle_message_fn: Callable[[str], str],
) -> dict:
    """Route an incoming API Gateway HTTP API (v2) event to the right handler.

    Dispatch logic:

    * **GET  /.well-known/agent-card.json** -> ``handle_agent_card``
    * **GET  /ping**                        -> ``handle_ping``
    * **POST /**                            -> parse JSON-RPC, call *handle_message_fn*
    * **OPTIONS** (any path)                -> 204 preflight
    * Everything else                       -> 404

    Parameters
    ----------
    event : dict
        The Lambda proxy-integration event from API Gateway HTTP API v2.
    agent_card : dict
        The agent card dict to serve.
    handle_message_fn : callable
        ``fn(user_text: str) -> str`` — the agent-specific logic.
    """
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
    raw_path = event.get("rawPath", "/")

    # --- CORS preflight ---
    if http_method == "OPTIONS":
        return build_api_response(204, {})

    # --- Agent card ---
    if http_method == "GET" and raw_path.rstrip("/") == "/.well-known/agent-card.json":
        return handle_agent_card(agent_card)

    # --- Health check ---
    if http_method == "GET" and raw_path.rstrip("/") == "/ping":
        return handle_ping()

    # --- A2A message/send ---
    if http_method == "POST" and raw_path.rstrip("/") in ("", "/"):
        rpc_body = parse_a2a_request(event)
        if rpc_body is None:
            return build_a2a_error("unknown", -32700, "Parse error: invalid JSON body")

        rpc_id = rpc_body.get("id", "unknown")
        method = rpc_body.get("method")

        if method != "message/send":
            return build_a2a_error(rpc_id, -32601, f"Method not found: {method}")

        user_text = extract_user_message(rpc_body)
        if user_text is None:
            return build_a2a_error(rpc_id, -32602, "No text part found in message")

        try:
            agent_response = handle_message_fn(user_text)
        except Exception as exc:
            return build_a2a_error(rpc_id, -32000, f"Agent error: {exc}")

        return build_a2a_response(rpc_id, agent_response)

    # --- Fallback ---
    return build_api_response(404, {"error": "Not found"})
