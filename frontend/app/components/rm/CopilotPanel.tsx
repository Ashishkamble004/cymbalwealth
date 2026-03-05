"use client";

import { useEffect, useState, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  clientId: number;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function CopilotPanel({ clientId }: Props) {
  const [brief, setBrief] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    setBrief(null);
    setChatMessages([]);
    fetch(`${API_URL}/rm/copilot/brief/${clientId}`)
      .then((r) => r.json())
      .then((data) => {
        setBrief(data.brief);
        setLoading(false);
      })
      .catch(() => {
        setBrief("Failed to load brief. Please try again.");
        setLoading(false);
      });
  }, [clientId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    const updated = [...chatMessages, userMsg];
    setChatMessages(updated);
    setInput("");
    setChatLoading(true);

    try {
      const res = await fetch(`${API_URL}/rm/copilot/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId, messages: updated }),
      });
      const data = await res.json();
      setChatMessages([
        ...updated,
        { role: "assistant", content: data.response },
      ]);
    } catch {
      setChatMessages([
        ...updated,
        { role: "assistant", content: "Failed to get response. Please retry." },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Simple markdown-like rendering for the brief
  const renderBrief = (text: string) => {
    return text.split("\n").map((line, i) => {
      if (line.startsWith("## ")) {
        return (
          <h3 key={i} className="mt-4 mb-2 text-sm font-bold text-indigo-400 uppercase tracking-wide">
            {line.replace("## ", "")}
          </h3>
        );
      }
      if (line.startsWith("- ")) {
        return (
          <li key={i} className="ml-4 text-sm text-gray-300 list-disc">
            {line.replace("- ", "")}
          </li>
        );
      }
      if (line.trim() === "") {
        return <br key={i} />;
      }
      return (
        <p key={i} className="text-sm text-gray-300 leading-relaxed">
          {line}
        </p>
      );
    });
  };

  return (
    <div className="card">
      <h2 className="card-header flex items-center gap-2">
        🤖 AI Copilot Brief
      </h2>

      {loading ? (
        <div className="flex items-center gap-3 py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <p className="text-sm text-gray-400">Generating pre-call brief with Gemini...</p>
        </div>
      ) : brief ? (
        <div className="mb-6 max-h-96 overflow-y-auto pr-2">
          {renderBrief(brief)}
        </div>
      ) : null}

      {/* Follow-up Chat */}
      <div className="border-t border-gray-800 pt-4">
        <h3 className="mb-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Follow-up Chat
        </h3>

        <div className="max-h-48 overflow-y-auto space-y-2 mb-3">
          {chatMessages.map((m, i) => (
            <div
              key={i}
              className={`rounded-lg px-3 py-2 text-sm ${
                m.role === "user"
                  ? "ml-8 bg-indigo-500/20 text-indigo-200"
                  : "mr-8 bg-gray-800 text-gray-300"
              }`}
            >
              {m.content}
            </div>
          ))}
          {chatLoading && (
            <div className="mr-8 rounded-lg bg-gray-800 px-3 py-2 text-sm text-gray-500">
              Thinking...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask about this client..."
            className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
          />
          <button
            onClick={sendMessage}
            disabled={chatLoading || !input.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
