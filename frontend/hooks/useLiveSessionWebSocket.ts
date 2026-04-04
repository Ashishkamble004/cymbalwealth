/**
 * Custom hook for managing a WebSocket connection to the Video KYC backend.
 * Handles bidirectional audio/video streaming with the ADK agent.
 */

import { useState, useRef, useCallback, useEffect } from "react";
import {
  ConnectionState,
  ChatMessage,
  ServerMessage,
  ClientMessage,
} from "../types";
import {
  encodeAudioToBase64,
  decodeBase64ToAudio,
  createAudioBuffer,
  resampleAudio,
  getPCMProcessorCode,
} from "../utils/audioUtils";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "ws://localhost:8080";
const INPUT_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 24000;
const VIDEO_FPS = 1;

interface UseLiveSessionReturn {
  connectionState: ConnectionState;
  messages: ChatMessage[];
  isMicActive: boolean;
  isCameraActive: boolean;
  isRearCamera: boolean;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  connect: (referenceNumber: string) => void;
  disconnect: () => void;
  toggleMic: () => void;
  toggleCamera: () => void;
  switchCamera: () => Promise<void>;
  sendTextMessage: (text: string) => void;
}

export function useLiveSessionWebSocket(): UseLiveSessionReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>(
    ConnectionState.DISCONNECTED
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isMicActive, setIsMicActive] = useState(false);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isRearCamera, setIsRearCamera] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const facingModeRef = useRef<"user" | "environment">("user");
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const videoIntervalRef = useRef<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const isSpeakingRef = useRef(false);

  // Queue for audio playback to prevent overlap
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);

  // Track in-progress transcription message IDs for live updates
  const inputTranscriptionIdRef = useRef<string | null>(null);
  const outputTranscriptionIdRef = useRef<string | null>(null);
  // Client-side buffer for output transcription (handles both cumulative and delta chunks)
  const outputTextBufferRef = useRef<string>("");

  const addMessage = useCallback(
    (role: "user" | "agent", text: string, source?: "text" | "transcription") => {
      const msg: ChatMessage = {
        id: crypto.randomUUID(),
        role,
        text,
        timestamp: new Date(),
        source,
      };
      setMessages((prev) => [...prev, msg]);
      return msg.id;
    },
    []
  );

  /**
   * Input transcription: Gemini sends growing cumulative partials per utterance.
   * ("Hello" → "Hello my" → "Hello my name is Ashish")
   * So we REPLACE the bubble text each time — the latest value is always the fullest.
   */
  const updateInputTranscription = useCallback(
    (text: string, finished: boolean) => {
      if (inputTranscriptionIdRef.current) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === inputTranscriptionIdRef.current
              ? { ...m, text, timestamp: new Date() }
              : m
          )
        );
        if (finished) inputTranscriptionIdRef.current = null;
      } else {
        const id = crypto.randomUUID();
        setMessages((prev) => [...prev, { id, role: "user", text, timestamp: new Date(), source: "transcription" } as ChatMessage]);
        if (!finished) inputTranscriptionIdRef.current = id;
      }
    },
    []
  );

  /**
   * Output transcription: chunks can arrive as either cumulative or delta.
   * Buffer heuristic (from cymbal-shop reference):
   * - If new text is longer AND starts with same prefix → server accumulating, REPLACE buffer
   * - Otherwise → new chunk, APPEND to buffer
   * DOM bubble always receives the full buffer content (REPLACE not append in DOM).
   */
  const updateOutputTranscription = useCallback(
    (text: string, finished: boolean) => {
      const buf = outputTextBufferRef.current;
      let newBuf: string;

      if (buf && text.length > buf.length && text.startsWith(buf.substring(0, Math.min(10, buf.length)))) {
        // Cumulative — server already has the full text, use it
        newBuf = text;
      } else if (buf && !text.startsWith(buf.substring(0, Math.min(10, buf.length)))) {
        // New distinct chunk — append
        newBuf = buf + (buf.endsWith(" ") ? "" : " ") + text;
      } else {
        // First chunk or exact match
        newBuf = text;
      }
      outputTextBufferRef.current = newBuf;

      const displayText = newBuf.trim();
      if (outputTranscriptionIdRef.current) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === outputTranscriptionIdRef.current
              ? { ...m, text: displayText, timestamp: new Date() }
              : m
          )
        );
        if (finished) {
          outputTranscriptionIdRef.current = null;
          outputTextBufferRef.current = "";
        }
      } else {
        const id = crypto.randomUUID();
        setMessages((prev) => [...prev, { id, role: "agent", text: displayText, timestamp: new Date(), source: "transcription" } as ChatMessage]);
        if (!finished) outputTranscriptionIdRef.current = id;
        else outputTextBufferRef.current = "";
      }
    },
    []
  );

  // Play queued audio buffers sequentially
  const playNextAudio = useCallback(() => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;
    isSpeakingRef.current = true;

    const buffer = audioQueueRef.current.shift()!;
    const ctx = playbackContextRef.current;
    if (!ctx) {
      isPlayingRef.current = false;
      isSpeakingRef.current = false;
      return;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = () => {
      isPlayingRef.current = false;
      if (audioQueueRef.current.length > 0) {
        playNextAudio();
      } else {
        isSpeakingRef.current = false;
      }
    };
    source.start();
  }, []);

  const handleServerMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: ServerMessage = JSON.parse(event.data);

        switch (data.type) {
          case "audio": {
            if (data.data && playbackContextRef.current) {
              const pcm = decodeBase64ToAudio(data.data);
              const audioBuffer = createAudioBuffer(
                playbackContextRef.current,
                pcm,
                OUTPUT_SAMPLE_RATE
              );
              audioQueueRef.current.push(audioBuffer);
              playNextAudio();
            }
            break;
          }
          case "transcript": {
            if (data.text) {
              addMessage(
                data.role === "user" ? "user" : "agent",
                data.text,
                "text"
              );
            }
            break;
          }
          case "input_transcription": {
            if (data.text && data.text.trim()) {
              updateInputTranscription(data.text.trim(), !!data.finished);
            } else if (data.finished) {
              inputTranscriptionIdRef.current = null;
            }
            break;
          }
          case "output_transcription": {
            if (data.text && data.text.trim()) {
              updateOutputTranscription(data.text.trim(), !!data.finished);
            } else if (data.finished) {
              outputTranscriptionIdRef.current = null;
              outputTextBufferRef.current = "";
            }
            break;
          }
          case "turn_complete": {
            // Safety net: clear output transcription state when agent turn ends
            outputTranscriptionIdRef.current = null;
            outputTextBufferRef.current = "";
            break;
          }
          case "interrupted": {
            // User interrupted — clear output state, input stays (user was speaking)
            outputTranscriptionIdRef.current = null;
            outputTextBufferRef.current = "";
            break;
          }
          case "pong":
            break;
          default:
        }
      } catch (e) {
        console.error("[WS] Failed to parse message:", e);
      }
    },
    [addMessage, updateInputTranscription, updateOutputTranscription, playNextAudio]
  );

  const sendMessage = useCallback((msg: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // Start capturing audio from the microphone
  const startAudioCapture = useCallback(
    async (stream: MediaStream) => {
      const audioContext = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE });
      audioContextRef.current = audioContext;

      const processorCode = getPCMProcessorCode();
      const blob = new Blob([processorCode], { type: "application/javascript" });
      const url = URL.createObjectURL(blob);
      await audioContext.audioWorklet.addModule(url);
      URL.revokeObjectURL(url);

      const source = audioContext.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(audioContext, "pcm-processor");
      workletNodeRef.current = workletNode;

      workletNode.port.onmessage = (event) => {
        if (event.data.pcmData) {
          const resampled = resampleAudio(
            event.data.pcmData,
            audioContext.sampleRate,
            INPUT_SAMPLE_RATE
          );
          const base64 = encodeAudioToBase64(resampled);
          sendMessage({ type: "audio", data: base64 });
        }
      };

      source.connect(workletNode);
      workletNode.connect(audioContext.destination);
    },
    [sendMessage]
  );

  // Start capturing video frames
  const startVideoCapture = useCallback(
    (stream: MediaStream) => {
      if (!canvasRef.current) {
        canvasRef.current = document.createElement("canvas");
      }
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      const videoTrack = stream.getVideoTracks()[0];
      const settings = videoTrack.getSettings();
      canvas.width = settings.width || 640;
      canvas.height = settings.height || 480;

      videoIntervalRef.current = window.setInterval(() => {
        if (videoRef.current && ctx) {
          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
          const dataUrl = canvas.toDataURL("image/jpeg", 0.6);
          const base64 = dataUrl.split(",")[1];
          sendMessage({ type: "video", data: base64 });
        }
      }, 1000 / VIDEO_FPS);
    },
    [sendMessage]
  );

  const connect = useCallback(
    (referenceNumber: string) => {
      if (wsRef.current) return;
      setConnectionState(ConnectionState.CONNECTING);
      setMessages([]);
      // Reset transcription state so stale refs don't bleed between sessions
      inputTranscriptionIdRef.current = null;
      outputTranscriptionIdRef.current = null;
      outputTextBufferRef.current = "";

      const userId = `user-${crypto.randomUUID().slice(0, 8)}`;
      const sessionId = `session-${crypto.randomUUID().slice(0, 8)}`;
      const wsUrl = `${BACKEND_URL}/ws/${userId}/${sessionId}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        setConnectionState(ConnectionState.CONNECTED);

        // Initialize playback context
        playbackContextRef.current = new AudioContext({
          sampleRate: OUTPUT_SAMPLE_RATE,
        });

        // Request media access
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              sampleRate: INPUT_SAMPLE_RATE,
              channelCount: 1,
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
            video: {
              width: { ideal: 640 },
              height: { ideal: 480 },
              facingMode: "user",
            },
          });

          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }

          await startAudioCapture(stream);
          startVideoCapture(stream);
          setIsMicActive(true);
          setIsCameraActive(true);
        } catch (err) {
          console.error("[Media] Failed to access media devices:", err);
        }

        // Send context with reference number
        sendMessage({
          type: "context",
          reference_number: referenceNumber,
        });

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          sendMessage({ type: "ping" });
        }, 30000);
      };

      ws.onmessage = handleServerMessage;

      ws.onerror = (e) => {
        console.error("[WS] Error:", e);
        setConnectionState(ConnectionState.ERROR);
      };

      ws.onclose = () => {
        setConnectionState(ConnectionState.DISCONNECTED);
        cleanup();
      };
    },
    [handleServerMessage, sendMessage, startAudioCapture, startVideoCapture]
  );

  const cleanup = useCallback(() => {
    // Stop ping
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    // Stop video capture
    if (videoIntervalRef.current) {
      clearInterval(videoIntervalRef.current);
      videoIntervalRef.current = null;
    }
    // Stop audio worklet
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    // Close audio contexts
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }
    // Stop media tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    // Clear audio queue
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    isSpeakingRef.current = false;

    setIsMicActive(false);
    setIsCameraActive(false);
    wsRef.current = null;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      sendMessage({ type: "end_session" });
      wsRef.current.close();
    }
    cleanup();
  }, [cleanup, sendMessage]);

  const toggleMic = useCallback(() => {
    if (streamRef.current) {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMicActive(audioTrack.enabled);
      }
    }
  }, []);

  const toggleCamera = useCallback(() => {
    if (streamRef.current) {
      const videoTrack = streamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsCameraActive(videoTrack.enabled);
        // Stop/restart video frame capture
        if (!videoTrack.enabled && videoIntervalRef.current) {
          clearInterval(videoIntervalRef.current);
          videoIntervalRef.current = null;
        } else if (videoTrack.enabled && !videoIntervalRef.current) {
          startVideoCapture(streamRef.current);
        }
      }
    }
  }, [startVideoCapture]);

  const sendTextMessage = useCallback(
    (text: string) => {
      if (text.trim()) {
        sendMessage({ type: "text", data: text.trim() });
        addMessage("user", text.trim(), "text");
      }
    },
    [sendMessage, addMessage]
  );

  const switchCamera = useCallback(async () => {
    if (!streamRef.current) return;

    // Toggle facing mode
    const newFacingMode = facingModeRef.current === "user" ? "environment" : "user";

    // Stop current video track(s)
    const oldVideoTracks = streamRef.current.getVideoTracks();
    oldVideoTracks.forEach((t) => {
      streamRef.current!.removeTrack(t);
      t.stop();
    });

    try {
      const newVideoStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: newFacingMode,
        },
      });

      const newVideoTrack = newVideoStream.getVideoTracks()[0];
      streamRef.current.addTrack(newVideoTrack);
      facingModeRef.current = newFacingMode;
      setIsRearCamera(newFacingMode === "environment");

      // Re-bind video element to pick up the new track
      if (videoRef.current) {
        videoRef.current.srcObject = null;
        videoRef.current.srcObject = streamRef.current;
      }

      // Restart video frame capture with the updated stream
      if (videoIntervalRef.current) {
        clearInterval(videoIntervalRef.current);
        videoIntervalRef.current = null;
      }
      startVideoCapture(streamRef.current);
    } catch (err) {
      console.error("[Media] Failed to switch camera:", err);
      // Re-attach original track on failure so video keeps working
      oldVideoTracks.forEach((t) => streamRef.current?.addTrack(t));
    }
  }, [startVideoCapture]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionState,
    messages,
    isMicActive,
    isCameraActive,
    isRearCamera,
    videoRef,
    connect,
    disconnect,
    toggleMic,
    toggleCamera,
    switchCamera,
    sendTextMessage,
  };
}
