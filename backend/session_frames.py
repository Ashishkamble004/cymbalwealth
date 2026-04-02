"""Shared state for passing video frames between WebSocket handler and agent tools.

Stores the latest video frame per session so capture tools can access it.

Architecture note: This uses in-process memory with threading locks, which works
correctly for single-instance Cloud Run (min-instances=1, session-affinity=true).
For horizontal scaling across multiple instances, replace with Redis:
  - redis.set(f"frame:{session_id}", frame_data, ex=600)
  - redis.get(f"frame:{session_id}")
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_latest_frames: dict[str, bytes] = {}
_session_filenames: dict[str, str] = {}
_lock = threading.Lock()

# Max frames to keep in memory (prevent memory leak from abandoned sessions)
_MAX_SESSIONS = 50


def set_latest_frame(session_id: str, frame_data: bytes):
    """Store the latest video frame for a session."""
    with _lock:
        # Evict oldest if too many sessions
        if len(_latest_frames) >= _MAX_SESSIONS and session_id not in _latest_frames:
            oldest = next(iter(_latest_frames))
            del _latest_frames[oldest]
            _session_filenames.pop(oldest, None)
            logger.warning(f"[Frames] Evicted oldest session {oldest} (max {_MAX_SESSIONS})")
        _latest_frames[session_id] = frame_data


def get_latest_frame(session_id: str) -> Optional[bytes]:
    """Get the latest video frame for a session."""
    with _lock:
        return _latest_frames.get(session_id)


def clear_session(session_id: str):
    """Clean up all data for a completed session."""
    with _lock:
        _latest_frames.pop(session_id, None)
        _session_filenames.pop(session_id, None)


def set_session_filename(session_id: str, filename: str):
    """Store the session filename for consistent naming across captures."""
    with _lock:
        _session_filenames[session_id] = filename


def get_session_filename(session_id: str) -> Optional[str]:
    """Get the session filename."""
    with _lock:
        return _session_filenames.get(session_id)
