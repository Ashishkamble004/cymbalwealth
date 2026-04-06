"""Cymbal Wealth — Video KYC Backend Server.

FastAPI application with WebSocket endpoint for real-time Video KYC
using Google ADK with Gemini Live bidirectional streaming.
"""

import asyncio
import base64
import json
import logging
import os
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load env BEFORE importing agent
load_dotenv(Path(__file__).parent / ".env")

# Set Vertex AI environment variables for ADK
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "general-ak"))
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_REGION", "us-central1"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
# Note: InMemorySessionService is used intentionally for this deployment.
# KYC sessions are short-lived (5-10 min) and Cloud Run is configured with
# min-instances=1 + session-affinity, ensuring sessions persist during a call.
# For horizontal scaling, replace with DatabaseSessionService backed by Cloud SQL.
from google.genai import types

from kyc_agent import agent as kyc_agent
from storage_utils import (
    get_session_filename,
    save_transcript,
    save_audio_recording,
    save_video_recording,
)
from session_frames import (
    set_latest_frame,
    set_session_filename,
    clear_session,
)
from customer_support.router import router as customer_support_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

APP_NAME = "cymbal-wealth-kyc-app"

app = FastAPI(title="Cymbal Wealth Video KYC", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "https://cymbalwealth.ak-demos.com,https://kyc-frontend-mcj3w7ujpq-uc.a.run.app").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=kyc_agent,
    session_service=session_service,
)


app.include_router(customer_support_router, prefix="/customer-support")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cymbal-wealth-kyc-backend"}


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """WebSocket endpoint for Video KYC sessions."""
    await websocket.accept()
    logger.info(f"[WS] Connected: user={user_id}, session={session_id}")

    live_request_queue = LiveRequestQueue()
    transcript: list[dict] = []
    reference_number = None

    # Buffers for recording
    input_audio_chunks: list[bytes] = []   # User audio (16kHz PCM)
    output_audio_chunks: list[bytes] = []  # Agent audio (24kHz PCM)
    video_frames: list[bytes] = []         # JPEG frames

    MAX_VIDEO_FRAMES = 1800  # ~30 min at 1 fps; prevents OOM on long sessions

    # Ensure session exists
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    async def upstream_task():
        """Route client messages into the ADK LiveRequestQueue."""
        nonlocal reference_number
        try:
            while True:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                msg_type = data.get("type", "")

                if msg_type == "audio":
                    audio_data = data.get("data", "")
                    if audio_data:
                        audio_bytes = base64.b64decode(audio_data)
                        # Buffer for recording
                        input_audio_chunks.append(audio_bytes)
                        audio_blob = types.Blob(
                            mime_type="audio/pcm;rate=16000",
                            data=audio_bytes,
                        )
                        live_request_queue.send_realtime(audio_blob)

                elif msg_type == "video":
                    video_data = data.get("data", "")
                    if video_data:
                        image_bytes = base64.b64decode(video_data)
                        # Buffer for recording and store latest frame for captures
                        if len(video_frames) < MAX_VIDEO_FRAMES:
                            video_frames.append(image_bytes)
                        await set_latest_frame(session_id, image_bytes)
                        image_blob = types.Blob(
                            mime_type="image/jpeg",
                            data=image_bytes,
                        )
                        live_request_queue.send_realtime(image_blob)

                elif msg_type == "text":
                    text = data.get("data", "")
                    if text:
                        transcript.append({"role": "user", "text": text, "ts": datetime.now(timezone.utc).isoformat()})
                        live_request_queue.send_content(
                            types.Content(
                                parts=[types.Part(text=text)],
                            )
                        )

                elif msg_type == "context":
                    reference_number = data.get("reference_number", "")
                    # Generate consistent session filename and store it
                    session_fname = get_session_filename(reference_number, session_id)
                    await set_session_filename(session_id, session_fname)

                    context_text = (
                        f"The customer reference number is {reference_number}. "
                        f"The session ID is {session_id}. "
                        f"Use this to look up the customer in the database. "
                        f"Begin the Video KYC process now."
                    )
                    live_request_queue.send_content(
                        types.Content(
                            parts=[types.Part(text=context_text)],
                        )
                    )

                elif msg_type == "end_session":
                    logger.info(f"[WS] Client ended session: {session_id}")
                    live_request_queue.close()
                    break

                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

        except WebSocketDisconnect:
            logger.info(f"[WS] Client disconnected: {session_id}")
            live_request_queue.close()
        except Exception as e:
            logger.error(f"[WS] Upstream error: {e}")
            traceback.print_exc()
            live_request_queue.close()

    async def downstream_task():
        """Route ADK agent events back to the client."""
        try:
            run_config = RunConfig(
                streaming_mode=StreamingMode.BIDI,
                response_modalities=["AUDIO"],
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
                session_resumption=types.SessionResumptionConfig(
                    transparent=True,
                ),
                context_window_compression=types.ContextWindowCompressionConfig(
                    trigger_tokens=64000,
                    sliding_window=types.SlidingWindow(
                        target_tokens=32000,
                    ),
                ),
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Charon"
                        )
                    )
                ),
            )

            interrupted = False

            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # Handle interruptions
                if hasattr(event, "interrupted") and getattr(event, "interrupted", False):
                    if not interrupted:
                        interrupted = True
                        logger.info("🤐 INTERRUPTION DETECTED")
                        await websocket.send_text(
                            json.dumps({
                                "type": "interrupted",
                                "data": "Response interrupted by user input"
                            })
                        )

                # Handle turn completion
                if hasattr(event, "turn_complete") and getattr(event, "turn_complete", False):
                    interrupted = False
                    await websocket.send_text(
                        json.dumps({
                            "type": "turn_complete",
                        })
                    )

                # Handle input transcription
                if event.input_transcription:
                    if event.input_transcription.text:
                        finished = bool(event.input_transcription.finished)
                        logger.debug(f"[WS] input_transcription finished={finished} text={event.input_transcription.text[:60]!r}")
                        await websocket.send_text(
                            json.dumps({
                                "type": "input_transcription",
                                "text": event.input_transcription.text,
                                "finished": finished,
                            })
                        )
                        if finished:
                            transcript.append({
                                "role": "user",
                                "text": event.input_transcription.text,
                                "ts": datetime.now(timezone.utc).isoformat(),
                                "source": "transcription",
                            })

                # Handle output transcription
                if event.output_transcription:
                    if event.output_transcription.text:
                        finished = bool(event.output_transcription.finished)
                        logger.debug(f"[WS] output_transcription finished={finished} text={event.output_transcription.text[:60]!r}")
                        await websocket.send_text(
                            json.dumps({
                                "type": "output_transcription",
                                "text": event.output_transcription.text,
                                "finished": finished,
                            })
                        )
                        if finished:
                            transcript.append({
                                "role": "agent",
                                "text": event.output_transcription.text,
                                "ts": datetime.now(timezone.utc).isoformat(),
                                "source": "transcription",
                            })

                # Handle audio content from agent
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.inline_data and part.inline_data.data:
                            mime_type = part.inline_data.mime_type or ""
                            if "audio" in mime_type and isinstance(part.inline_data.data, bytes):
                                # Buffer agent audio for recording
                                output_audio_chunks.append(part.inline_data.data)
                                audio_base64 = base64.b64encode(part.inline_data.data).decode("ascii")
                                await websocket.send_text(
                                    json.dumps({
                                        "type": "audio",
                                        "data": audio_base64,
                                        "mime_type": mime_type,
                                    })
                                )
                        elif part.text:
                            transcript.append({
                                "role": "agent",
                                "text": part.text,
                                "ts": datetime.now(timezone.utc).isoformat(),
                            })
                            await websocket.send_text(
                                json.dumps({
                                    "type": "transcript",
                                    "role": event.content.role or "model",
                                    "text": part.text,
                                })
                            )

        except Exception as e:
            logger.error(f"[WS] Downstream error: {e}")
            traceback.print_exc()

    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except Exception as e:
        logger.error(f"[WS] Session error: {e}")
        traceback.print_exc()
    finally:
        live_request_queue.close()

        # Save all session data to GCS
        if reference_number:
            from session_frames import get_session_filename as get_fname
            session_fname = await get_fname(session_id) or get_session_filename(reference_number, session_id)

            # Save transcript
            if transcript:
                try:
                    save_transcript(reference_number, session_id, session_fname, transcript, user_id)
                except Exception as e:
                    logger.error(f"[WS] Failed to save transcript: {e}")

            # Save audio recording (both user and agent)
            if input_audio_chunks or output_audio_chunks:
                try:
                    save_audio_recording(session_fname, input_audio_chunks, output_audio_chunks,
                                         input_sample_rate=16000, output_sample_rate=24000)
                except Exception as e:
                    logger.error(f"[WS] Failed to save audio recording: {e}")

            # Save video as stitched AVI
            if video_frames:
                try:
                    save_video_recording(session_fname, video_frames, fps=1.0)
                except Exception as e:
                    logger.error(f"[WS] Failed to save video recording: {e}")


        # Clean up shared state
        await clear_session(session_id)
        logger.info(f"[WS] Session ended: user={user_id}, session={session_id}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
