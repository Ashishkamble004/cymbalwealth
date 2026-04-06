"""Google Secret Manager helper with fallback to environment variables."""

import os


def get_secret(secret_id: str, project_id: str = "general-ak") -> str:
    """Fetch a secret value from Secret Manager, falling back to env vars.

    Args:
        secret_id: The Secret Manager secret ID (e.g. "workday-api-token").
        project_id: GCP project ID. Defaults to "general-ak".

    Returns:
        The secret value as a string.
    """
    # Env-var fallback: convert hyphens to underscores and upper-case
    env_key = secret_id.upper().replace("-", "_")
    env_val = os.environ.get(env_key)
    if env_val:
        return env_val

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        raise RuntimeError(
            f"Secret '{secret_id}' not found in env var '{env_key}' "
            f"or Secret Manager: {exc}"
        ) from exc
