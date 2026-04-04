"""Document Verification Sub-Agent for Cymbal Wealth Video KYC.

Uses gemini-2.5-flash for text-based document verification tasks.
Called by the root KYC agent via AgentTool.
"""

import os
import logging
from datetime import date
from google.adk.agents import Agent
from google.genai import types

logger = logging.getLogger(__name__)

# Static customer database for demo purposes
CUSTOMER_DATABASE = {
    "CW-2026-001": {
        "name": "Ashish Kamble",
        "pan": "EWIPK1035H",
        "aadhaar_last4": "9692",
        "dob": "1997-04-07",
        "phone": "+91 98765 43210",
        "email": "ashish.kamble@email.com",
        "address": "Flat 501, Horizon Heights, Andheri West, Mumbai 400053",
        "account_type": "Savings",
        "account_number": "XXXX XXXX 7831",
        "branch": "Andheri West, Mumbai",
    },
    "CW-2026-002": {
        "name": "Priya Sharma",
        "pan": "BDFPS5678B",
        "aadhaar_last4": "3456",
        "dob": "1992-07-22",
        "phone": "+91 87654 32109",
        "email": "priya.sharma@email.com",
        "address": "B-12, Green Park Extension, New Delhi 110016",
        "account_type": "Savings",
        "account_number": "XXXX XXXX 8934",
        "branch": "Green Park, Delhi",
    },
}


def lookup_customer(reference_number: str) -> dict:
    """Look up a customer by their reference number in the Cymbal Wealth database.

    Args:
        reference_number: The customer reference number (e.g., CW-2026-001)

    Returns:
        A dictionary with customer details if found, or an error message.
    """
    ref = reference_number.strip().upper()
    customer = CUSTOMER_DATABASE.get(ref)
    if customer:
        return {
            "found": True,
            "reference_number": ref,
            "name": customer["name"],
            "account_type": customer["account_type"],
            "branch": customer["branch"],
            "message": f"Customer {customer['name']} found. Account at {customer['branch']} branch.",
        }
    return {
        "found": False,
        "reference_number": ref,
        "message": "Customer not found in our records. Please check the reference number.",
    }


def verify_pan(reference_number: str, pan_number: str) -> dict:
    """Verify PAN card number against customer records.

    Args:
        reference_number: The customer reference number
        pan_number: The PAN card number provided by customer

    Returns:
        Verification result with match status.
    """
    ref = reference_number.strip().upper()
    pan = pan_number.strip().upper()
    customer = CUSTOMER_DATABASE.get(ref)
    if not customer:
        return {"verified": False, "message": "Customer not found."}
    if customer["pan"] == pan:
        return {
            "verified": True,
            "message": f"PAN {pan} verified successfully for {customer['name']}.",
        }
    return {
        "verified": False,
        "message": "PAN number does not match our records. Please check and try again.",
    }


def verify_aadhaar_last4(reference_number: str, aadhaar_last4: str) -> dict:
    """Verify last 4 digits of Aadhaar number against customer records.

    Args:
        reference_number: The customer reference number
        aadhaar_last4: Last 4 digits of Aadhaar number

    Returns:
        Verification result with match status.
    """
    ref = reference_number.strip().upper()
    digits = aadhaar_last4.strip()
    customer = CUSTOMER_DATABASE.get(ref)
    if not customer:
        return {"verified": False, "message": "Customer not found."}
    if customer["aadhaar_last4"] == digits:
        return {
            "verified": True,
            "message": f"Aadhaar last 4 digits verified successfully for {customer['name']}.",
        }
    return {
        "verified": False,
        "message": "Aadhaar last 4 digits do not match our records.",
    }


def verify_dob(reference_number: str, date_of_birth: str) -> dict:
    """Verify date of birth against customer records.

    Args:
        reference_number: The customer reference number
        date_of_birth: Date of birth in any common format (YYYY-MM-DD, DD/MM/YYYY, etc.)

    Returns:
        Verification result with match status.
    """
    ref = reference_number.strip().upper()
    customer = CUSTOMER_DATABASE.get(ref)
    if not customer:
        return {"verified": False, "message": "Customer not found."}

    # Parse both dates flexibly to handle speech-transcribed formats
    # Handles: "1997-04-07", "07/04/1997", "7th April 1997", "April 7 1997", etc.
    from datetime import datetime as dt
    expected = customer["dob"]  # Always YYYY-MM-DD in our DB

    expected_date = dt.strptime(expected, "%Y-%m-%d").date()

    # Try multiple parsing approaches
    matched = False
    dob_clean = date_of_birth.strip()

    # Common formats to try
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%d.%m.%Y", "%B %d %Y", "%d %B %Y",
        "%b %d %Y", "%d %b %Y", "%B %d, %Y", "%d %B, %Y",
    ]
    for fmt in formats:
        try:
            parsed = dt.strptime(dob_clean, fmt).date()
            if parsed == expected_date:
                matched = True
                break
        except ValueError:
            continue

    # Handle ordinal suffixes: "7th April 1997" → "7 April 1997"
    if not matched:
        import re
        cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', dob_clean)
        for fmt in formats:
            try:
                parsed = dt.strptime(cleaned, fmt).date()
                if parsed == expected_date:
                    matched = True
                    break
            except ValueError:
                continue

    if matched:
        return {
            "verified": True,
            "message": f"Date of birth verified successfully for {customer['name']}.",
        }
    return {
        "verified": False,
        "message": "Date of birth does not match our records.",
    }


def capture_pan_card(reference_number: str, session_id: str) -> dict:
    """Capture the PAN card image from the current video frame and store it in GCS.

    Call this when the customer is holding their PAN card steady in front of the camera.

    Args:
        reference_number: The customer reference number
        session_id: The current session ID

    Returns:
        Status of the capture operation.
    """
    from session_frames import get_latest_frame_sync, get_session_filename_sync
    from storage_utils import save_capture

    frame = get_latest_frame_sync(session_id)
    if not frame:
        return {"captured": False, "message": "No video frame available. Ask the customer to ensure their camera is on."}

    session_filename = get_session_filename_sync(session_id) or session_id
    gcs_uri = save_capture(session_filename, "pan-card", frame)
    if gcs_uri:
        return {"captured": True, "message": "PAN card image captured and stored successfully.", "uri": gcs_uri}
    return {"captured": False, "message": "Failed to store PAN card image."}


def capture_profile_photo(reference_number: str, session_id: str) -> dict:
    """Capture the customer's profile photo from the current video frame and store it in GCS.

    Call this after asking the customer to look directly at the camera and stay still.

    Args:
        reference_number: The customer reference number
        session_id: The current session ID

    Returns:
        Status of the capture operation.
    """
    from session_frames import get_latest_frame_sync, get_session_filename_sync
    from storage_utils import save_capture

    frame = get_latest_frame_sync(session_id)
    if not frame:
        return {"captured": False, "message": "No video frame available. Ask the customer to ensure their camera is on."}

    session_filename = get_session_filename_sync(session_id) or session_id
    gcs_uri = save_capture(session_filename, "profile-photo", frame)
    if gcs_uri:
        return {"captured": True, "message": "Profile photo captured and stored successfully.", "uri": gcs_uri}
    return {"captured": False, "message": "Failed to store profile photo."}


def capture_signature(reference_number: str, session_id: str) -> dict:
    """Capture the customer's signature from the current video frame and store it in GCS.

    Call this when the customer is showing their signed paper to the camera.

    Args:
        reference_number: The customer reference number
        session_id: The current session ID

    Returns:
        Status of the capture operation.
    """
    from session_frames import get_latest_frame_sync, get_session_filename_sync
    from storage_utils import save_capture

    frame = get_latest_frame_sync(session_id)
    if not frame:
        return {"captured": False, "message": "No video frame available. Ask the customer to ensure their camera is on."}

    session_filename = get_session_filename_sync(session_id) or session_id
    gcs_uri = save_capture(session_filename, "signature", frame)
    if gcs_uri:
        return {"captured": True, "message": "Signature captured and stored successfully.", "uri": gcs_uri}
    return {"captured": False, "message": "Failed to store signature image."}


def complete_kyc(reference_number: str, pan_verified: bool, aadhaar_verified: bool, face_verified: bool) -> dict:
    """Complete the Video KYC process and generate a KYC completion reference.

    Args:
        reference_number: The customer reference number
        pan_verified: Whether PAN was verified
        aadhaar_verified: Whether Aadhaar was verified
        face_verified: Whether face/liveness was verified

    Returns:
        KYC completion status with reference ID.
    """
    ref = reference_number.strip().upper()
    customer = CUSTOMER_DATABASE.get(ref)
    if not customer:
        return {"completed": False, "message": "Customer not found."}

    all_verified = pan_verified and aadhaar_verified and face_verified
    if all_verified:
        import random
        import string
        kyc_id = "KYC-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return {
            "completed": True,
            "kyc_reference": kyc_id,
            "customer_name": customer["name"],
            "status": "VERIFIED",
            "message": f"Video KYC completed successfully. Your KYC reference is {kyc_id}. "
                       f"Your account is now fully verified.",
        }
    missing = []
    if not pan_verified:
        missing.append("PAN verification")
    if not aadhaar_verified:
        missing.append("Aadhaar verification")
    if not face_verified:
        missing.append("Face/liveness verification")
    return {
        "completed": False,
        "status": "INCOMPLETE",
        "missing": missing,
        "message": f"KYC incomplete. Still pending: {', '.join(missing)}.",
    }


def get_current_date() -> dict:
    """Get the current date for reference during KYC process.

    Returns:
        Current date information.
    """
    today = date.today()
    return {
        "date": today.isoformat(),
        "formatted": today.strftime("%d %B %Y"),
    }


# Sub-agent definition
document_verification_agent = Agent(
    name="document_verification_agent",
    model="gemini-2.5-flash",
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    instruction="""You are a document verification specialist for Cymbal Wealth.
Your job is to verify customer identity documents during Video KYC by
cross-checking data provided by the root agent against our internal records.

IMPORTANT: You do NOT see the video feed. The root agent (Sanjay) reads the
documents using vision and passes the extracted data to you. You then verify
that data against the customer database using your tools.

Verification workflow:
1. **UNMISTAKABLY** invoke lookup_customer(reference_number) to find the customer record
2. When the root agent provides a PAN number (read from the card via vision),
   **UNMISTAKABLY** invoke verify_pan(reference_number, pan_number) to check against DB
3. When the root agent provides Aadhaar last 4 digits (told by customer),
   **UNMISTAKABLY** invoke verify_aadhaar_last4(reference_number, aadhaar_last4)
4. When the root agent provides DOB (told by customer),
   **UNMISTAKABLY** invoke verify_dob(reference_number, date_of_birth)
5. When asked to capture PAN card, **UNMISTAKABLY** invoke capture_pan_card
6. When asked to capture profile photo, **UNMISTAKABLY** invoke capture_profile_photo
7. When asked to capture signature, **UNMISTAKABLY** invoke capture_signature
8. When ALL verifications pass (PAN, Aadhaar, DOB, face, signature),
   **UNMISTAKABLY** invoke complete_kyc

Rules:
- Return EXACT verification results — pass or fail with specific details
- If a PAN/Aadhaar/DOB doesn't match, say EXACTLY what doesn't match
- Never reveal the expected values from the database to the customer
- Never share full account numbers or sensitive details
- Do NOT complete KYC unless ALL checks have passed
""",
    tools=[
        lookup_customer,
        verify_pan,
        verify_aadhaar_last4,
        verify_dob,
        capture_pan_card,
        capture_profile_photo,
        capture_signature,
        complete_kyc,
        get_current_date,
    ],
)
