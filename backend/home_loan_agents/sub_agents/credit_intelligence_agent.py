"""Credit Intelligence Agent — A2A bridge to AWS Credit Intelligence.

Calls the AWS-hosted Credit Intelligence A2A agent to get CIBIL credit scores,
DTI ratios, and loan eligibility. Runs as part of the Home Loan ParallelAgent.
"""

import os

from google.adk.agents import Agent
from google.genai import types


def check_credit(customer_ref: str) -> dict:
    """Check credit score and loan eligibility for a customer.

    Args:
        customer_ref: Customer reference number (e.g., CW-2026-001)

    Returns:
        dict with credit_report key containing the A2A agent's response
    """
    from a2a_client import call_credit_intelligence

    query = (
        f"Provide complete credit analysis for customer {customer_ref}: "
        f"CIBIL score, credit grade, active loans summary, "
        f"debt-to-income ratio, and loan eligibility recommendation."
    )
    try:
        result = call_credit_intelligence(query)
        return {"credit_report": result}
    except Exception as e:
        return {"credit_report": f"Credit check unavailable: {str(e)}"}


credit_intelligence_agent = Agent(
    name="credit_intelligence_agent",
    model=os.environ.get("HOME_LOAN_MODEL", "gemini-2.5-flash"),
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    output_key="credit_intelligence_result",
    tools=[check_credit],
    instruction="""## CREDIT INTELLIGENCE AGENT — Cymbal Wealth Home Loans

You verify the applicant's creditworthiness using the external Credit Intelligence service.

### YOUR TASK
1. Call the check_credit tool with the customer reference number from the application
2. Report the results clearly

### EXTRACT CUSTOMER REFERENCE
The customer reference follows the format CW-YYYY-NNN (e.g., CW-2026-001).
Look for it in the applicant details provided.
If no reference number is available, use the applicant's PAN as the lookup key.

### OUTPUT FORMAT
Summarize:
- **CIBIL Score**: [score] ([grade])
- **Active Loans**: [count] loans, total EMI ₹[amount]/month
- **DTI Ratio**: [percentage]%
- **Credit Eligibility**: [ELIGIBLE/NOT ELIGIBLE] — max recommended loan: ₹[amount]
- **Risk Flags**: [any DPD or adverse items]

If the credit check service is unavailable, report that clearly — do NOT fabricate scores.
""",
)
