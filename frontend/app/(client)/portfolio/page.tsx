"use client";

import { useEffect, useState } from "react";
import HoldingsTable from "@/app/components/portfolio/HoldingsTable";
import AllocationChart from "@/app/components/portfolio/AllocationChart";
import VoiceAssistant from "@/app/components/voice/VoiceAssistant";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PortfolioData {
  client_id: number;
  client_name: string;
  segment: string;
  risk_profile: string;
  total_invested: number;
  total_current_value: number;
  total_unrealized_pnl: number;
  total_return_pct: number;
  holdings: Holding[];
  allocation: Record<string, number>;
  goals: Goal[];
}

interface Holding {
  instrument_name: string;
  instrument_type: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  invested_value: number;
  current_value: number;
  unrealized_pnl: number;
  return_pct: number;
}

interface Goal {
  name: string;
  target_amount: number;
  current_amount: number;
  target_year: number;
  progress_pct: number;
}

interface ClientOption {
  id: number;
  name: string;
  segment: string;
}

function formatINR(value: number): string {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
  return `₹${value.toLocaleString("en-IN")}`;
}

export default function PortfolioPage() {
  const [clients, setClients] = useState<ClientOption[]>([]);
  const [selectedId, setSelectedId] = useState<number>(1);
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [commentary, setCommentary] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [showVoice, setShowVoice] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/onboarding/clients`)
      .then((r) => r.json())
      .then(setClients)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    fetch(`${API_URL}/portfolio/${selectedId}`)
      .then((r) => r.json())
      .then(setPortfolio)
      .catch(() => {});
  }, [selectedId]);

  const streamCommentary = () => {
    setCommentary("");
    setStreaming(true);
    const es = new EventSource(
      `${API_URL}/portfolio/${selectedId}/commentary`
    );
    es.onmessage = (e) => {
      if (e.data === "[DONE]") {
        es.close();
        setStreaming(false);
        return;
      }
      try {
        const parsed = JSON.parse(e.data);
        if (parsed.token) {
          setCommentary((prev) => prev + parsed.token);
        } else {
          setCommentary((prev) => prev + e.data);
        }
      } catch {
        setCommentary((prev) => prev + e.data);
      }
    };
    es.onerror = () => {
      es.close();
      setStreaming(false);
    };
  };

  if (!portfolio) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-8">
        <p className="text-gray-400">Loading portfolio...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {portfolio.client_name}
          </h1>
          <p className="mt-1 text-sm text-gray-400">
            {portfolio.segment} · {portfolio.risk_profile} Risk Profile
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(Number(e.target.value))}
            className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
          >
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setShowVoice(!showVoice)}
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 transition hover:bg-gray-800"
          >
            {showVoice ? "Hide Aria" : "🎤 Talk to Aria"}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="card">
          <p className="card-header">Current Value</p>
          <p className="text-xl font-bold text-white">
            {formatINR(portfolio.total_current_value)}
          </p>
        </div>
        <div className="card">
          <p className="card-header">Total Invested</p>
          <p className="text-xl font-bold text-gray-300">
            {formatINR(portfolio.total_invested)}
          </p>
        </div>
        <div className="card">
          <p className="card-header">Unrealized P&L</p>
          <p
            className={`text-xl font-bold ${
              portfolio.total_unrealized_pnl >= 0
                ? "text-emerald-400"
                : "text-red-400"
            }`}
          >
            {portfolio.total_unrealized_pnl >= 0 ? "+" : ""}
            {formatINR(portfolio.total_unrealized_pnl)}
          </p>
        </div>
        <div className="card">
          <p className="card-header">Total Return</p>
          <p
            className={`text-xl font-bold ${
              portfolio.total_return_pct >= 0
                ? "text-emerald-400"
                : "text-red-400"
            }`}
          >
            {portfolio.total_return_pct >= 0 ? "+" : ""}
            {portfolio.total_return_pct.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Voice Assistant */}
      {showVoice && (
        <div className="mb-8">
          <VoiceAssistant clientId={selectedId} clientName={portfolio.client_name} />
        </div>
      )}

      {/* Goals */}
      <div className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-white">
          Financial Goals
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {portfolio.goals.map((g, i) => (
            <div key={i} className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-white">{g.name}</p>
                  <p className="mt-1 text-xs text-gray-400">
                    Target: {formatINR(g.target_amount)} by {g.target_year}
                  </p>
                </div>
                <span className="text-sm font-bold text-indigo-400">
                  {g.progress_pct.toFixed(0)}%
                </span>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-gray-800">
                <div
                  className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all"
                  style={{ width: `${Math.min(g.progress_pct, 100)}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Current: {formatINR(g.current_amount)}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Holdings & Allocation */}
      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <HoldingsTable holdings={portfolio.holdings} />
        </div>
        <div>
          <AllocationChart allocation={portfolio.allocation} />
        </div>
      </div>

      {/* AI Commentary */}
      <div className="card">
        <div className="flex items-center justify-between">
          <h2 className="card-header mb-0">AI Portfolio Commentary</h2>
          <button
            onClick={streamCommentary}
            disabled={streaming}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {streaming ? "Generating..." : "✨ Generate Commentary"}
          </button>
        </div>
        {commentary && (
          <div className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
            {commentary}
            {streaming && (
              <span className="ml-1 inline-block h-4 w-1.5 animate-pulse bg-indigo-400" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
