"""Customer Support Agent — STT + RAG-grounded LLM streaming via WebSocket."""

import asyncio
import concurrent.futures
import json
import logging
import time

from fastapi import WebSocket, WebSocketDisconnect
from google.cloud.speech_v2 import SpeechAsyncClient
from google.cloud.speech_v2.types import cloud_speech as speech_types
from google.api_core.client_options import ClientOptions
from google import genai
from google.genai import types

from .compliance import ComplianceMonitor
from .config import settings

logger = logging.getLogger(__name__)

_SAFETY_OFF = [
    types.SafetySetting(category=c, threshold="OFF")
    for c in [
        "HARM_CATEGORY_DANGEROUS_CONTENT",
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    ]
]

_SYSTEM_INSTRUCTION = (
    "You are an AI assistant helping a bank customer service agent. "
    "Provide concise, accurate suggestions based on the customer's query. "
    "Focus on being helpful, accurate, and compliant with banking regulations."
)


class StreamingSTTManager:
    """Manages a Google Cloud Speech-to-Text v2 streaming session in a background thread.

    Audio bytes are pushed via `feed()`.  Transcription callbacks are posted back
    to the caller's asyncio event loop via `asyncio.run_coroutine_threadsafe`.
    The stream restarts automatically on error with a 1-second backoff.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        on_transcript,  # async callable(text: str, is_final: bool)
        stt_language: str = "auto",
    ):
        self._loop = loop
        self._on_transcript = on_transcript

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="stt")
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

        # Build once — reused across stream restarts
        raw_lang = stt_language or "auto"
        language_codes = ["auto"] if raw_lang == "auto" else [lc.strip() for lc in raw_lang.split(",") if lc.strip()]

        recognition_config = speech_types.RecognitionConfig(
            explicit_decoding_config=speech_types.ExplicitDecodingConfig(
                encoding=speech_types.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                audio_channel_count=1,
            ),
            language_codes=language_codes,
            model=settings.stt_model,
        )
        self._config_request = speech_types.StreamingRecognizeRequest(
            recognizer=f"projects/{settings.gcp_project_id}/locations/{settings.stt_location}/recognizers/_",
            streaming_config=speech_types.StreamingRecognitionConfig(
                config=recognition_config,
                streaming_features=speech_types.StreamingRecognitionFeatures(
                    interim_results=True,
                ),
            ),
        )
        # Single client — gRPC connection is reused across restarts
        self._speech_client = SpeechAsyncClient(
            client_options=ClientOptions(api_endpoint="us-speech.googleapis.com")
        )

    def start(self):
        self._running = True
        self._task = asyncio.ensure_future(self._manager_loop())

    async def stop(self):
        self._running = False
        await self._audio_queue.put(None)  # sentinel to unblock reader
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._executor.shutdown(wait=False)

    async def feed(self, audio_bytes: bytes):
        await self._audio_queue.put(audio_bytes)

    async def _manager_loop(self):
        while self._running:
            try:
                await asyncio.get_running_loop().run_in_executor(
                    self._executor, self._run_blocking_stream
                )
            except Exception as exc:
                if not self._running:
                    break
                logger.warning("STT stream error, restarting in 1 s: %s", exc)
                await asyncio.sleep(1)

    def _run_blocking_stream(self):
        """Blocking gRPC streaming call — runs in the ThreadPoolExecutor thread."""
        def audio_generator():
            yield self._config_request
            while self._running:
                # Bridge asyncio queue into this blocking thread via run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(
                    self._audio_queue.get(), self._loop
                )
                try:
                    chunk = future.result(timeout=5)
                except concurrent.futures.TimeoutError:
                    continue
                if chunk is None:
                    return
                yield speech_types.StreamingRecognizeRequest(audio=chunk)

        # SpeechAsyncClient wraps a sync transport; access it directly for blocking iteration
        responses = self._speech_client._client.streaming_recognize(audio_generator())  # type: ignore[attr-defined]
        for response in responses:
            if not self._running:
                break
            for result in response.results:
                if not result.alternatives:
                    continue
                asyncio.run_coroutine_threadsafe(
                    self._on_transcript(result.alternatives[0].transcript, result.is_final),
                    self._loop,
                )


async def process_with_rag_llm(
    websocket: WebSocket,
    chat,
    transcript: str,
):
    """Send transcript to the RAG-grounded chat and stream back chunks."""
    start = time.monotonic()
    first_chunk_time: float | None = None

    try:
        await websocket.send_text(json.dumps({"type": "stream_start"}))

        # Stream response — the google-genai aio chat returns an async iterator
        async for chunk in await chat.send_message_stream(transcript):
            if chunk.text:
                if first_chunk_time is None:
                    first_chunk_time = time.monotonic()
                await websocket.send_text(
                    json.dumps({"type": "stream_chunk", "text": chunk.text})
                )

        total = time.monotonic() - start
        ttfc = (first_chunk_time - start) if first_chunk_time is not None else total
        await websocket.send_text(
            json.dumps({"type": "stream_end", "ttfc": round(ttfc, 3), "total_time": round(total, 3)})
        )
    except asyncio.CancelledError:
        pass  # Cancelled because a new transcript arrived
    except Exception as exc:
        logger.error("LLM streaming error: %s", exc)
        await websocket.send_text(
            json.dumps({"type": "error", "message": str(exc)})
        )


async def run_agent(
    websocket: WebSocket,
    stt_language: str = "auto",
    llm_model: str = "gemini-2.5-flash",
):
    """Main WebSocket handler — wires STT → LLM → compliance pipeline."""
    await websocket.accept()

    loop = asyncio.get_running_loop()
    model = llm_model or settings.llm_model

    client = genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )

    rag_tool = types.Tool(
        retrieval=types.Retrieval(
            vertex_rag_store=types.VertexRagStore(
                rag_resources=[
                    types.VertexRagStoreRagResource(rag_corpus=settings.rag_corpus_resource_name)
                ],
                similarity_top_k=5,
            )
        )
    )

    chat = client.aio.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            tools=[rag_tool],
            system_instruction=_SYSTEM_INSTRUCTION,
            safety_settings=_SAFETY_OFF,
        ),
    )

    compliance = ComplianceMonitor(client, model)
    pending_llm_task: asyncio.Task | None = None

    async def on_transcript(text: str, is_final: bool):
        nonlocal pending_llm_task
        await websocket.send_text(
            json.dumps({"type": "transcript", "text": text, "is_final": is_final})
        )
        if is_final:
            if pending_llm_task and not pending_llm_task.done():
                pending_llm_task.cancel()
            pending_llm_task = asyncio.ensure_future(
                process_with_rag_llm(websocket, chat, text)
            )
            asyncio.ensure_future(_send_compliance(text))

    async def _send_compliance(text: str):
        result = await compliance.analyze(text)
        if result:
            await websocket.send_text(
                json.dumps({"type": "compliance_result", **result})
            )

    stt = StreamingSTTManager(loop, on_transcript, stt_language=stt_language)
    stt.start()

    try:
        while True:
            data = await websocket.receive_bytes()
            await stt.feed(data)
    except WebSocketDisconnect:
        logger.info("Customer support WebSocket disconnected")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": str(exc)})
            )
        except Exception:
            pass
    finally:
        await stt.stop()
        if pending_llm_task and not pending_llm_task.done():
            pending_llm_task.cancel()
