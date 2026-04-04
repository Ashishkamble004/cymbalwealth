"""Utility functions for saving KYC session data to Cloud Storage."""

import io
import json
import logging
import os
import wave
from datetime import datetime, timezone

import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "cymbal-wealth")
logger = logging.getLogger(__name__)


def _get_gcs_bucket():
    """Get GCS bucket client."""
    from google.cloud import storage
    client = storage.Client()
    return client.bucket(GCS_BUCKET)


def _upload_to_gcs(blob_path: str, data: bytes, content_type: str):
    """Upload data to GCS."""
    try:
        bucket = _get_gcs_bucket()
        blob = bucket.blob(blob_path)
        blob.upload_from_string(data, content_type=content_type)
        logger.info(f"[Storage] Uploaded to gs://{GCS_BUCKET}/{blob_path}")
        return f"gs://{GCS_BUCKET}/{blob_path}"
    except Exception as e:
        logger.error(f"[Storage] Failed to upload {blob_path}: {e}")
        return None


def get_session_filename(reference_number: str, session_id: str) -> str:
    """Generate a consistent filename for a session across all folders."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{reference_number}_{session_id}_{ts}"


def save_transcript(reference_number: str, session_id: str, session_filename: str, transcript: list[dict], user_id: str = ""):
    """Save call transcription to GCS under /call-transcription/."""
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "reference_number": reference_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transcript": transcript,
    }
    payload_json = json.dumps(payload, indent=2, ensure_ascii=False)
    blob_path = f"call-transcription/{session_filename}.json"
    result = _upload_to_gcs(blob_path, payload_json.encode("utf-8"), "application/json")
    if not result:
        local_dir = os.path.join("transcripts", reference_number)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, f"{session_filename}.json")
        with open(local_path, "w") as f:
            f.write(payload_json)
        logger.warning(f"[Storage] GCS unavailable. Transcript saved locally: {local_path}")


def _pcm_to_wav(pcm_chunks: list[bytes], sample_rate: int) -> bytes:
    """Convert raw PCM chunks to WAV format."""
    all_pcm = b"".join(pcm_chunks)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(all_pcm)
    return wav_buffer.getvalue()


def save_audio_recording(session_filename: str, input_chunks: list[bytes], output_chunks: list[bytes],
                          input_sample_rate: int = 16000, output_sample_rate: int = 24000):
    """Save audio recordings to GCS under /call-recording/.

    Saves both user and agent audio as separate WAV files,
    plus a combined version with the agent audio resampled to match user's rate.
    """
    # Save user audio
    if input_chunks:
        user_wav = _pcm_to_wav(input_chunks, input_sample_rate)
        blob_path = f"call-recording/{session_filename}_user.wav"
        _upload_to_gcs(blob_path, user_wav, "audio/wav")
        logger.info(f"[Storage] User audio: {len(input_chunks)} chunks, {len(user_wav)} bytes")

    # Save agent audio
    if output_chunks:
        agent_wav = _pcm_to_wav(output_chunks, output_sample_rate)
        blob_path = f"call-recording/{session_filename}_agent.wav"
        _upload_to_gcs(blob_path, agent_wav, "audio/wav")
        logger.info(f"[Storage] Agent audio: {len(output_chunks)} chunks, {len(agent_wav)} bytes")

    if not input_chunks and not output_chunks:
        logger.warning("[Storage] No audio chunks to save")


def save_video_recording(session_filename: str, video_frames: list[bytes], fps: float = 1.0):
    """Save video recording as MP4 to GCS under /video-recording/.

    Stitches JPEG frames into an MP4 video using OpenCV.
    """
    if not video_frames:
        logger.warning("[Storage] No video frames to save")
        return

    # Decode first frame to get dimensions
    first_frame = cv2.imdecode(np.frombuffer(video_frames[0], np.uint8), cv2.IMREAD_COLOR)
    if first_frame is None:
        logger.error("[Storage] Failed to decode first video frame")
        return
    height, width = first_frame.shape[:2]

    # Write video to temp file (OpenCV needs a file path)
    tmp_path = f"/tmp/{session_filename}.avi"
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))

    frame_count = 0
    for frame_data in video_frames:
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            # Resize if dimensions don't match first frame
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            writer.write(frame)
            frame_count += 1

    writer.release()

    # Upload to GCS
    try:
        with open(tmp_path, "rb") as f:
            video_data = f.read()
        blob_path = f"video-recording/{session_filename}.avi"
        _upload_to_gcs(blob_path, video_data, "video/x-msvideo")
        logger.info(f"[Storage] Video: {frame_count} frames stitched into AVI")
    except Exception as e:
        logger.error(f"[Storage] Failed to read/upload video: {e}")
    finally:
        # Cleanup temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def save_capture(session_filename: str, folder: str, image_data: bytes, suffix: str = "") -> str:
    """Save a captured image (PAN card, profile photo, signature) to GCS.

    Args:
        session_filename: The consistent session filename
        folder: GCS folder name (pan-card, profile-photo, signature)
        image_data: JPEG image bytes
        suffix: Optional suffix for the filename

    Returns:
        GCS URI of the saved image, or empty string on failure.
    """
    filename = f"{session_filename}{suffix}.jpg"
    blob_path = f"{folder}/{filename}"
    result = _upload_to_gcs(blob_path, image_data, "image/jpeg")
    return result or ""
