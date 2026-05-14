"""Credit Intelligence A2A Agent — Strands + AgentCore Runtime.

Deployed to Bedrock AgentCore Runtime as an A2A-compliant agent.
Queries Redshift Serverless for customer credit profiles and loan history.
"""

import json
import os
import time

import boto3
from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a

REDSHIFT_WORKGROUP = os.environ.get("REDSHIFT_WORKGROUP", "cymbal-wealth-wg")
REDSHIFT_DATABASE = os.environ.get("REDSHIFT_DATABASE", "cymbalwealth")
REDSHIFT_SECRET_ARN = os.environ.get("REDSHIFT_SECRET_ARN", "")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

_redshift = boto3.client("redshift-data", region_name=BEDROCK_REGION)


def _execute_redshift(sql: str) -> list[dict]:
    params = {
        "WorkgroupName": REDSHIFT_WORKGROUP,
        "Database": REDSHIFT_DATABASE,
        "Sql": sql,
    }
    if REDSHIFT_SECRET_ARN:
        params["SecretArn"] = REDSHIFT_SECRET_ARN

    resp = _redshift.execute_statement(**params)
    stmt_id = resp["Id"]

    for _ in range(60):
        desc = _redshift.describe_statement(Id=stmt_id)
        status = desc["Status"]
        if status == "FINISHED":
            break
        if status in ("FAILED", "ABORTED"):
            raise RuntimeError(f"Redshift query {status}: {desc.get('Error', 'unknown')}")
        time.sleep(0.5)

    result = _redshift.get_statement_result(Id=stmt_id)
    columns = [col["name"] for col in result["ColumnMetadata"]]
    rows = []
    for record in result["Records"]:
        row = {}
        for i, field in enumerate(record):
            for k, v in field.items():
                if k != "isNull":
                    row[columns[i]] = v
                    break
            else:
                row[columns[i]] = None
        rows.append(row)
    return rows


@tool
def query_credit_data(sql_query: str) -> str:
    """Query customer credit profiles and loan history from Redshift Serverless.

    Available tables:
    - credit_profiles: customer_ref, cibil_score, credit_grade, active_loans, total_exposure, dpd_30, dpd_90, updated_at
    - loan_history: customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at

    Always filter by customer_ref. Only SELECT queries are allowed.

    Args:
        sql_query: SQL SELECT query to execute against Redshift.

    Returns:
        JSON string with query results.
    """
    if not sql_query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed"})
    try:
        rows = _execute_redshift(sql_query)
        return json.dumps(rows, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


SYSTEM_PROMPT = """You are the Credit Intelligence Agent for Cymbal Wealth, a banking institution.
You have access to Redshift Serverless containing customer credit profiles and loan history.

When asked about a customer's credit standing, ALWAYS use the query_credit_data tool to fetch real data.
Never fabricate credit scores or financial figures.

Customer reference numbers follow the format CW-YYYY-NNN (e.g., CW-2026-001).

Format responses clearly with:
- Credit score and grade
- Active loans summary
- DTI ratio (total EMI / assumed monthly income of Rs 1,50,000)
- Eligibility recommendation with max loan amount

Use Indian Rupee formatting. Be precise with numbers."""

agent = Agent(
    model="us.anthropic.claude-sonnet-4-6",
    system_prompt=SYSTEM_PROMPT,
    tools=[query_credit_data],
    name="Cymbal Wealth Credit Intelligence",
    description="Provides CIBIL-style credit scoring, debt-to-income analysis, and loan eligibility assessments for Cymbal Wealth customers.",
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
