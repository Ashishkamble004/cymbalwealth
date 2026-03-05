"use client";

import { useEffect, useState } from "react";
import CopilotPanel from "@/app/components/rm/CopilotPanel";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ClientSummary {
  id: number;
  name: string;
  segment: string;
  risk_profile: string;
  aum: number;
  total_return_pct: number;
  goals_count: number;
  holdings_count: number;
}

function formatINR(value: number): string {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)} Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)} L`;
  return `₹${value.toLocaleString("en-IN")}`;
}

function segmentBadge(segment: string) {
  const cls =
    segment === "UHNI"
      ? "badge-blue"
      : segment === "HNI"
      ? "badge-green"
      : "badge-yellow";
  return <span className={`badge ${cls}`}>{segment}</span>;
}

export default function RMDashboard() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/rm/copilot/clients-summary`)
      .then((r) => r.json())
      .then((data) => {
        setClients(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">RM Dashboard</h1>
        <p className="mt-1 text-sm text-gray-400">
          Welcome back, Vikram. Here&apos;s your client portfolio overview.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <p className="card-header">Total AUM</p>
          <p className="text-2xl font-bold text-white">
            {formatINR(clients.reduce((s, c) => s + c.aum, 0))}
          </p>
        </div>
        <div className="card">
          <p className="card-header">Active Clients</p>
          <p className="text-2xl font-bold text-white">{clients.length}</p>
        </div>
        <div className="card">
          <p className="card-header">Avg Return</p>
          <p className="text-2xl font-bold text-emerald-400">
            {clients.length > 0
              ? (
                  clients.reduce((s, c) => s + c.total_return_pct, 0) /
                  clients.length
                ).toFixed(1)
              : 0}
            %
          </p>
        </div>
        <div className="card">
          <p className="card-header">Total Goals</p>
          <p className="text-2xl font-bold text-white">
            {clients.reduce((s, c) => s + c.goals_count, 0)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Client List */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="card-header">Client Book</h2>
            {loading ? (
              <p className="text-sm text-gray-500">Loading clients...</p>
            ) : (
              <div className="space-y-3">
                {clients.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setSelectedClientId(c.id)}
                    className={`w-full rounded-lg border p-4 text-left transition ${
                      selectedClientId === c.id
                        ? "border-indigo-500 bg-indigo-500/10"
                        : "border-gray-800 hover:border-gray-700 hover:bg-gray-800/50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-white">{c.name}</p>
                        <p className="mt-0.5 text-xs text-gray-400">
                          {formatINR(c.aum)} · {c.risk_profile} ·{" "}
                          {c.holdings_count} holdings
                        </p>
                      </div>
                      <div className="text-right">
                        {segmentBadge(c.segment)}
                        <p
                          className={`mt-1 text-sm font-medium ${
                            c.total_return_pct >= 0
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {c.total_return_pct >= 0 ? "+" : ""}
                          {c.total_return_pct.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Copilot Panel */}
        <div className="lg:col-span-3">
          {selectedClientId ? (
            <CopilotPanel clientId={selectedClientId} />
          ) : (
            <div className="card flex min-h-[400px] items-center justify-center">
              <p className="text-sm text-gray-500">
                Select a client to view the AI-powered pre-call brief
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
