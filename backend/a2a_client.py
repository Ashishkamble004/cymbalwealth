"""A2A Client — calls remote A2A agents from GCP.

Supports two routing modes:
- Direct: calls AWS API Gateway endpoints (default, for now)
- Agent Gateway: routes through GCP Agent Gateway (when enabled)

Config via environment variables:
- A2A_CREDIT_ENDPOINT: Credit Intelligence agent URL
- A2A_REGULATORY_ENDPOINT: Regulatory Reporting agent URL
- A2A_GATEWAY_ENABLED: "true" to route via Agent Gateway (default: "false")
- A2A_GATEWAY_URL: Agent Gateway base URL (when enabled)
- A2A_AUTH_TOKEN: Bearer token for AWS API Gateway auth (direct mode)
"""

import json
import logging
import os
import uuid

import requests

logger = logging.getLogger(__name__)


class A2AError(Exception):
    pass


def get_config() -> dict:
    return {
        "credit_endpoint": os.environ.get("A2A_CREDIT_ENDPOINT", ""),
        "regulatory_endpoint": os.environ.get("A2A_REGULATORY_ENDPOINT", ""),
        "gateway_enabled": os.environ.get("A2A_GATEWAY_ENABLED", "false").lower() == "true",
        "gateway_url": os.environ.get("A2A_GATEWAY_URL", ""),
        "auth_token": os.environ.get("A2A_AUTH_TOKEN", ""),
    }


def call_a2a_agent(endpoint_url: str, user_message: str, auth_token: str = "") -> str:
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": user_message}],
                "messageId": str(uuid.uuid4()),
            }
        },
    }

    try:
        resp = requests.post(endpoint_url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise A2AError(f"A2A request failed: {exc}") from exc

    try:
        body = resp.json()
    except ValueError as exc:
        raise A2AError(f"Invalid JSON response: {resp.text[:200]}") from exc

    if "error" in body:
        err = body["error"]
        raise A2AError(f"A2A error {err.get('code')}: {err.get('message')}")

    try:
        return body["result"]["artifacts"][0]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise A2AError(f"Unexpected response structure: {json.dumps(body)[:300]}") from exc


def call_credit_intelligence(query: str) -> str:
    config = get_config()
    if config["gateway_enabled"]:
        endpoint = f"{config['gateway_url']}/credit-intelligence"
        return call_a2a_agent(endpoint, query)
    endpoint = config["credit_endpoint"]
    if not endpoint:
        raise A2AError("A2A_CREDIT_ENDPOINT not configured")
    return call_a2a_agent(endpoint, query, auth_token=config["auth_token"])


def call_regulatory_reporting(query: str) -> str:
    config = get_config()
    if config["gateway_enabled"]:
        endpoint = f"{config['gateway_url']}/regulatory-reporting"
        return call_a2a_agent(endpoint, query)
    endpoint = config["regulatory_endpoint"]
    if not endpoint:
        raise A2AError("A2A_REGULATORY_ENDPOINT not configured")
    return call_a2a_agent(endpoint, query, auth_token=config["auth_token"])


def fetch_agent_card(endpoint_url: str) -> dict:
    url = f"{endpoint_url.rstrip('/')}/.well-known/agent-card.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()
