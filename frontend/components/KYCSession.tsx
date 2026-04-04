import React, { useEffect, useRef, useState } from "react";
import { useLiveSessionWebSocket } from "../hooks/useLiveSessionWebSocket";
import { ConnectionState } from "../types";
import VerificationStatus from "./VerificationStatus";

interface KYCSessionProps {
  referenceNumber: string;
  onEndSession: () => void;
}

export default function KYCSession({
  referenceNumber,
  onEndSession,
}: KYCSessionProps) {
  const {
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
  } = useLiveSessionWebSocket();

  const [textInput, setTextInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  // Auto-connect on mount
  useEffect(() => {
    connect(referenceNumber);
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    const el = document.getElementById("chat-messages");
    if (el) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [messages]);

  const handleSendText = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim()) {
      sendTextMessage(textInput);
      setTextInput("");
    }
  };

  const handleEndSession = () => {
    disconnect();
    onEndSession();
  };

  const isConnected = connectionState === ConnectionState.CONNECTED;

  return (
    <div className="h-[100dvh] flex flex-col bg-idfc-gray-50">
      {/* Top Bar */}
      <header className="bg-idfc-maroon text-white px-4 py-3 flex items-center justify-between shadow-md z-10">
        <div className="flex items-center space-x-3">
          <span className="font-bold text-lg">Cymbal Wealth</span>
          <span className="text-white/60 text-sm">|</span>
          <span className="text-sm font-medium text-white/90">Video KYC</span>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            {/* Connection indicator */}
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                isConnected
                  ? "bg-green-400"
                  : connectionState === ConnectionState.CONNECTING
                  ? "bg-yellow-400 animate-pulse"
                  : "bg-red-400"
              }`}
            />
            <span className="text-xs font-medium text-white/80">
              {isConnected
                ? "Connected"
                : connectionState === ConnectionState.CONNECTING
                ? "Connecting..."
                : "Disconnected"}
            </span>
          </div>
          <span className="hidden sm:inline text-xs font-mono bg-white/10 px-2 py-1 rounded">
            {referenceNumber}
          </span>
          <button
            onClick={() => setShowEndConfirm(true)}
            className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded transition-colors flex items-center space-x-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            <span className="hidden sm:inline">End Session</span>
          </button>
        </div>
      </header>

      {/* Main Content - 70/30 split */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Left: Video Feed (70%) */}
        <div className="w-full md:w-[70%] h-[45vh] md:h-auto bg-idfc-gray-900 relative flex flex-col">
          {/* Video */}
          <div className="flex-1 relative">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />

            {/* Camera off overlay */}
            {!isCameraActive && isConnected && (
              <div className="absolute inset-0 bg-idfc-gray-800 flex items-center justify-center">
                <div className="text-center text-idfc-gray-400">
                  <svg className="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  </svg>
                  <p className="text-sm">Camera is off</p>
                </div>
              </div>
            )}

            {/* Not connected overlay */}
            {!isConnected && (
              <div className="absolute inset-0 bg-idfc-gray-800 flex items-center justify-center">
                <div className="text-center text-idfc-gray-400">
                  {connectionState === ConnectionState.CONNECTING ? (
                    <>
                      <svg className="animate-spin w-12 h-12 mx-auto mb-3 text-idfc-maroon" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <p className="text-sm">Connecting to Sanjay, your KYC Agent...</p>
                    </>
                  ) : (
                    <>
                      <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      <p className="text-sm">Session ended</p>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Recording indicator */}
            {isConnected && (
              <div className="absolute top-4 left-4 flex items-center space-x-2 bg-black/50 backdrop-blur-sm px-3 py-1.5 rounded-full">
                <div className="relative w-3 h-3 text-red-500 pulse-ring">
                  <div className="w-3 h-3 bg-red-500 rounded-full" />
                </div>
                <span className="text-xs text-white font-medium">REC</span>
              </div>
            )}

            {/* Verification status overlay */}
            {isConnected && (
              <div className="absolute top-4 right-4">
                <VerificationStatus messages={messages} />
              </div>
            )}
          </div>

          {/* Controls bar */}
          <div className="bg-idfc-gray-800/90 backdrop-blur px-6 py-4 flex items-center justify-center space-x-4">
            {/* Mic toggle */}
            <button
              onClick={toggleMic}
              disabled={!isConnected}
              className={`p-3 rounded-full transition-all ${
                isMicActive
                  ? "bg-idfc-gray-600 hover:bg-idfc-gray-500 text-white"
                  : "bg-red-500 hover:bg-red-600 text-white"
              } disabled:opacity-30 disabled:cursor-not-allowed`}
              title={isMicActive ? "Mute microphone" : "Unmute microphone"}
            >
              {isMicActive ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                </svg>
              )}
            </button>

            {/* Camera toggle */}
            <button
              onClick={toggleCamera}
              disabled={!isConnected}
              className={`p-3 rounded-full transition-all ${
                isCameraActive
                  ? "bg-idfc-gray-600 hover:bg-idfc-gray-500 text-white"
                  : "bg-red-500 hover:bg-red-600 text-white"
              } disabled:opacity-30 disabled:cursor-not-allowed`}
              title={isCameraActive ? "Turn off camera" : "Turn on camera"}
            >
              {isCameraActive ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                </svg>
              )}
            </button>

            {/* Switch camera (front/back) */}
            <button
              onClick={switchCamera}
              disabled={!isConnected || !isCameraActive}
              className="p-3 rounded-full bg-idfc-gray-600 hover:bg-idfc-gray-500 text-white transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              title={isRearCamera ? "Switch to front camera" : "Switch to back camera"}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>

            {/* End call */}
            <button
              onClick={() => setShowEndConfirm(true)}
              className="p-3 bg-red-600 hover:bg-red-700 text-white rounded-full transition-all"
              title="End session"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Right: Chat Panel (30%) */}
        <div className="w-full md:w-[30%] flex flex-col bg-white border-t md:border-t-0 md:border-l border-idfc-gray-200">
          {/* Chat header */}
          <div className="px-4 py-3 border-b border-idfc-gray-200 bg-idfc-gray-50">
            <h3 className="font-semibold text-idfc-gray-800 text-sm">
              KYC Session Transcript
            </h3>
            <p className="text-xs text-idfc-gray-500 mt-0.5">
              {messages.length} message{messages.length !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3" id="chat-messages">
            {messages.length === 0 && isConnected && (
              <div className="text-center py-8">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-idfc-maroon/10 mb-3">
                  <svg className="w-6 h-6 text-idfc-maroon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <p className="text-sm text-idfc-gray-500">
                  Waiting for Sanjay to connect...
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${
                    msg.role === "user"
                      ? "bg-idfc-maroon text-white rounded-br-none"
                      : "bg-idfc-gray-100 text-idfc-gray-800 rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.text}</p>
                  <p
                    className={`text-[10px] mt-1 ${
                      msg.role === "user"
                        ? "text-white/60"
                        : "text-idfc-gray-400"
                    }`}
                  >
                    {msg.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    {msg.source === "transcription" && " • voice"}
                  </p>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Text input */}
          <form
            onSubmit={handleSendText}
            className="px-4 py-3 border-t border-idfc-gray-200 bg-idfc-gray-50"
          >
            <div className="flex space-x-2">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder={
                  isConnected ? "Type a message..." : "Not connected"
                }
                disabled={!isConnected}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-idfc-gray-300 focus:ring-2 focus:ring-idfc-maroon/30 focus:border-idfc-maroon outline-none disabled:bg-idfc-gray-100 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={!isConnected || !textInput.trim()}
                className="px-4 py-2 bg-idfc-maroon hover:bg-idfc-maroon-dark text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* End session confirmation modal */}
      {showEndConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-4 sm:p-6 max-w-sm mx-4">
            <h3 className="text-lg font-bold text-idfc-gray-900">
              End KYC Session?
            </h3>
            <p className="mt-2 text-sm text-idfc-gray-600">
              Are you sure you want to end this Video KYC session? If
              verification is incomplete, you may need to start over.
            </p>
            <div className="mt-6 flex space-x-3 justify-end">
              <button
                onClick={() => setShowEndConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-idfc-gray-700 hover:bg-idfc-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleEndSession}
                className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                End Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
