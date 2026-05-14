"""Shared Redshift Data API client for CymbalWealth A2A agents.

This module wraps the Redshift Data API (boto3 redshift-data) for use as a
Lambda Layer shared by both Credit Intelligence and Regulatory Reporting agents.
Each agent's Lambda handler calls execute_query_json(sql) when Bedrock requests
a tool call to query Redshift Serverless.

Environment variables:
    REDSHIFT_WORKGROUP  – Redshift Serverless workgroup name (default: cymbal-wealth-wg)
    REDSHIFT_DATABASE   – Database name inside the workgroup   (default: cymbalwealth)
    REDSHIFT_SECRET_ARN – Secrets Manager ARN for DB credentials (required in prod)
"""

from __future__ import annotations

import json
import os
import time

import boto3

# ---------------------------------------------------------------------------
# Module-level configuration — read once at import / cold-start
# ---------------------------------------------------------------------------
WORKGROUP: str = os.environ.get("REDSHIFT_WORKGROUP", "cymbal-wealth-wg")
DATABASE: str = os.environ.get("REDSHIFT_DATABASE", "cymbalwealth")
SECRET_ARN: str = os.environ.get("REDSHIFT_SECRET_ARN", "")

# Reuse across invocations (Lambda container reuse / warm starts)
_client = boto3.client("redshift-data")

# Polling interval in seconds
_POLL_INTERVAL: float = 0.5

# Terminal states returned by describe_statement
_FINISHED = "FINISHED"
_FAILED = "FAILED"
_ABORTED = "ABORTED"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wait_for_statement(statement_id: str, max_wait_seconds: int) -> dict:
    """Poll describe_statement until the query reaches a terminal state.

    Returns the final describe_statement response on FINISHED.
    Raises RuntimeError on FAILED/ABORTED; TimeoutError if max_wait exceeded.
    """
    elapsed: float = 0.0
    while elapsed < max_wait_seconds:
        resp = _client.describe_statement(Id=statement_id)
        status = resp["Status"]

        if status == _FINISHED:
            return resp

        if status == _FAILED:
            error = resp.get("Error", "unknown error")
            raise RuntimeError(
                f"Redshift query {statement_id} FAILED: {error}"
            )

        if status == _ABORTED:
            raise RuntimeError(
                f"Redshift query {statement_id} was ABORTED"
            )

        time.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL

    raise TimeoutError(
        f"Redshift query {statement_id} did not finish within "
        f"{max_wait_seconds}s (last status: {status})"
    )


def _parse_results(response: dict) -> list[dict]:
    """Convert get_statement_result response into a list of row dicts.

    Each row is a dict mapping column name -> Python value, derived from
    the Redshift Data API Field union type.
    """
    columns = [col["name"] for col in response["ColumnMetadata"]]
    rows: list[dict] = []

    for record in response.get("Records", []):
        row: dict = {}
        for idx, field in enumerate(record):
            col_name = columns[idx]
            if field.get("isNull", False):
                row[col_name] = None
            elif "stringValue" in field:
                row[col_name] = field["stringValue"]
            elif "longValue" in field:
                row[col_name] = field["longValue"]
            elif "doubleValue" in field:
                row[col_name] = field["doubleValue"]
            elif "booleanValue" in field:
                row[col_name] = field["booleanValue"]
            else:
                # blobValue or unexpected — stringify for safety
                row[col_name] = str(field)
        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_query(sql: str, max_wait_seconds: int = 30) -> list[dict]:
    """Execute SQL against Redshift Serverless via the Redshift Data API.

    Args:
        sql: The SQL statement to execute.
        max_wait_seconds: Maximum time to wait for query completion.

    Returns:
        A list of dicts, one per row, with column names as keys.

    Raises:
        RuntimeError: If the query fails or is aborted.
        TimeoutError: If the query does not complete within max_wait_seconds.
    """
    execute_params: dict = {
        "WorkgroupName": WORKGROUP,
        "Database": DATABASE,
        "Sql": sql,
    }
    if SECRET_ARN:
        execute_params["SecretArn"] = SECRET_ARN

    resp = _client.execute_statement(**execute_params)
    statement_id: str = resp["Id"]

    _wait_for_statement(statement_id, max_wait_seconds)

    result = _client.get_statement_result(Id=statement_id)
    return _parse_results(result)


def execute_query_json(sql: str, max_wait_seconds: int = 30) -> str:
    """Execute SQL and return the result as a JSON string.

    Convenience wrapper for Bedrock tool responses, which expect a string
    payload rather than a Python object.

    Args:
        sql: The SQL statement to execute.
        max_wait_seconds: Maximum time to wait for query completion.

    Returns:
        JSON-encoded string of the query results (list of row dicts).
    """
    rows = execute_query(sql, max_wait_seconds=max_wait_seconds)
    return json.dumps(rows, default=str)
