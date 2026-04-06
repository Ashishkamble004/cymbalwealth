import React, { useCallback, useEffect, useRef, useState } from "react";
import { ConnectionState } from "../types";

interface TranscriptEntry {
  id: string;
  text: string;
  isFinal: boolean;
  speaker: "customer" | "ai";
  timestamp: Date;
  latencyMs?: number;
}

interface Alert {
  id: string;
  title: string;
  description: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  timestamp: Date;
}

interface CustomerSupportPageProps {
  onBack: () => void;
}

const LANGUAGE_OPTIONS = [
  { value: "auto", label: "Auto Detect" },
  { value: "hi-IN", label: "Hindi" },
  { value: "en-IN", label: "English (India)" },
  { value: "mr-IN", label: "Marathi" },
  { value: "ta-IN", label: "Tamil" },
  { value: "te-IN", label: "Telugu" },
  { value: "kn-IN", label: "Kannada" },
  { value: "gu-IN", label: "Gujarati" },
  { value: "bn-IN", label: "Bengali" },
  { value: "ml-IN", label: "Malayalam" },
  { value: "pa-IN", label: "Punjabi" },
];

const PROCESSOR_CODE = `
class PCMProcessor extends AudioWorkletProcessor {
  constructor() { super(); this._targetSampleRate = 16000; }
  process(inputs) {
    const input = inputs[0][0];
    if (!input) return true;
    const ratio = sampleRate / this._targetSampleRate;
    const outLength = Math.floor(input.length / ratio);
    const out = new Int16Array(outLength);
    for (let i = 0; i < outLength; i++) {
      const sample = input[Math.floor(i * ratio)];
      out[i] = Math.max(-32768, Math.min(32767, sample * 32768));
    }
    this.port.postMessage(out.buffer, [out.buffer]);
    return true;
  }
}
registerProcessor('pcm-processor', PCMProcessor);
`;

const SEVERITY_STYLES: Record<Alert["severity"], { border: string; text: string; badge: string }> = {
  HIGH:   { border: "border-red-600",     text: "text-red-600",    badge: "bg-red-600"    },
  MEDIUM: { border: "border-amber-500",   text: "text-amber-600",  badge: "bg-amber-500"  },
  LOW:    { border: "border-idfc-maroon", text: "text-idfc-maroon", badge: "bg-idfc-maroon" },
};

export default function CustomerSupportPage({ onBack }: CustomerSupportPageProps) {
  const [status, setStatus] = useState<ConnectionState>(ConnectionState.DISCONNECTED);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState("auto");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const aiEntryIdRef = useRef<string | null>(null);
  const aiStartTimeRef = useRef<number>(0);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    requestAnimationFrame(() => {
      transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
    });
  }, [transcript]);

  const handleMessage = useCallback((event: MessageEvent) => {
    // Binary frames (audio echo) are not JSON — skip
    if (event.data instanceof ArrayBuffer || event.data instanceof Blob) return;

    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(event.data as string) as Record<string, unknown>;
    } catch {
      return;
    }

    const type = msg.type as string;

    if (type === "transcript") {
      const isFinal = Boolean(msg.is_final);
      const text = String(msg.text ?? "");
      const entryId = String(msg.id ?? crypto.randomUUID());

      setTranscript((prev) => {
        const existing = prev.findIndex((e) => e.id === entryId);
        const entry: TranscriptEntry = {
          id: entryId,
          text,
          isFinal,
          speaker: "customer",
          timestamp: new Date(),
        };
        if (existing !== -1) {
          const next = [...prev];
          next[existing] = entry;
          return next;
        }
        // Server re-uses the same id for interim → final updates; but if the id
        // is new, replace the last open interim to avoid duplicate bubbles.
        const lastIdx = prev.length - 1;
        if (lastIdx >= 0 && !prev[lastIdx].isFinal && prev[lastIdx].speaker === "customer") {
          const next = [...prev];
          next[lastIdx] = entry;
          return next;
        }
        return [...prev, entry];
      });
    } else if (type === "stream_start") {
      const id = crypto.randomUUID();
      aiEntryIdRef.current = id;
      aiStartTimeRef.current = Date.now();
      setTranscript((prev) => [
        ...prev,
        { id, text: "", isFinal: false, speaker: "ai", timestamp: new Date() },
      ]);
    } else if (type === "stream_chunk") {
      const chunk = String(msg.text ?? "");
      const id = aiEntryIdRef.current;
      if (!id) return;
      setTranscript((prev) =>
        prev.map((e) =>
          e.id === id ? { ...e, text: e.text + chunk } : e
        )
      );
    } else if (type === "stream_end") {
      const id = aiEntryIdRef.current;
      const latencyMs = Date.now() - aiStartTimeRef.current;
      if (!id) return;
      setTranscript((prev) =>
        prev.map((e) =>
          e.id === id ? { ...e, isFinal: true, latencyMs } : e
        )
      );
      aiEntryIdRef.current = null;
    } else if (type === "compliance_result") {
      const alert: Alert = {
        id: crypto.randomUUID(),
        title: String(msg.title ?? "Compliance Alert"),
        description: String(msg.description ?? ""),
        severity: (msg.severity as Alert["severity"]) ?? "LOW",
        timestamp: new Date(),
      };
      setAlerts((prev) => [alert, ...prev]);
    } else if (type === "error") {
      setErrorMsg(String(msg.message ?? "An unknown error occurred."));
    }
  }, []);

  const connect = useCallback(async () => {
    setErrorMsg(null);
    setStatus(ConnectionState.CONNECTING);

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setErrorMsg("Microphone access denied. Please allow mic permissions and try again.");
      setStatus(ConnectionState.DISCONNECTED);
      return;
    }
    streamRef.current = stream;

    const base = (import.meta.env.VITE_BACKEND_URL as string | undefined) || "http://localhost:8000";
    const wsBase = base.replace(/^http/, "ws").replace(/^https/, "wss");
    const wsUrl = `${wsBase}/customer-support/ws?stt_language=${selectedLanguage}`;

    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = async () => {
      setStatus(ConnectionState.CONNECTED);

      try {
        const blob = new Blob([PROCESSOR_CODE], { type: "application/javascript" });
        const blobUrl = URL.createObjectURL(blob);

        const audioCtx = new AudioContext({ sampleRate: 48000 });
        audioCtxRef.current = audioCtx;

        await audioCtx.audioWorklet.addModule(blobUrl);
        URL.revokeObjectURL(blobUrl);

        const source = audioCtx.createMediaStreamSource(stream);
        const workletNode = new AudioWorkletNode(audioCtx, "pcm-processor");
        workletNodeRef.current = workletNode;

        workletNode.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
          }
        };

        source.connect(workletNode);
        workletNode.connect(audioCtx.destination);
      } catch (err) {
        console.error("AudioWorklet error:", err);
        setErrorMsg("Audio capture failed. Please check browser compatibility.");
      }
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => {
      setErrorMsg("WebSocket connection error. Is the backend running?");
    };

    ws.onclose = () => {
      setStatus(ConnectionState.DISCONNECTED);
      cleanup();
    };
  }, [selectedLanguage, handleMessage]);

  const cleanup = useCallback(() => {
    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    cleanup();
    setStatus(ConnectionState.DISCONNECTED);
  }, [cleanup]);

  useEffect(() => () => { disconnect(); }, [disconnect]);

  const isConnected = status === ConnectionState.CONNECTED;
  const isConnecting = status === ConnectionState.CONNECTING;
  const highAlerts = alerts.filter((a) => a.severity === "HIGH").length;

  return (
    <div className="h-[100dvh] flex flex-col bg-idfc-cream font-sans">
      <header className="bg-idfc-maroon text-white px-4 py-3 flex items-center justify-between shadow-md z-10 flex-shrink-0">
        <div className="flex items-center space-x-3">
          <button
            onClick={onBack}
            className="flex items-center space-x-1 text-white/80 hover:text-white transition-colors text-sm font-medium"
            aria-label="Back to landing"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="hidden sm:inline">Back</span>
          </button>
          <span className="text-white/40">|</span>
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-idfc-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            <span className="font-semibold text-base">Customer Support</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isConnected
                ? "bg-green-400"
                : isConnecting
                ? "bg-yellow-400 animate-pulse"
                : "bg-white/40"
            }`}
          />
          <span className="text-xs font-semibold tracking-wide uppercase">
            {isConnected ? "LIVE" : isConnecting ? "CONNECTING…" : "DISCONNECTED"}
          </span>
        </div>
      </header>

      {errorMsg && (
        <div className="bg-red-50 border-l-4 border-red-600 px-4 py-3 flex items-start justify-between text-sm text-red-700 flex-shrink-0">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="ml-4 text-red-400 hover:text-red-600 font-bold leading-none">×</button>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[30%] flex-shrink-0 border-r border-idfc-gray-200 flex flex-col bg-white overflow-hidden">
          <div className="px-4 py-3 border-b border-idfc-gray-200 bg-idfc-gray-50 flex items-center justify-between flex-shrink-0">
            <h2 className="text-sm font-semibold text-idfc-gray-800">Compliance Alerts</h2>
            {alerts.length > 0 && (
              <span className="text-xs font-semibold bg-idfc-maroon text-white rounded-full px-2 py-0.5">
                {alerts.length}
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {alerts.length === 0 ? (
              <div className="text-center py-10 text-idfc-gray-400">
                <svg className="w-8 h-8 mx-auto mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-xs">No alerts yet</p>
              </div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`bg-white rounded-lg border-l-4 ${SEVERITY_STYLES[alert.severity].border} border border-idfc-gray-200 p-3 shadow-sm`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className={`text-xs font-bold uppercase tracking-wide ${SEVERITY_STYLES[alert.severity].text}`}>
                      {alert.severity}
                    </p>
                    <p className="text-[10px] text-idfc-gray-400 whitespace-nowrap">
                      {alert.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  <p className="text-xs font-semibold text-idfc-gray-800 mt-1">{alert.title}</p>
                  {alert.description && (
                    <p className="text-xs text-idfc-gray-500 mt-0.5 leading-relaxed">{alert.description}</p>
                  )}
                </div>
              ))
            )}
          </div>

          {highAlerts > 0 && (
            <div className="border-t border-idfc-gray-200 px-4 py-2 bg-red-50 flex items-center space-x-2 flex-shrink-0">
              <span className={`text-xs font-bold rounded-full px-2 py-0.5 text-white ${SEVERITY_STYLES.HIGH.badge}`}>
                {highAlerts}
              </span>
              <span className="text-xs font-medium text-red-700">High-severity alert{highAlerts !== 1 ? "s" : ""}</span>
            </div>
          )}
        </div>

        <div className="flex-1 flex flex-col bg-idfc-cream overflow-hidden">
          <div className="px-4 py-3 border-b border-idfc-gray-200 bg-white flex-shrink-0">
            <h2 className="text-sm font-semibold text-idfc-gray-800">Conversation</h2>
            <p className="text-xs text-idfc-gray-400 mt-0.5">
              {isConnected ? "Listening — speak now" : "Connect to start transcription"}
            </p>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {transcript.length === 0 && (
              <div className="text-center py-12 text-idfc-gray-400">
                <svg className="w-10 h-10 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
                <p className="text-sm">Conversation will appear here</p>
              </div>
            )}

            {transcript.map((entry) => {
              if (entry.speaker === "customer") {
                return (
                  <div key={entry.id} className="flex justify-start">
                    <div
                      className={`max-w-[80%] bg-white border-l-4 border-idfc-gold rounded-r-xl rounded-bl-xl px-4 py-2.5 shadow-sm ${
                        !entry.isFinal ? "opacity-65 border-dashed" : ""
                      }`}
                    >
                      <p className="text-xs font-semibold text-idfc-gray-400 mb-1 uppercase tracking-wide">Customer</p>
                      <p className="text-sm text-idfc-gray-700 leading-relaxed">{entry.text}</p>
                      <p className="text-[10px] text-idfc-gray-300 mt-1">
                        {entry.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        {!entry.isFinal && " · interim"}
                      </p>
                    </div>
                  </div>
                );
              }

              return (
                <div key={entry.id} className="flex justify-end">
                  <div
                    className={`max-w-[80%] bg-[#f7edf3] rounded-l-xl rounded-br-xl px-4 py-2.5 shadow-sm${entry.isFinal ? "" : " opacity-75"}`}
                  >
                    <div className="flex items-center space-x-2 mb-1">
                      <p className="text-xs font-semibold text-idfc-maroon uppercase tracking-wide">AI Suggestion</p>
                      {entry.isFinal && entry.latencyMs !== undefined && (
                        <span className="text-[10px] bg-idfc-maroon/10 text-idfc-maroon rounded-full px-1.5 py-0.5 font-medium">
                          {entry.latencyMs}ms
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-idfc-maroon leading-relaxed whitespace-pre-wrap">
                      {entry.text}
                      {!entry.isFinal && (
                        <span className="inline-block w-1.5 h-3.5 bg-idfc-maroon/60 ml-0.5 animate-pulse rounded-sm align-text-bottom" />
                      )}
                    </p>
                    <p className="text-[10px] text-idfc-maroon/40 mt-1">
                      {entry.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              );
            })}
            <div ref={transcriptEndRef} />
          </div>
        </div>
      </div>

      <footer className="bg-white border-t border-idfc-gray-200 px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3 flex-shrink-0">
        <div className="flex items-center space-x-2">
          <svg className="w-4 h-4 text-idfc-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
          </svg>
          <label htmlFor="lang-select" className="text-sm text-idfc-gray-600 font-medium whitespace-nowrap">
            Language:
          </label>
          <select
            id="lang-select"
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            disabled={isConnected || isConnecting}
            className="text-sm border border-idfc-gray-300 rounded-lg px-2 py-1.5 focus:ring-2 focus:ring-idfc-maroon/30 focus:border-idfc-maroon outline-none disabled:bg-idfc-gray-100 disabled:cursor-not-allowed text-idfc-gray-700"
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-3">
          {status !== ConnectionState.CONNECTED ? (
            <button
              onClick={connect}
              disabled={isConnecting}
              className="flex items-center space-x-2 px-5 py-2 bg-idfc-maroon hover:bg-idfc-maroon-dark text-white text-sm font-semibold rounded-xl shadow-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isConnecting ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>Connecting…</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="6" />
                  </svg>
                  <span>Connect &amp; Start</span>
                </>
              )}
            </button>
          ) : (
            <button
              onClick={disconnect}
              className="flex items-center space-x-2 px-5 py-2 border-2 border-idfc-maroon text-idfc-maroon text-sm font-semibold rounded-xl hover:bg-idfc-maroon/5 transition-all duration-200"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>Disconnect</span>
            </button>
          )}
        </div>
      </footer>
    </div>
  );
}
