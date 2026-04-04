"""Home Loan Document Verification API.

Architecture:
- Document uploads: Handled locally on Cloud Run → GCS
- Verification: Routed to Vertex AI Agent Engine (multi-agent orchestration)
- Agent Engine ID: projects/769002985772/locations/us-central1/reasoningEngines/5257055913222602752
"""

import asyncio
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import vertexai
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from vertexai import agent_engines

logger = logging.getLogger(__name__)

try:
    import google.cloud.logging as gcloud_logging
    _gcloud_log_client = gcloud_logging.Client()
    _hl_logger = _gcloud_log_client.logger("cymbal-homeloan-verification")
except Exception:
    _hl_logger = None


def _log_loan_verification(application_ref: str, applicant_name: str,
                           applicant_pan: str, total_tokens: int,
                           duration_seconds: float, results: list,
                           documents_processed: int) -> None:
    """Write structured home loan verification result to Cloud Logging → BigQuery."""
    if not _hl_logger:
        return
    full_text = " ".join(r.get("text", "") for r in results).lower()
    has_fail  = any(k in full_text for k in ["fail", "reject", "duplicate", "mismatch"])
    status    = "issues_found" if has_fail else "approved"
    try:
        _hl_logger.log_struct({
            "application_ref":      application_ref,
            "applicant_name":       applicant_name,
            "applicant_pan":        applicant_pan,
            "agent_engine_id":      AGENT_ENGINE_ID,
            "documents_processed":  documents_processed,
            "verification_status":  status,
            "total_tokens":         total_tokens,
            "duration_seconds":     round(duration_seconds, 1),
        }, severity="INFO")
    except Exception as exc:
        logger.warning(f"[HomeLoan] Failed to write verification log: {exc}")

router = APIRouter(prefix="/api/home-loan", tags=["home-loan"])

GCS_BUCKET = os.getenv("GCS_BUCKET", "cymbal-wealth")
AGENT_ENGINE_ID = os.getenv(
    "AGENT_ENGINE_ID",
    "projects/769002985772/locations/us-central1/reasoningEngines/5257055913222602752"
)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "general-ak")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


# ---------------------------------------------------------------------------
# Agent Engine session pool
# ---------------------------------------------------------------------------
# Agent Engine sessions take ~6s to create. This pool pre-warms a fixed number
# of sessions at startup so every incoming verify request starts immediately.
# After consuming a session the pool refills itself in the background.
# ---------------------------------------------------------------------------

class _AgentSessionPool:
    """Pre-warms Vertex AI Agent Engine sessions to eliminate per-request latency."""

    POOL_SIZE = 3  # number of sessions to keep ready

    def __init__(self):
        self._lock = threading.Lock()
        self._agent = None          # cached agent_engines handle
        self._queue: asyncio.Queue | None = None

    # -- internals (run in thread-pool executor) ----------------------------

    def _init_agent(self):
        """Cache the agent handle. Called once from a thread."""
        with self._lock:
            if self._agent is None:
                vertexai.init(project=PROJECT_ID, location=LOCATION)
                self._agent = agent_engines.get(AGENT_ENGINE_ID)
                logger.info("[Pool] Agent Engine handle cached")
        return self._agent

    def _create_session_sync(self) -> tuple[str, str]:
        """Create one session synchronously and return (session_id, user_id)."""
        agent = self._init_agent()
        uid = f"pool-{uuid.uuid4().hex[:8]}"
        session = agent.create_session(user_id=uid)
        sid = (
            session.get("id") if isinstance(session, dict)
            else getattr(session, "id", str(session))
        )
        return sid, uid

    # -- async interface ----------------------------------------------------

    async def warmup(self):
        """Pre-create POOL_SIZE sessions concurrently. Called once on startup."""
        self._queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        async def _one(idx):
            try:
                sid, uid = await loop.run_in_executor(None, self._create_session_sync)
                await self._queue.put((sid, uid))
                logger.info(f"[Pool] Slot {idx} ready — session {sid}")
            except Exception as exc:
                logger.warning(f"[Pool] Warmup slot {idx} failed: {exc}")

        await asyncio.gather(*[_one(i) for i in range(self.POOL_SIZE)])
        logger.info(f"[Pool] Warmup complete — {self._queue.qsize()} sessions ready")

    async def acquire(self) -> tuple[object, str, str]:
        """Return (agent, session_id, user_id). Instant if pool has a session."""
        if self._queue is None or self._queue.empty():
            logger.info("[Pool] Empty — creating session on-demand")
            loop = asyncio.get_event_loop()
            sid, uid = await loop.run_in_executor(None, self._create_session_sync)
        else:
            sid, uid = self._queue.get_nowait()
            logger.info(f"[Pool] Issued pre-warmed session {sid} — {self._queue.qsize()} remaining")

        # Replenish the consumed slot in the background
        asyncio.create_task(self._refill())
        return self._agent, sid, uid

    async def _refill(self):
        """Add one new session back to the pool."""
        try:
            loop = asyncio.get_event_loop()
            sid, uid = await loop.run_in_executor(None, self._create_session_sync)
            await self._queue.put((sid, uid))
            logger.info(f"[Pool] Refilled — session {sid} | pool size {self._queue.qsize()}")
        except Exception as exc:
            logger.warning(f"[Pool] Refill failed: {exc}")

    def acquire_sync(self, loop: asyncio.AbstractEventLoop) -> tuple[object, str, str]:
        """Blocking wrapper for use inside worker threads."""
        future = asyncio.run_coroutine_threadsafe(self.acquire(), loop)
        return future.result(timeout=30)


_pool = _AgentSessionPool()




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
    app_ref = f"{request.applicant_pan}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
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
    today_str = datetime.now(timezone.utc).strftime("%d %B %Y")
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
        # Agent Engine stream_query accepts the parts list directly or as a Content dict.
        # Using the parts list directly avoids SDK version inconsistencies with role wrapping.
        prompt = {"role": "user", "parts": message_parts}
        logger.info(f"[HomeLoan] Multimodal message: {len(message_parts)} parts (file_data GCS URIs for binary docs)")
    else:
        prompt = prompt_text
        logger.info(f"[HomeLoan] Text-only message ({len(prompt_text)} chars)")

    # Stream results from Agent Engine via NDJSON (fixes event parsing + gives real-time UI feedback)
    async def _generate():
        yield json.dumps({"type": "status", "message": f"Loaded {len(documents)} docs | Connecting to Agent Engine..."}) + "\n"

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        results: list = []

        def _parse_event(event):
            """Return (author, text) from Agent Engine event.

            Agent Engine SDK may return events as plain dicts (REST transport) or
            as ADK Event objects (gRPC transport). Handle both.
            """
            if isinstance(event, dict):
                author = event.get("author") or "orchestrator"
                raw = event.get("content") or {}
                parts = raw.get("parts", []) if isinstance(raw, dict) else (getattr(raw, "parts", None) or [])
                for part in parts:
                    text = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
                    if text:
                        return author, text
            else:
                author = getattr(event, "author", None) or "orchestrator"
                content = getattr(event, "content", None)
                if content:
                    for part in (getattr(content, "parts", None) or []):
                        text = getattr(part, "text", None)
                        if text:
                            return author, text
            return None, None

        def _run_agent():
            try:
                # Acquire a pre-warmed session from the pool (usually instant)
                # IMPORTANT: use the pool's uid in stream_query — session belongs to that uid
                remote_agent, session_id, pool_uid = _pool.acquire_sync(loop)
                # Use pool_uid — session was created under this user_id, must match for stream_query
                logger.info(f"[HomeLoan] Using session: {session_id} (uid: {pool_uid})")
                loop.call_soon_threadsafe(queue.put_nowait, {
                    "type": "status",
                    "message": "Agent Engine session ready | Running verification pipeline..."
                })

                for raw_event in remote_agent.stream_query(
                    user_id=pool_uid, session_id=session_id, message=prompt
                ):
                    author, text = _parse_event(raw_event)
                    if text:
                        ts = datetime.now(timezone.utc).isoformat()
                        entry = {"agent": author, "text": text, "timestamp": ts}
                        results.append(entry)
                        logger.info(f"[HomeLoan] [{author}] {text[:150]}")
                        loop.call_soon_threadsafe(
                            queue.put_nowait, {"type": "agent_result", **entry}
                        )

                loop.call_soon_threadsafe(queue.put_nowait, {"type": "_done"})
            except Exception as exc:
                logger.error(f"[HomeLoan] Agent thread error: {exc}")
                loop.call_soon_threadsafe(
                    queue.put_nowait, {"type": "error", "message": str(exc)}
                )

        t = threading.Thread(target=_run_agent, daemon=True)
        t.start()

        # Yield events to the client as they arrive from the agent thread
        while True:
            item = await queue.get()
            if item["type"] == "_done":
                break
            yield json.dumps(item) + "\n"
            if item["type"] == "error":
                break

        t.join(timeout=10)

        # Save verification report to GCS
        # Log verification summary to Cloud Logging → BigQuery
        total_tok = sum(int(r.get("total_tokens", 0)) for r in results if isinstance(r, dict) and "total_tokens" in r)
        _log_loan_verification(
            application_ref=request.application_ref,
            applicant_name=request.applicant_name,
            applicant_pan=request.applicant_pan,
            total_tokens=total_tok,
            duration_seconds=0,  # timing not tracked here; use Cloud Trace for that
            results=results,
            documents_processed=len(documents),
        )

        try:
            report_blob = bucket.blob(f"home-loan/{request.application_ref}/verification_report.json")
            report_blob.upload_from_string(
                json.dumps({
                    "applicant": request.applicant_name,
                    "pan": request.applicant_pan,
                    "application_ref": request.application_ref,
                    "agent_engine_id": AGENT_ENGINE_ID,
                    "documents_verified": len(documents),
                    "results": results,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, indent=2),
                content_type="application/json",
            )
            logger.info(f"[HomeLoan] Report saved to GCS")
        except Exception as exc:
            logger.warning(f"[HomeLoan] GCS report save failed: {exc}")

        # Final summary event
        yield json.dumps({
            "type": "complete",
            "status": "completed",
            "applicant": request.applicant_name,
            "application_ref": request.application_ref,
            "gcs_folder": f"gs://{GCS_BUCKET}/home-loan/{request.application_ref}",
            "documents_processed": len(documents),
            "agent_engine_id": AGENT_ENGINE_ID,
            "verification_results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }) + "\n"

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


@router.get("/health")
async def home_loan_health():
    return {
        "status": "ok",
        "service": "home-loan-verification",
        "agent_engine": AGENT_ENGINE_ID,
        "mode": "agent-engine",
    }
