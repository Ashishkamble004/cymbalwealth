"use client";

import { useState, useRef, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  clientId: number;
  clientName: string;
}

interface TranscriptEntry {
  role: "user" | "aria";
  text: string;
  timestamp: string;
}

export default function VoiceAssistant({ clientId, clientName }: Props) {
  const [isActive, setIsActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [duration, setDuration] = useState(0);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [status, setStatus] = useState<string>("Ready");
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number | null>(null);

  // Waveform visualizer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isActive) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const bars = 40;
      const barW = w / bars - 2;

      for (let i = 0; i < bars; i++) {
        const amplitude = isActive && !isMuted ? Math.random() * 0.6 + 0.1 : 0.05;
        const barH = h * amplitude;
        const x = i * (barW + 2);
        const y = (h - barH) / 2;

        const gradient = ctx.createLinearGradient(x, y, x, y + barH);
        gradient.addColorStop(0, "rgba(99, 102, 241, 0.8)");
        gradient.addColorStop(1, "rgba(139, 92, 246, 0.4)");
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barW, barH);
      }

      animFrameRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isActive, isMuted]);

  const startSession = () => {
    const wsUrl = API_URL.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsUrl}/voice/stream?client_id=${clientId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsActive(true);
      setStatus("Connected to Aria");
      setDuration(0);
      setTranscript([]);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "transcript_ack" || msg.type === "session_start") {
          setStatus("Listening...");
        }
        if (msg.type === "session_end") {
          setStatus(`Session ended — ${msg.transcript_count} messages`);
        }
        if (msg.type === "error") {
          setStatus(msg.message);
        }
      } catch {
        /* ignore */
      }
    };

    ws.onclose = () => {
      setIsActive(false);
      if (timerRef.current) clearInterval(timerRef.current);
    };

    ws.onerror = () => {
      setStatus("Connection error — please retry");
      setIsActive(false);
    };
  };

  const endSession = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: "end_session" }));
      wsRef.current.close();
    }
    setIsActive(false);
    if (timerRef.current) clearInterval(timerRef.current);
    setStatus("Session ended");
  };

  const addTranscript = (role: "user" | "aria", text: string) => {
    const entry: TranscriptEntry = {
      role,
      text,
      timestamp: new Date().toISOString(),
    };
    setTranscript((prev) => [...prev, entry]);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: "transcript", role, text })
      );
    }
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">
            🎤 Aria — Voice Assistant
          </h3>
          <p className="text-xs text-gray-400">
            Speaking with {clientName} · {status}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isActive && (
            <>
              <span className="text-sm font-mono text-gray-400">
                {formatTime(duration)}
              </span>
              <button
                onClick={() => setIsMuted(!isMuted)}
                className={`rounded-lg px-3 py-1.5 text-sm transition ${
                  isMuted
                    ? "bg-red-500/20 text-red-400"
                    : "bg-gray-800 text-gray-300"
                }`}
              >
                {isMuted ? "🔇 Muted" : "🔊 Mute"}
              </button>
            </>
          )}
          <button
            onClick={isActive ? endSession : startSession}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              isActive
                ? "bg-red-600 text-white hover:bg-red-500"
                : "bg-indigo-600 text-white hover:bg-indigo-500"
            }`}
          >
            {isActive ? "End Session" : "Start Session"}
          </button>
        </div>
      </div>

      {/* Waveform */}
      <div className="mb-4 rounded-lg bg-gray-800/50 p-4">
        <canvas
          ref={canvasRef}
          width={600}
          height={80}
          className="w-full h-20"
        />
      </div>

      {/* Transcript */}
      <div className="max-h-60 overflow-y-auto space-y-2">
        {transcript.length === 0 ? (
          <p className="text-center text-sm text-gray-500 py-4">
            {isActive
              ? "Listening... Start speaking to Aria"
              : "Start a session to interact with Aria"}
          </p>
        ) : (
          transcript.map((t, i) => (
            <div
              key={i}
              className={`flex gap-3 text-sm ${
                t.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 ${
                  t.role === "user"
                    ? "bg-indigo-500/20 text-indigo-200"
                    : "bg-purple-500/20 text-purple-200"
                }`}
              >
                <p className="text-xs font-medium mb-0.5 opacity-60">
                  {t.role === "user" ? clientName : "Aria"}
                </p>
                {t.text}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
