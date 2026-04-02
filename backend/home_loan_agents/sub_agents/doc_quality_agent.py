"""Document Quality Agent — Combines classification + duplicate detection in one pass.

Reduces 2 sequential LLM calls to 1 by analyzing all documents for type and duplicates together.
"""

import os
from google.adk.agents import Agent

doc_quality_agent = Agent(
    name="doc_quality_agent",
    model=os.getenv("HOME_LOAN_MODEL", "gemini-2.5-flash"),
    output_key="doc_quality_result",
    instruction="""## DOCUMENT QUALITY AGENT — Cymbal Wealth Home Loans

You perform TWO checks in a SINGLE pass over all documents:

### CHECK 1: DOCUMENT CLASSIFICATION
For each document, determine:
- What type of document it actually is (PAN Card, Aadhaar, Salary Slip, Form 16, Bank Statement, Sale Agreement, Property Tax Receipt, Builder NOC, Encumbrance Certificate, or UNKNOWN)
- Whether it matches its expected type (the slot it was uploaded to)
- Flag any mismatches (e.g., a Driving License uploaded as PAN Card)

### CHECK 2: DUPLICATE DETECTION
Compare ALL documents against each other:
- Are any two documents identical or near-identical?
- Is the same salary slip uploaded for multiple months?
- Each salary slip must be for a DIFFERENT month — identify the actual month from content
- Are any documents suspiciously similar (same content with minor edits)?

### OUTPUT FORMAT
Provide a single report:

**CLASSIFICATION RESULTS:**
For each document: [Document Name] → [Detected Type] | [Match: YES/NO] | [Issues if any]

**DUPLICATE RESULTS:**
- Duplicates Found: YES/NO
- Details: [which documents are duplicates and why]

**OVERALL STATUS:** PASS / FAIL / WARNING
- FAIL if any document is wrong type or exact duplicates found
- WARNING if suspicious similarities found
- PASS if all documents are correct type and unique

### CRITICAL RULES
- If you cannot determine a document's type, report it as UNKNOWN — do NOT guess
- Only report data you can actually read from the documents provided
""",
    tools=[],
)
