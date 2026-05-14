"""
Credit Intelligence Agent — AWS Lambda handler.

Provides CIBIL-style credit scoring, debt-to-income analysis, and loan
eligibility assessments for Cymbal Wealth customers. Queries Redshift
Serverless for credit profiles and loan history, reasons over the data
using Bedrock Converse API (Claude), and exposes the result as an A2A-
compliant endpoint via the shared a2a_adapter layer.

Called by GCP's Home Loan orchestrator via A2A protocol.
"""

import json
import os
import pathlib

import boto3

# Shared Lambda Layer imports
from a2a_adapter import route_request
from redshift_client import execute_query_json

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-6")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

# Load agent card once at module level (stays warm across Lambda invocations)
_AGENT_CARD_PATH = pathlib.Path(__file__).parent / "agent_card.json"
with open(_AGENT_CARD_PATH) as _f:
    AGENT_CARD = json.load(_f)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are the Credit Intelligence agent for Cymbal Wealth, a premium "
    "wealth-management bank in India. Your job is to assess customer "
    "creditworthiness by querying the bank's credit data warehouse.\n\n"
    "You have access to a tool that can execute SELECT queries against "
    "Redshift Serverless. Use it to look up credit profiles (CIBIL scores, "
    "credit grades, active loans, exposure, delinquency counts) and loan "
    "history (loan types, sanctioned vs outstanding amounts, EMI, status).\n\n"
    "When answering:\n"
    "- Always cite the CIBIL score and grade.\n"
    "- Calculate debt-to-income (DTI) ratio when income data is available.\n"
    "- For eligibility assessments, state whether the customer qualifies, "
    "the recommended maximum loan amount, and any risk flags.\n"
    "- Use clear, concise banking language.\n"
    "- If a customer reference number is not found, say so explicitly.\n"
    "- Never fabricate data — only report what the query returns.\n"
    "- Return monetary values in INR with commas (e.g., 12,50,000)."
)

# ---------------------------------------------------------------------------
# Tool definitions (Bedrock Converse toolConfig format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "toolSpec": {
            "name": "query_credit_data",
            "description": (
                "Execute a read-only SQL query against the Cymbal Wealth "
                "credit data warehouse (Redshift Serverless). "
                "Available tables:\n"
                "  - credit_profiles (customer_ref, cibil_score, credit_grade, "
                "active_loans, total_exposure, dpd_30, dpd_90, updated_at)\n"
                "  - loan_history (customer_ref, loan_type, sanctioned_amt, "
                "outstanding_amt, emi, status, opened_at, closed_at)"
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": (
                                "A SELECT SQL query to run against Redshift. "
                                "Only SELECT statements are permitted."
                            ),
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


def _run_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool call and return the result as a dict."""
    if tool_name != "query_credit_data":
        return {"error": f"Unknown tool: {tool_name}"}

    sql = tool_input.get("sql", "").strip()

    # Safety: only allow SELECT statements
    first_keyword = sql.split()[0].upper() if sql else ""
    if first_keyword != "SELECT":
        return {
            "error": (
                "Only SELECT queries are allowed. "
                f"Received statement starting with: {first_keyword}"
            )
        }

    # Block obviously dangerous patterns even inside a SELECT
    sql_upper = sql.upper()
    for forbidden in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"):
        # Check for the keyword as a standalone token (not part of a column name)
        if f" {forbidden} " in f" {sql_upper} ":
            return {"error": f"Forbidden keyword detected: {forbidden}"}

    try:
        rows = execute_query_json(sql)
        return {"rows": rows, "row_count": len(rows)}
    except Exception as exc:
        return {"error": f"Query execution failed: {str(exc)}"}


# ---------------------------------------------------------------------------
# Bedrock Converse loop (tool-use capable)
# ---------------------------------------------------------------------------

MAX_TOOL_ROUNDS = 5


def _converse_with_tools(user_text: str) -> str:
    """Send a message through Bedrock Converse with tool-use loop.

    Calls bedrock.converse() and, if the model requests tool use, executes
    the tool and feeds the result back. Loops up to MAX_TOOL_ROUNDS times
    before returning whatever partial answer is available.
    """
    messages = [
        {"role": "user", "content": [{"text": user_text}]}
    ]

    for _round in range(MAX_TOOL_ROUNDS):
        response = bedrock.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=messages,
            system=[{"text": SYSTEM_PROMPT}],
            toolConfig={"tools": TOOLS},
        )

        output_message = response["output"]["message"]
        stop_reason = response["stopReason"]

        # Append the assistant's reply to the conversation
        messages.append(output_message)

        if stop_reason == "end_turn":
            # Extract final text from assistant response
            return _extract_text(output_message)

        if stop_reason == "tool_use":
            # Process each tool-use block in the assistant's response
            tool_results = []
            for block in output_message["content"]:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    tool_name = tool_use["name"]
                    tool_input = tool_use["input"]
                    tool_use_id = tool_use["toolUseId"]

                    result = _run_tool(tool_name, tool_input)

                    tool_results.append(
                        {
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [{"json": result}],
                            }
                        }
                    )

            # Send tool results back to the model
            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason — return whatever text we have
            return _extract_text(output_message)

    # Exhausted tool rounds — return the last assistant text
    return _extract_text(messages[-1]) if messages else "Max tool rounds reached."


def _extract_text(message: dict) -> str:
    """Pull text parts out of a Bedrock Converse message."""
    parts = []
    for block in message.get("content", []):
        if "text" in block:
            parts.append(block["text"])
    return "\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def handle_message(user_text: str) -> str:
    """Process a single user message and return the agent's response."""
    return _converse_with_tools(user_text)


def lambda_handler(event, context):
    """AWS Lambda entry point.

    Delegates to the shared A2A adapter which handles:
    - GET /.well-known/agent-card.json → returns AGENT_CARD
    - GET /ping → health check
    - POST / → JSON-RPC message/send → calls handle_message
    """
    return route_request(event, AGENT_CARD, handle_message)
