"""A2A Client — calls remote A2A agents from GCP via OIDC federation.

Authentication flow (no static AWS credentials needed):
  GCP metadata server (Cloud Run / GCE)
    → Google-signed OIDC ID token
    → AWS STS AssumeRoleWithWebIdentity
    → Temporary AWS credentials
    → boto3 AgentCore invocation (SigV4)

Config via environment variables:
- A2A_CREDIT_ARN: Credit Intelligence AgentCore Runtime ARN
- A2A_REGULATORY_ARN: Regulatory Reporting AgentCore Runtime ARN
- A2A_AWS_ROLE_ARN: IAM role to assume via OIDC (default: cymbal-wealth-gcp-agentcore)
- A2A_OIDC_AUDIENCE: Audience claim for the OIDC token (default: "sts.amazonaws.com").
    Note: AWS checks the `azp` claim (SA numeric ID) against the OIDC provider's
    client IDs, NOT this audience value. This can be any string.
- A2A_GATEWAY_ENABLED: "true" to route via GCP Agent Gateway (default: "false")
- A2A_GATEWAY_URL: Agent Gateway base URL (when enabled)
- AWS_REGION: AWS region for AgentCore (default: "us-east-1")
"""

import json
import logging
import os
import threading
import uuid
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
OIDC_AUDIENCE = os.environ.get("A2A_OIDC_AUDIENCE", "sts.amazonaws.com")


class A2AError(Exception):
    pass


_creds_lock = threading.Lock()
_cached_creds: dict = {}
_creds_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)
_boto3_client = None
_boto3_creds_id: str | None = None


def _get_gcp_id_token(audience: str) -> str:
    """Get a Google-signed OIDC ID token. Works on Cloud Run, GCE, and locally."""
    import requests as http_requests

    # Fastest path: GCE/Cloud Run metadata server (no IAM API, no extra perms)
    try:
        resp = http_requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/"
            f"service-accounts/default/identity?audience={audience}&format=full",
            headers={"Metadata-Flavor": "Google"},
            timeout=3,
        )
        if resp.ok:
            logger.info(f"[A2A] Got OIDC token via metadata server (aud={audience})")
            return resp.text
    except http_requests.ConnectionError:
        pass

    # Fallback: google-auth library (uses ADC — works with SA key files)
    import google.oauth2.id_token
    import google.auth.transport.requests
    token = google.oauth2.id_token.fetch_id_token(
        google.auth.transport.requests.Request(), audience
    )
    logger.info(f"[A2A] Got OIDC token via google-auth (aud={audience})")
    return token


def _get_aws_credentials() -> dict:
    """Exchange GCP ID token for temporary AWS credentials via OIDC federation."""
    global _cached_creds, _creds_expiry

    now = datetime.now(timezone.utc)
    if _cached_creds and now < _creds_expiry - timedelta(minutes=5):
        return _cached_creds

    with _creds_lock:
        if _cached_creds and now < _creds_expiry - timedelta(minutes=5):
            return _cached_creds

        try:
            import requests as http_requests
            import xml.etree.ElementTree as ET

            id_token = _get_gcp_id_token(OIDC_AUDIENCE)

            resp = http_requests.post("https://sts.amazonaws.com/", data={
                "Version": "2011-06-15",
                "Action": "AssumeRoleWithWebIdentity",
                "RoleArn": AWS_ROLE_ARN,
                "RoleSessionName": f"cymbal-gcp-{uuid.uuid4().hex[:8]}",
                "WebIdentityToken": id_token,
                "DurationSeconds": "3600",
            }, timeout=15)
            if not resp.ok:
                error_text = resp.text.replace("\n", " ").replace("\r", "")
                logger.error(f"[A2A] STS {resp.status_code}: {error_text}")
            resp.raise_for_status()

            ns = {"sts": "https://sts.amazonaws.com/doc/2011-06-15/"}
            root = ET.fromstring(resp.text)

            def _find(el, tag):
                node = el.find(f"sts:{tag}", ns)
                if node is None:
                    node = el.find(tag)
                return node

            result = root.find(".//sts:AssumeRoleWithWebIdentityResult", ns)
            if result is None:
                result = root.find(".//AssumeRoleWithWebIdentityResult")
            cred_el = _find(result, "Credentials") if result is not None else None
            if cred_el is None:
                raise ValueError(f"No Credentials in STS response: {resp.text[:300]}")

            def _text(tag):
                node = _find(cred_el, tag)
                return node.text if node is not None else None

            _cached_creds = {
                "aws_access_key_id": _text("AccessKeyId"),
                "aws_secret_access_key": _text("SecretAccessKey"),
                "aws_session_token": _text("SessionToken"),
            }
            expiry_str = _text("Expiration")
            _creds_expiry = (
                datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                if expiry_str
                else now + timedelta(hours=1)
            )
            logger.info("[A2A] OIDC credentials refreshed")
            return _cached_creds

        except Exception as exc:
            raise A2AError(f"OIDC credential exchange failed: {exc}") from exc


def _get_boto3_client():
    """Return a boto3 bedrock-agentcore client with OIDC-derived credentials."""
    global _boto3_client, _boto3_creds_id
    import boto3

    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return boto3.client("bedrock-agentcore", region_name=AWS_REGION)

    creds = _get_aws_credentials()
    creds_id = creds["aws_access_key_id"]
    if _boto3_client is not None and _boto3_creds_id == creds_id:
        return _boto3_client
    _boto3_client = boto3.client("bedrock-agentcore", region_name=AWS_REGION, **creds)
    _boto3_creds_id = creds_id
    return _boto3_client


def _extract_a2a_text(body: dict) -> str:
    """Extract text from an A2A JSON-RPC response (artifacts or history format)."""
    result = body.get("result", {})
    messages = result.get("artifacts") or result.get("history", [])
    for msg in reversed(messages):
        for part in msg.get("parts", []):
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
    raise A2AError(f"No text in A2A response: {json.dumps(body)[:300]}")


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

    return _extract_a2a_text(body)


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

    return _extract_a2a_text(body)


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
