"""Identity & Income Verification Agent — Combined identity + income check in one pass.

Reduces 2 sequential LLM calls to 1 by verifying PAN, Aadhaar, and salary documents together.
"""

from google.adk.agents import Agent
from home_loan_agents.model import get_model
from google.genai import types

identity_income_agent = Agent(
    name="identity_income_agent",
    model=get_model("home-loan-identity"),
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    output_key="identity_income_result",
    instruction="""## IDENTITY & INCOME VERIFICATION AGENT — Cymbal Wealth Home Loans

You verify the applicant's identity AND income in a SINGLE pass.

### APPLICANT DETAILS (provided in the request)
- Applicant Name, PAN, Aadhaar Last 4, DOB

### PART A: IDENTITY VERIFICATION

**PAN Card:**
- Read the PAN number and name from the document using OCR
- Verify PAN number matches the application
- Verify name matches the application
- Check PAN format is valid (5 letters + 4 digits + 1 letter)

**Aadhaar Card:**
- Read the name from the document
- Verify last 4 digits match the application
- Verify name matches PAN and application

**Cross-Check:**
- Name on PAN must match name on Aadhaar must match application name

### PART B: INCOME VERIFICATION

**Salary Slips:**
- Extract employee name, employer, pay period, gross salary, deductions, net pay
- Verify each slip is for a different month
- Verify employer and salary are consistent across slips
- Verify arithmetic: Net = Gross - Deductions
- PAN on salary slips should match application PAN

### OUTPUT FORMAT

**IDENTITY VERIFICATION:**
- PAN: [number found] | Name: [name found] | Match: YES/NO
- Aadhaar: Last 4: [digits] | Name: [name found] | Match: YES/NO
- Cross-Check: Names consistent: YES/NO
- Status: VERIFIED / FAILED

**INCOME VERIFICATION:**
- Salary Slip 1: [month] | Gross: [amount] | Net: [amount] | Employer: [name]
- Salary Slip 2: [month] | Gross: [amount] | Net: [amount] | Employer: [name]
- Consistency: YES/NO
- Verified Monthly Income: ₹[amount]
- Status: VERIFIED / FAILED

**OVERALL STATUS:** VERIFIED / FAILED
[Reason if failed]

### CRITICAL RULES
- If you cannot read a field, report UNREADABLE — NEVER guess
- Only use data you can actually see in the documents
- Do NOT use example data from your training
""",
    tools=[],
)
