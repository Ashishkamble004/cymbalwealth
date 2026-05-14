"""Cymbal Wealth -- Video KYC Backend Server.

FastAPI application with WebSocket endpoint for real-time Video KYC
using google-genai SDK with Gemini Live bidirectional streaming.
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

# Load env BEFORE importing other modules
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.genai import types

from gemini_client import gemini_manager
from kyc_agent import TOOLS_MAP
from tool_executor import ToolExecutor
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
# from compliance_agent.router import router as compliance_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # Activate telemetry inside the event loop so dashboard creation and
    # JSON periodic flush work correctly (requires a running asyncio loop).
    try:
        from gemini_live_telemetry import activate, InstrumentationConfig
        activate(InstrumentationConfig(
            project_id="general-ak",
            enable_dashboard=True,
            enable_json_export=True,
            enable_gcp_export=True,
        ))
        logger.info("gemini-live-telemetry activated successfully")
    except ImportError:
        logger.warning("gemini-live-telemetry not installed, skipping instrumentation")
    except Exception as exc:
        logger.warning(f"Telemetry activation failed: {exc}")
    yield

app = FastAPI(title="Cymbal Wealth Video KYC", version="1.0.0", lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "https://cymbalwealth.ak-demos.com,https://kyc-frontend-mcj3w7ujpq-uc.a.run.app").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customer_support_router, prefix="/customer-support")
app.include_router(compliance_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cymbal-wealth-kyc-backend"}


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """WebSocket endpoint for Video KYC sessions."""
    await websocket.accept()
    logger.info(f"[WS] Connected: user={user_id}, session={session_id}")

    # Initialize genai client and config
    client = gemini_manager.client
    config = gemini_manager.get_live_config()
    model_id = gemini_manager.model
    tool_executor = ToolExecutor(tools_map=TOOLS_MAP)

    transcript: list[dict] = []
    reference_number = None

    # Buffers for recording
    input_audio_chunks: list[bytes] = []   # User audio (16kHz PCM)
    output_audio_chunks: list[bytes] = []  # Agent audio (24kHz PCM)
    video_frames: list[bytes] = []         # JPEG frames

    MAX_VIDEO_FRAMES = 1800  # ~30 min at 1 fps; prevents OOM on long sessions

    try:
        async with client.aio.live.connect(model=model_id, config=config) as session:
            tool_executor.session = session
            session_handle = None

            async def send_to_gemini():
                """Route client WebSocket messages to the Gemini Live session."""
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
                                input_audio_chunks.append(audio_bytes)
                                if len(input_audio_chunks) % 50 == 1:
                                    logger.info(f"[WS] Audio chunk #{len(input_audio_chunks)}: {len(audio_bytes)} bytes")
                                await session.send_realtime_input(
                                    audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                                )

                        elif msg_type == "video":
                            video_data = data.get("data", "")
                            if video_data:
                                image_bytes = base64.b64decode(video_data)
                                if len(video_frames) < MAX_VIDEO_FRAMES:
                                    video_frames.append(image_bytes)
                                await set_latest_frame(session_id, image_bytes)
                                await session.send_realtime_input(
                                    video=types.Blob(data=image_bytes, mime_type="image/jpeg")
                                )

                        elif msg_type == "text":
                            text = data.get("data", "")
                            if text:
                                transcript.append({"role": "user", "text": text, "ts": datetime.now(timezone.utc).isoformat()})
                                await session.send_client_content(
                                    turns=types.Content(role="user", parts=[types.Part(text=text)])
                                )

                        elif msg_type == "context":
                            reference_number = data.get("reference_number", "")
                            session_fname = get_session_filename(reference_number, session_id)
                            await set_session_filename(session_id, session_fname)
                            context_text = (
                                f"The customer reference number is {reference_number}. "
                                f"The session ID is {session_id}. "
                                f"Use this to look up the customer in the database. "
                                f"Begin the Video KYC process now."
                            )
                            await session.send_client_content(
                                turns=types.Content(role="user", parts=[types.Part(text=context_text)])
                            )

                        elif msg_type == "end_session":
                            logger.info(f"[WS] Client ended session: {session_id}")
                            break

                        elif msg_type == "ping":
                            await websocket.send_text(json.dumps({"type": "pong"}))

                except WebSocketDisconnect:
                    logger.info(f"[WS] Client disconnected: {session_id}")
                except Exception as e:
                    logger.error(f"[WS] Upstream error: {e}")
                    traceback.print_exc()

            _ws_closed = False

            async def safe_send(data: str):
                """Send text to the client WebSocket, ignoring errors if already closed."""
                nonlocal _ws_closed
                if _ws_closed:
                    return
                try:
                    await websocket.send_text(data)
                except Exception:
                    _ws_closed = True

            async def receive_from_gemini():
                """Route Gemini Live session events back to the client WebSocket."""
                nonlocal session_handle
                try:
                    while True:
                        async for message in session.receive():
                            if message.session_resumption_update:
                                update = message.session_resumption_update
                                if update.resumable and update.new_handle:
                                    session_handle = update.new_handle

                            if message.data is not None:
                                output_audio_chunks.append(message.data)
                                audio_base64 = base64.b64encode(message.data).decode("ascii")
                                await safe_send(json.dumps({
                                    "type": "audio",
                                    "data": audio_base64,
                                    "mime_type": "audio/pcm;rate=24000",
                                }))

                            if message.server_content:
                                sc = message.server_content

                                if sc.interrupted:
                                    await safe_send(json.dumps({
                                        "type": "interrupted",
                                        "data": "Response interrupted by user input"
                                    }))

                                if sc.turn_complete:
                                    await safe_send(json.dumps({"type": "turn_complete"}))

                                if sc.input_transcription and sc.input_transcription.text:
                                    finished = bool(sc.input_transcription.finished)
                                    await safe_send(json.dumps({
                                        "type": "input_transcription",
                                        "text": sc.input_transcription.text,
                                        "finished": finished,
                                    }))
                                    if finished:
                                        transcript.append({
                                            "role": "user", "text": sc.input_transcription.text,
                                            "ts": datetime.now(timezone.utc).isoformat(), "source": "transcription",
                                        })

                                if sc.output_transcription and sc.output_transcription.text:
                                    finished = bool(sc.output_transcription.finished)
                                    await safe_send(json.dumps({
                                        "type": "output_transcription",
                                        "text": sc.output_transcription.text,
                                        "finished": finished,
                                    }))
                                    if finished:
                                        transcript.append({
                                            "role": "agent", "text": sc.output_transcription.text,
                                            "ts": datetime.now(timezone.utc).isoformat(), "source": "transcription",
                                        })

                                if sc.model_turn and sc.model_turn.parts:
                                    for part in sc.model_turn.parts:
                                        if part.text:
                                            transcript.append({
                                                "role": "agent", "text": part.text,
                                                "ts": datetime.now(timezone.utc).isoformat(),
                                            })
                                            await safe_send(json.dumps({
                                                "type": "transcript",
                                                "role": "model",
                                                "text": part.text,
                                            }))

                            if message.tool_call:
                                await tool_executor.handle_tool_call(message.tool_call)

                        await asyncio.sleep(0.01)

                except asyncio.CancelledError:
                    logger.info(f"[WS] Receive task cancelled: {session_id}")
                except Exception as e:
                    logger.error(f"[WS] Downstream error: {e}")
                    traceback.print_exc()

            send_task = asyncio.create_task(send_to_gemini())
            recv_task = asyncio.create_task(receive_from_gemini())
            done, pending = await asyncio.wait(
                [send_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        logger.error(f"[WS] Session error: {e}")
        traceback.print_exc()
    finally:
        # Save session data to GCS
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
