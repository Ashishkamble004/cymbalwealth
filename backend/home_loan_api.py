"""Home Loan Document Verification API.

Architecture:
- Document uploads: Handled locally on Cloud Run → GCS
- Verification: Routed to Vertex AI Agent Engine (multi-agent orchestration)
- Agent Engine ID: projects/769002985772/locations/us-central1/reasoningEngines/5257055913222602752
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/home-loan", tags=["home-loan"])

GCS_BUCKET = os.getenv("GCS_BUCKET", "cymbal-wealth")
AGENT_ENGINE_ID = os.getenv(
    "AGENT_ENGINE_ID",
    "projects/769002985772/locations/us-central1/reasoningEngines/5257055913222602752"
)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "general-ak")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


# --- Models ---

class UploadUrlRequest(BaseModel):
    applicant_pan: str
    documents: list[str]


class UploadUrlResponse(BaseModel):
    application_ref: str
    gcs_folder: str
    upload_urls: dict[str, str]
    expires_in_minutes: int


class VerifyRequest(BaseModel):
    application_ref: str
    applicant_name: str
    applicant_pan: str
    applicant_aadhaar_last4: str
    applicant_dob: str
    loan_amount: str
    property_value: str
    tenure_years: str
    gcs_folder: str
    documents: dict[str, str]


# --- Step 1: Upload URLs (stays on Cloud Run) ---

@router.post("/upload-urls", response_model=UploadUrlResponse)
async def get_upload_urls(request: UploadUrlRequest):
    """Generate direct upload paths for documents."""
    app_ref = f"{request.applicant_pan}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    gcs_folder = f"home-loan/{app_ref}"

    upload_urls = {}
    for doc_name in request.documents:
        upload_urls[doc_name] = f"/api/home-loan/upload-direct/{app_ref}/{doc_name}"

    logger.info(f"[HomeLoan] Upload session: {app_ref} ({len(upload_urls)} docs)")

    return UploadUrlResponse(
        application_ref=app_ref,
        gcs_folder=f"gs://{GCS_BUCKET}/{gcs_folder}",
        upload_urls=upload_urls,
        expires_in_minutes=30,
    )


# --- Step 1b: Direct upload (stays on Cloud Run) ---

@router.post("/upload-direct/{app_ref}/{doc_name}")
async def upload_direct_post(app_ref: str, doc_name: str, file: UploadFile = File(...)):
    """Direct upload — accepts file via POST multipart and stores in GCS."""
    from google.cloud import storage as gcs

    content = await file.read()
    try:
        client = gcs.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob_path = f"home-loan/{app_ref}/{doc_name}"
        ext = os.path.splitext(file.filename)[1] if file.filename else ""
        if ext:
            blob_path += ext
        blob = bucket.blob(blob_path)
        blob.upload_from_string(content, content_type=file.content_type or "application/octet-stream")
        gcs_path = f"gs://{GCS_BUCKET}/{blob_path}"
        logger.info(f"[HomeLoan] Uploaded: {gcs_path} ({len(content)} bytes)")
        return {"status": "uploaded", "gcs_path": gcs_path, "size": len(content)}
    except Exception as e:
        logger.error(f"[HomeLoan] Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Step 2: Verify via Agent Engine ---

@router.post("/verify")
async def verify_documents(request: VerifyRequest):
    """Run multi-agent verification via Vertex AI Agent Engine.

    Reads documents from GCS, builds the prompt, and sends to Agent Engine.
    Traces are visible in Vertex AI Console — no custom logging needed.
    """
    logger.info(f"[HomeLoan] Verify request: {request.applicant_name} | {request.application_ref}")

    # Classify documents: text files get content read, binary files get GCS URI reference
    # Agent Engine's Gemini reads binary files DIRECTLY from GCS via file_data — no downloading needed
    from google.cloud import storage
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(GCS_BUCKET)

    documents = {}
    for doc_name, gcs_path in request.documents.items():
        try:
            blob_path = gcs_path.replace(f"gs://{GCS_BUCKET}/", "")
            blob = bucket.blob(blob_path)
            blob.reload()  # Get metadata without downloading
            content_type = blob.content_type or "application/octet-stream"
            file_size = blob.size or 0

            if content_type.startswith("text/") or blob_path.endswith(".txt"):
                # Text files — read content to embed in prompt
                content = blob.download_as_bytes()
                documents[doc_name] = {
                    "type": "text",
                    "content": content.decode("utf-8"),
                    "size": file_size,
                }
                logger.info(f"[HomeLoan] Text doc: {doc_name} ({file_size} bytes)")
            else:
                # Binary files (PDF, images) — pass GCS URI, Gemini reads directly
                documents[doc_name] = {
                    "type": "binary",
                    "gcs_uri": gcs_path,
                    "content_type": content_type,
                    "size": file_size,
                }
                logger.info(f"[HomeLoan] Binary doc: {doc_name} ({content_type}, {file_size} bytes) — GCS URI passed to Gemini")

        except Exception as e:
            logger.error(f"[HomeLoan] Failed to access {doc_name}: {e}")
            documents[doc_name] = {"type": "error", "error": str(e)}

    if not documents:
        raise HTTPException(status_code=400, detail="No documents could be read from GCS")

    # Build multimodal prompt: text instructions + file_data references for binary docs
    today_str = datetime.utcnow().strftime("%d %B %Y")
    prompt_text = f"""## HOME LOAN VERIFICATION REQUEST

### TODAY'S DATE: {today_str}

### APPLICANT DETAILS
- Name: {request.applicant_name}
- PAN: {request.applicant_pan}
- Aadhaar Last 4: {request.applicant_aadhaar_last4}
- Date of Birth: {request.applicant_dob}
- Requested Loan Amount: Rs {request.loan_amount}
- Property Value: Rs {request.property_value}
- Tenure: {request.tenure_years} years
- Application Ref: {request.application_ref}

### UPLOADED DOCUMENTS ({len(documents)} documents)
"""

    # Build message parts: text prompt first, then file_data for each binary doc
    message_parts = []
    has_binary = False

    for doc_name, doc_data in documents.items():
        if doc_data["type"] == "text":
            content = doc_data["content"]
            if len(content) > 50000:
                logger.warning(f"[HomeLoan] {doc_name} truncated to 50000 chars")
                content = content[:50000] + "\n... [truncated] ..."
            prompt_text += f"\n--- DOCUMENT: {doc_name} (text, {doc_data['size']} bytes) ---\n"
            prompt_text += content + "\n"
        elif doc_data["type"] == "binary":
            prompt_text += f"\n--- DOCUMENT: {doc_name} ({doc_data['content_type']}, {doc_data['size']} bytes) ---\n"
            prompt_text += f"[Binary document attached via file_data below. READ IT FULLY using vision/OCR.]\n"
            has_binary = True
        else:
            prompt_text += f"\n--- DOCUMENT: {doc_name} ---\n[ERROR: {doc_data.get('error', 'unknown')}]\n"

    prompt_text += "\nRun the complete verification pipeline and provide the final report.\n"

    # Assemble the multimodal message
    message_parts.append({"text": prompt_text})

    # Append file_data parts for binary documents — Gemini reads from GCS directly
    for doc_name, doc_data in documents.items():
        if doc_data["type"] == "binary":
            message_parts.append({"text": f"\n[Binary document: {doc_name}]"})
            message_parts.append({
                "file_data": {
                    "mime_type": doc_data["content_type"],
                    "file_uri": doc_data["gcs_uri"],
                }
            })

    if has_binary:
        prompt = {"role": "user", "parts": message_parts}
        logger.info(f"[HomeLoan] Multimodal message: {len(message_parts)} parts (file_data GCS URIs for binary docs)")
    else:
        prompt = prompt_text
        logger.info(f"[HomeLoan] Text-only message ({len(prompt_text)} chars)")

    # Call Agent Engine via Vertex AI Python SDK
    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    try:
        # Get the deployed agent
        remote_agent = agent_engines.get(AGENT_ENGINE_ID)
        logger.info(f"[HomeLoan] Connected to Agent Engine: {AGENT_ENGINE_ID}")

        # Create a session
        user_id = f"homeloan-{request.applicant_pan}"
        session = remote_agent.create_session(user_id=user_id)
        session_id = session.get("id") if isinstance(session, dict) else getattr(session, "id", str(session))
        logger.info(f"[HomeLoan] Session created: {session_id}")

        # Stream query to the agent
        results = []
        for event in remote_agent.stream_query(
            user_id=user_id,
            session_id=session_id,
            message=prompt,
        ):
            # Extract author and text from each event
            author = getattr(event, "author", None) or "orchestrator"

            # Check for content.parts
            content = getattr(event, "content", None)
            if content and hasattr(content, "parts"):
                for part in content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        results.append({
                            "agent": author,
                            "text": text,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        logger.info(f"[HomeLoan] [{author}] {text[:200]}")

            # Check for actions (function calls = agent handoffs)
            actions = getattr(event, "actions", None)
            if actions:
                fc_list = getattr(actions, "function_calls", None)
                if fc_list:
                    for fc in fc_list:
                        results.append({
                            "agent": author,
                            "type": "agent_handoff",
                            "target_agent": getattr(fc, "name", "unknown"),
                            "timestamp": datetime.utcnow().isoformat(),
                        })

        logger.info(f"[HomeLoan] Collected {len(results)} events from Agent Engine")

        # Store verification report in GCS
        try:
            report_blob = bucket.blob(f"home-loan/{request.application_ref}/verification_report.json")
            report_data = json.dumps({
                "applicant": request.applicant_name,
                "pan": request.applicant_pan,
                "application_ref": request.application_ref,
                "agent_engine_id": AGENT_ENGINE_ID,
                "documents_verified": len(documents),
                "results": results,
                "timestamp": datetime.utcnow().isoformat(),
            }, indent=2)
            report_blob.upload_from_string(report_data, content_type="application/json")
            logger.info(f"[HomeLoan] Report stored in GCS")
        except Exception as e:
            logger.error(f"[HomeLoan] Failed to store report: {e}")

        return {
            "status": "completed",
            "applicant": request.applicant_name,
            "application_ref": request.application_ref,
            "gcs_folder": f"gs://{GCS_BUCKET}/home-loan/{request.application_ref}",
            "documents_processed": len(documents),
            "agent_engine_id": AGENT_ENGINE_ID,
            "verification_results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"[HomeLoan] Agent Engine error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent Engine error: {str(e)}")


@router.get("/health")
async def home_loan_health():
    return {
        "status": "ok",
        "service": "home-loan-verification",
        "agent_engine": AGENT_ENGINE_ID,
        "mode": "agent-engine",
    }
