"""Cymbal Wealth — Gemini Live API Client Manager (genai-sdk).

Manages the genai.Client for AI Studio and provides LiveConnectConfig
for real-time voice/video KYC sessions via the Gemini Live API.

Fetches the API key from GCP Secret Manager, falling back to the
GEMINI_API_KEY environment variable.
"""

import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiClientManager:
    """Singleton-style manager for the genai.Client and LiveConnectConfig."""

    def __init__(self):
        self._client: genai.Client | None = None
        self._api_key: str | None = None
        self._model: str | None = None

    # ------------------------------------------------------------------
    # API key resolution
    # ------------------------------------------------------------------

    def _fetch_api_key(self) -> str:
        """Fetch API key from Secret Manager, fall back to env var."""
        # 1. Try GCP Secret Manager
        try:
            from google.cloud import secretmanager

            sm_client = secretmanager.SecretManagerServiceClient()
            secret_name = "projects/general-ak/secrets/gemini-api-key/versions/latest"
            response = sm_client.access_secret_version(request={"name": secret_name})
            key = response.payload.data.decode("UTF-8").strip()
            if key:
                logger.info("API key loaded from Secret Manager")
                return key
        except Exception as exc:
            logger.warning("Secret Manager unavailable, falling back to env var: %s", exc)

        # 2. Fallback to environment variable
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if key:
            logger.info("API key loaded from GEMINI_API_KEY env var")
            return key

        raise RuntimeError(
            "No Gemini API key found. Set GEMINI_API_KEY or configure "
            "projects/general-ak/secrets/gemini-api-key in Secret Manager."
        )

    # ------------------------------------------------------------------
    # Client & model
    # ------------------------------------------------------------------

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            self._api_key = self._fetch_api_key()
        return self._api_key

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                api_key=self.api_key,
                http_options={"api_version": "v1beta"},
            )
            logger.info("genai.Client initialised (v1beta)")
        return self._client

    @property
    def model(self) -> str:
        if self._model is None:
            raw = os.getenv("MODEL_ID", "gemini-3.1-flash-live-preview")
            self._model = raw if raw.startswith("models/") else f"models/{raw}"
        return self._model

    # ------------------------------------------------------------------
    # LiveConnectConfig
    # ------------------------------------------------------------------

    def get_live_config(self) -> types.LiveConnectConfig:
        """Build and return a LiveConnectConfig for a KYC session."""
        from kyc_agent.agent import SYSTEM_INSTRUCTION, get_tool_declarations

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_INSTRUCTION,
            tools=get_tool_declarations(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon",
                    )
                ),
                language_code="hi-IN",
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(handle=None),
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow(),
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefix_padding_ms=200,
                    silence_duration_ms=800,
                ),
                turn_coverage=types.TurnCoverage.TURN_INCLUDES_ALL_INPUT,
            ),
        )


# Global singleton
gemini_manager = GeminiClientManager()
