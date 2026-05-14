"""A2A Client — calls remote A2A agents from GCP via OIDC federation.

Authentication flow (no static AWS credentials needed):
  GCP Cloud Run service account
    → GCP ID token (google-auth)
    → AWS STS AssumeRoleWithWebIdentity
    → Temporary AWS credentials
    → boto3 AgentCore invocation (SigV4)

Config via environment variables:
- A2A_CREDIT_ARN: Credit Intelligence AgentCore Runtime ARN
- A2A_REGULATORY_ARN: Regulatory Reporting AgentCore Runtime ARN
- A2A_AWS_ROLE_ARN: IAM role to assume via OIDC (default: cymbal-wealth-gcp-agentcore)
- A2A_GATEWAY_ENABLED: "true" to route via GCP Agent Gateway (default: "false")
- A2A_GATEWAY_URL: Agent Gateway base URL (when enabled)
- AWS_REGION: AWS region for AgentCore (default: "us-east-1")
"""

import json
import logging
import os
import uuid
from functools import lru_cache
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

CREDIT_ARN = os.environ.get(
    "A2A_CREDIT_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:453809273083:runtime/cymbal_credit_intelligence-26fPFAF9gS",
)
REGULATORY_ARN = os.environ.get(
    "A2A_REGULATORY_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:453809273083:runtime/cymbal_regulatory_reporting-vA2VQ08PxI",
)
AWS_ROLE_ARN = os.environ.get(
    "A2A_AWS_ROLE_ARN",
    "arn:aws:iam::453809273083:role/cymbal-wealth-gcp-agentcore",
)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


class A2AError(Exception):
    pass


# Cache temporary credentials (they last 1 hour; refresh with 5 min buffer)
_cached_creds: dict = {}
_creds_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)


def _get_aws_credentials() -> dict:
    """Exchange GCP ID token for temporary AWS credentials via OIDC federation."""
    global _cached_creds, _creds_expiry

    now = datetime.now(timezone.utc)
    if _cached_creds and now < _creds_expiry - timedelta(minutes=5):
        return _cached_creds

    try:
        import google.auth
        import google.auth.transport.requests
        import google.oauth2.id_token
        import boto3
        import requests as http_requests
        import xml.etree.ElementTree as ET

        # Get GCP ID token — audience is the STS endpoint
        audience = "https://sts.amazonaws.com"
        request = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(request, audience)

        # AssumeRoleWithWebIdentity via unsigned HTTP POST — no AWS credentials needed.
        # Use global STS endpoint (not regional) for OIDC web identity exchanges.
        sts_url = "https://sts.amazonaws.com/"
        params = {
            "Version": "2011-06-15",
            "Action": "AssumeRoleWithWebIdentity",
            "RoleArn": AWS_ROLE_ARN,
            "RoleSessionName": f"cymbal-gcp-{uuid.uuid4().hex[:8]}",
            "WebIdentityToken": id_token,
            "DurationSeconds": "3600",
        }
        resp = http_requests.post(sts_url, data=params, timeout=10)
        if not resp.ok:
            logger.error(f"[A2A] STS response {resp.status_code}: {resp.text[:2000]}")
        resp.raise_for_status()

        # Parse XML response
        ns = {"sts": "https://sts.amazonaws.com/doc/2011-06-15/"}
        root = ET.fromstring(resp.text)
        result = root.find(".//sts:AssumeRoleWithWebIdentityResult", ns)
        if result is None:
            # Try without namespace
            result = root.find(".//AssumeRoleWithWebIdentityResult")
        cred_el = result.find("sts:Credentials", ns) if result is not None else None
        if cred_el is None and result is not None:
            cred_el = result.find("Credentials")

        if cred_el is None:
            raise ValueError(f"No Credentials in STS response: {resp.text[:300]}")

        def _text(el, tag):
            node = el.find(f"sts:{tag}", ns) or el.find(tag)
            return node.text if node is not None else None

        _cached_creds = {
            "aws_access_key_id": _text(cred_el, "AccessKeyId"),
            "aws_secret_access_key": _text(cred_el, "SecretAccessKey"),
            "aws_session_token": _text(cred_el, "SessionToken"),
        }
        expiry_str = _text(cred_el, "Expiration")
        _creds_expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00")) if expiry_str else datetime.now(timezone.utc) + timedelta(hours=1)
        logger.info("[A2A] OIDC credentials refreshed via unsigned STS AssumeRoleWithWebIdentity")
        return _cached_creds

    except Exception as exc:
        raise A2AError(f"OIDC credential exchange failed: {exc}") from exc


def _get_boto3_client():
    """Return a boto3 bedrock-agentcore client with OIDC-derived credentials."""
    import boto3

    # If running locally with explicit AWS env vars, use them directly
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return boto3.client("bedrock-agentcore", region_name=AWS_REGION)

    # On Cloud Run: use OIDC federation
    creds = _get_aws_credentials()
    return boto3.client("bedrock-agentcore", region_name=AWS_REGION, **creds)


def get_config() -> dict:
    return {
        "credit_arn": CREDIT_ARN,
        "regulatory_arn": REGULATORY_ARN,
        "gateway_enabled": os.environ.get("A2A_GATEWAY_ENABLED", "false").lower() == "true",
        "gateway_url": os.environ.get("A2A_GATEWAY_URL", ""),
        "aws_region": AWS_REGION,
    }


def _call_agentcore(runtime_arn: str, user_message: str) -> str:
    """Invoke an AgentCore Runtime agent — SigV4 auth handled by boto3."""
    client = _get_boto3_client()
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
