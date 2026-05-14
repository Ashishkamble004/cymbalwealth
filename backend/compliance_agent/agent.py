"""Compliance & Reporting Agent — queries AWS Regulatory Reporting via A2A.

Deployed to Vertex AI Agent Engine. Called from demo portal.
Uses the A2A protocol to delegate regulatory data queries to the
AWS-hosted Regulatory Reporting agent backed by Redshift Serverless.
"""

import os

from google.adk.agents import Agent
from google.genai import types


def query_regulatory_data(query: str) -> dict:
    """Query regulatory compliance data via the AWS Regulatory Reporting A2A agent.

    Args:
        query: Natural language question about capital adequacy, liquidity, NPA,
               or Basel III compliance metrics.

    Returns:
        dict with regulatory_report key containing the response.
    """
    from a2a_client import call_regulatory_reporting

    try:
        result = call_regulatory_reporting(query)
        return {"regulatory_report": result}
    except Exception as e:
        return {"regulatory_report": f"Regulatory data unavailable: {str(e)}"}


def create_compliance_agent() -> Agent:
    """Factory function for Agent Engine deployment (same pattern as hr_agents/deploy.py)."""
    return Agent(
        name="compliance_reporting_agent",
        model=os.environ.get("COMPLIANCE_MODEL", "gemini-2.5-flash"),
        generate_content_config=types.GenerateContentConfig(temperature=0.1),
        tools=[query_regulatory_data],
        instruction=_INSTRUCTION,
    )


_INSTRUCTION = """## COMPLIANCE & REPORTING AGENT — Cymbal Wealth

You are the Compliance & Reporting intelligence agent for Cymbal Wealth bank.
You answer questions about regulatory compliance by querying the Regulatory Reporting service.

### CAPABILITIES
- **Capital Adequacy (CRAR)**: Capital to Risk-weighted Assets Ratio vs RBI minimum of 9%
- **Liquidity Ratios**: LCR (Liquidity Coverage Ratio) and NSFR (Net Stable Funding Ratio)
- **Asset Quality (NPA)**: Gross NPA %, Net NPA %, provision coverage ratio
- **Basel III Summary**: Tier 1 + Tier 2 capital breakdown, risk-weighted assets

### HOW TO RESPOND
1. ALWAYS call the query_regulatory_data tool — never fabricate regulatory numbers
2. Present data with clear comparisons to regulatory minimums
3. Highlight metrics close to or below regulatory thresholds
4. Show quarter-over-quarter trends when multiple periods are available
5. Use Indian Rupee (₹) and Crore (Cr) formatting

### IF SERVICE IS UNAVAILABLE
Report clearly that the regulatory data service is temporarily unavailable.
Do NOT invent regulatory numbers — this is compliance-critical data.
"""

compliance_agent = create_compliance_agent()
