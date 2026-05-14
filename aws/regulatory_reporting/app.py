"""
Regulatory Reporting A2A Agent — Lambda handler.

Provides Basel III capital adequacy (CRAR), liquidity coverage (LCR/NSFR),
and NPA analysis for Cymbal Wealth's regulatory compliance.
Queries Redshift Serverless via the shared Lambda Layer.

Called by GCP's Compliance & Reporting agent via A2A protocol.
"""

import json
import logging
import os
import re
from pathlib import Path

import boto3

from a2a_adapter import route_request
from redshift_client import execute_query_json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

# Load agent card at module level (cold start, reused across invocations)
_AGENT_CARD_PATH = Path(__file__).parent / "agent_card.json"
with open(_AGENT_CARD_PATH) as f:
    AGENT_CARD = json.load(f)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a Regulatory Reporting agent for Cymbal Wealth, a licensed Indian banking institution.

Your role is to retrieve and analyse regulatory data from the bank's Redshift data warehouse and present clear, accurate compliance reports.

Key regulatory benchmarks:
- CRAR (Capital to Risk-weighted Assets Ratio): RBI minimum is 9.0%
- LCR (Liquidity Coverage Ratio): Basel III minimum is 100%
- NSFR (Net Stable Funding Ratio): Basel III minimum is 100%

Formatting rules:
- Always use Indian Rupee symbol: ₹
- Large amounts in Crore (Cr) — e.g. ₹1,250 Cr
- Percentages to two decimal places — e.g. 14.52%
- Always state whether each metric is ABOVE or BELOW the regulatory minimum
- Include the report_date for context

When presenting results:
1. Lead with the headline metric and its compliance status
2. Provide the supporting breakdown (Tier 1, Tier 2, RWA for CRAR; HQLA, net outflows for LCR, etc.)
3. Flag any metric that is within 1 percentage point of the regulatory minimum as a WARNING
4. Use tables for multi-row data

Use the query_regulatory_data tool to retrieve data. Always use ORDER BY report_date DESC LIMIT 1 for latest data unless the user explicitly requests historical trends."""

# ---------------------------------------------------------------------------
# Tool definitions (Bedrock converse format)
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "toolSpec": {
            "name": "query_regulatory_data",
            "description": (
                "Execute a read-only SQL query against the Cymbal Wealth regulatory "
                "data warehouse (Redshift Serverless). Available tables:\n"
                "- capital_adequacy (report_date, tier1_capital, tier2_capital, "
                "total_rwa, crar_pct, min_required)\n"
                "- liquidity_ratios (report_date, hqla, net_cash_30d, lcr_pct, "
                "nsfr_pct)\n"
                "- npa_summary (report_date, gross_npa_pct, net_npa_pct, "
                "provision_cov, total_advances)\n"
                "Use ORDER BY report_date DESC for latest data."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "A read-only SELECT SQL query to execute against Redshift.",
                        }
                    },
                    "required": ["sql"],
                }
            },
        }
    }
]


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------
def _run_tool(name: str, tool_input: dict) -> dict:
    """Execute a tool call. Only query_regulatory_data is supported."""
    if name != "query_regulatory_data":
        return {"error": f"Unknown tool: {name}"}

    sql = tool_input.get("sql", "")

    # Safety: only allow SELECT statements
    normalised = re.sub(r"\s+", " ", sql).strip().upper()
    if not normalised.startswith("SELECT"):
        return {"error": "Only SELECT queries are permitted."}

    # Block mutation keywords even if they appear after SELECT (sub-query injection)
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
    for keyword in forbidden:
        if keyword in normalised:
            return {"error": f"Forbidden SQL keyword: {keyword}"}

    try:
        rows = execute_query_json(sql)
        return {"results": rows, "row_count": len(rows)}
    except Exception as exc:
        logger.exception("Redshift query failed")
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Bedrock converse loop (multi-turn tool use)
# ---------------------------------------------------------------------------
def _converse_with_tools(user_message: str) -> str:
    """Run a Bedrock converse loop, handling tool use turns until the model
    produces a final text response."""
    messages = [{"role": "user", "content": [{"text": user_message}]}]

    for _ in range(10):  # guard against infinite loops
        response = bedrock.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig={"tools": TOOLS},
        )

        stop_reason = response["stopReason"]
        assistant_content = response["output"]["message"]["content"]
        messages.append({"role": "assistant", "content": assistant_content})

        if stop_reason == "end_turn":
            # Extract final text from assistant content
            for block in assistant_content:
                if "text" in block:
                    return block["text"]
            return ""

        if stop_reason == "tool_use":
            tool_results = []
            for block in assistant_content:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    result = _run_tool(tool_use["name"], tool_use["input"])
                    tool_results.append(
                        {
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [{"json": result}],
                            }
                        }
                    )

            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason — return whatever text we have
            for block in assistant_content:
                if "text" in block:
                    return block["text"]
            return f"Unexpected stop reason: {stop_reason}"

    return "Maximum tool-use iterations reached."


# ---------------------------------------------------------------------------
# A2A message handler
# ---------------------------------------------------------------------------
def handle_message(task_text: str) -> dict:
    """Process an A2A message/send request and return the result artifact."""
    logger.info("Regulatory Reporting request: %s", task_text[:200])

    response_text = _converse_with_tools(task_text)

    return {
        "type": "text",
        "text": response_text,
    }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    """AWS Lambda handler — delegates to the shared A2A adapter for routing."""
    return route_request(event, AGENT_CARD, handle_message)
