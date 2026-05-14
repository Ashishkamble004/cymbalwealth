"""Regulatory Reporting A2A Agent — Strands + AgentCore Runtime.

Deployed to Bedrock AgentCore Runtime as an A2A-compliant agent.
Queries Redshift Serverless for Basel III, RBI CRAR, LCR, NSFR, and NPA data.
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
def query_regulatory_data(sql_query: str) -> str:
    """Query regulatory compliance data from Redshift Serverless.

    Available tables:
    - capital_adequacy: report_date, tier1_capital, tier2_capital, total_rwa, crar_pct, min_required
    - liquidity_ratios: report_date, hqla, net_cash_30d, lcr_pct, nsfr_pct
    - npa_summary: report_date, gross_npa_pct, net_npa_pct, provision_cov, total_advances

    Order by report_date DESC for latest data. Only SELECT queries are allowed.

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


SYSTEM_PROMPT = """You are the Regulatory Reporting Agent for Cymbal Wealth, a banking institution.
You have access to Redshift Serverless containing regulatory and compliance data.

When asked about capital adequacy, liquidity, or asset quality, ALWAYS use the query_regulatory_data tool.
Never fabricate regulatory figures.

Key regulatory benchmarks:
- CRAR (Capital to Risk-weighted Assets Ratio): RBI minimum is 9.0%
- LCR (Liquidity Coverage Ratio): minimum 100%
- NSFR (Net Stable Funding Ratio): minimum 100%

Format responses clearly with:
- Current metric value vs regulatory minimum
- Buffer above/below minimum
- Tier 1 and Tier 2 capital breakdown where relevant
- Quarter-over-quarter trend if multiple periods available

Use Indian Rupee and Crore (Cr) formatting. Be precise with numbers and percentages."""

agent = Agent(
    model="us.anthropic.claude-sonnet-4-6",
    system_prompt=SYSTEM_PROMPT,
    tools=[query_regulatory_data],
    name="Cymbal Wealth Regulatory Reporting",
    description="Provides Basel III capital adequacy (CRAR), liquidity coverage (LCR/NSFR), and NPA analysis for Cymbal Wealth regulatory compliance.",
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
