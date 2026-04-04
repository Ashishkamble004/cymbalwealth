"""Shared model factory for home loan agents.

Returns ApigeeLlm when APIGEE_PROXY_URL is set (routes through Apigee AI Gateway
for token telemetry, audit logging, and gemini-2.0 deny policy).
Falls back to direct Vertex AI if Apigee is not configured.
"""

import os
from google.adk.models.apigee_llm import ApigeeLlm

APIGEE_PROXY_URL = os.environ.get("APIGEE_PROXY_URL")
_BASE_MODEL = os.environ.get("HOME_LOAN_MODEL", "gemini-2.5-flash")


def get_model(app_label: str):
    """Return ApigeeLlm if Apigee proxy is configured, else direct model string."""
    if APIGEE_PROXY_URL:
        return ApigeeLlm(
            model=f"apigee/vertex_ai/{_BASE_MODEL}",
            proxy_url=APIGEE_PROXY_URL,
            custom_headers={"x-cymbal-app": app_label},
        )
    return _BASE_MODEL
