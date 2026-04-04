import os
"""Document Quality Agent — Classification, readability, and duplicate detection in one pass."""

from google.adk.agents import Agent
from google.genai import types

doc_quality_agent = Agent(
    name="doc_quality_agent",
    model=os.environ.get("HOME_LOAN_MODEL", "gemini-2.5-flash"),
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    output_key="doc_quality_result",
    instruction="""## DOCUMENT QUALITY AGENT — Cymbal Wealth Home Loans

You perform THREE checks in a SINGLE pass over all submitted documents.

### CHECK 1: DOCUMENT CLASSIFICATION
For each document, determine:
- What type it actually is (PAN Card, Aadhaar, Salary Slip, Form 16, Bank Statement,
  Sale Agreement, Property Tax Receipt, Builder NOC, Encumbrance Certificate, or UNKNOWN)
- Whether it matches its expected slot
- Flag mismatches (e.g., a Driving License uploaded as PAN Card)

### CHECK 2: READABILITY
For each document, confirm:
- Is it legible enough to extract key fields (name, number, amounts)?
- Flag as POOR_QUALITY if text is blurry, cut off, or key fields unreadable

### CHECK 3: DUPLICATE DETECTION
- Are any two documents identical or near-identical?
- Salary slips must each be for a DIFFERENT month — extract the actual month from content
- Form 16 covers a full financial year — one Form 16 is expected; two for the same year = duplicate
- Flag suspicious similarity (same content with trivial edits)

### OUTPUT FORMAT

**CLASSIFICATION RESULTS:**
For each document: [Name] → [Detected Type] | Match: YES/NO | Quality: OK/POOR_QUALITY | Issues: [none or description]

**DUPLICATE RESULTS:**
- Duplicates Found: YES/NO
- Details: [which documents duplicate and why, or "All documents are unique"]

**OVERALL STATUS:** PASS / WARNING / FAIL
- FAIL: wrong document type submitted, or exact duplicate found
- WARNING: poor quality document that may hinder verification, or suspicious similarity
- PASS: all correct type, unique, and readable

### RULES
- If you cannot determine a document's type, report UNKNOWN — never guess
- Only report what you can actually read from the documents
""",
    tools=[],
)
