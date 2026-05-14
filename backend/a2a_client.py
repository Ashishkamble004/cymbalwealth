"""A2A Client — calls remote A2A agents from GCP.

Supports two routing modes:
- Direct: calls AWS Bedrock AgentCore Runtime via boto3 SigV4 (default)
- Agent Gateway: routes through GCP Agent Gateway (when enabled)

Config via environment variables:
- A2A_CREDIT_ARN: Credit Intelligence AgentCore Runtime ARN
- A2A_REGULATORY_ARN: Regulatory Reporting AgentCore Runtime ARN
- A2A_GATEWAY_ENABLED: "true" to route via GCP Agent Gateway (default: "false")
- A2A_GATEWAY_URL: Agent Gateway base URL (when enabled)
- AWS_REGION: AWS region for AgentCore (default: "us-east-1")
- AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN: AWS credentials
"""

import json
import logging
import os
import uuid

logger = logging.getLogger(__name__)

CREDIT_ARN = os.environ.get(
    "A2A_CREDIT_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:453809273083:runtime/cymbal_credit_intelligence-26fPFAF9gS",
)
REGULATORY_ARN = os.environ.get(
    "A2A_REGULATORY_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:453809273083:runtime/cymbal_regulatory_reporting-vA2VQ08PxI",
)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


class A2AError(Exception):
    pass


def get_config() -> dict:
    return {
        "credit_arn": CREDIT_ARN,
        "regulatory_arn": REGULATORY_ARN,
        "gateway_enabled": os.environ.get("A2A_GATEWAY_ENABLED", "false").lower() == "true",
        "gateway_url": os.environ.get("A2A_GATEWAY_URL", ""),
        "aws_region": AWS_REGION,
    }


def _call_agentcore(runtime_arn: str, user_message: str) -> str:
    """Invoke an AgentCore Runtime agent using boto3 (SigV4 auth, no HTTP URLs needed)."""
    import boto3

    client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
    session_id = str(uuid.uuid4())  # 36 chars — satisfies AgentCore min 33

    payload = json.dumps({
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
    }).encode()

    try:
        resp = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier="DEFAULT",
        )
    except Exception as exc:
        raise A2AError(f"AgentCore invocation failed: {exc}") from exc

    try:
        body = json.loads(resp["response"].read().decode("utf-8"))
    except (KeyError, ValueError) as exc:
        raise A2AError(f"Invalid AgentCore response: {exc}") from exc

    if "error" in body:
        err = body["error"]
        raise A2AError(f"A2A error {err.get('code')}: {err.get('message')}")

    try:
        return body["result"]["artifacts"][0]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise A2AError(f"Unexpected response structure: {json.dumps(body)[:300]}") from exc


def _call_via_gateway(gateway_url: str, path: str, user_message: str) -> str:
    """Route through GCP Agent Gateway when enabled."""
    import requests

    endpoint = f"{gateway_url.rstrip('/')}/{path}"
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
        resp = requests.post(endpoint, json=payload, timeout=90)
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:
        raise A2AError(f"Agent Gateway call failed: {exc}") from exc

    if "error" in body:
        raise A2AError(f"A2A error: {body['error']}")

    try:
        return body["result"]["artifacts"][0]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise A2AError(f"Unexpected response: {json.dumps(body)[:300]}") from exc


def call_credit_intelligence(query: str) -> str:
    config = get_config()
    if config["gateway_enabled"]:
        return _call_via_gateway(config["gateway_url"], "credit-intelligence", query)
    return _call_agentcore(config["credit_arn"], query)


def call_regulatory_reporting(query: str) -> str:
    config = get_config()
    if config["gateway_enabled"]:
        return _call_via_gateway(config["gateway_url"], "regulatory-reporting", query)
    return _call_agentcore(config["regulatory_arn"], query)
