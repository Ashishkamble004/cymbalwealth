"use client";

import { useState, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface KYCResult {
  name: string;
  dob: string;
  address: string;
  pan: string;
  aadhaar_last4: string;
  annual_income_estimate: number;
  risk_flags: string[];
  kyc_status: string;
}

interface RiskQuestion {
  question: string;
  options: { text: string; score: number }[];
}

export default function KYCUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [kycResult, setKycResult] = useState<KYCResult | null>(null);
  const [questionnaire, setQuestionnaire] = useState<RiskQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [riskProfile, setRiskProfile] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setKycResult(null);
    setQuestionnaire([]);

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    try {
      const res = await fetch(`${API_URL}/onboarding/analyze-docs`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setKycResult(data.kyc_data);
      setQuestionnaire(data.risk_questionnaire || []);
    } catch {
      alert("Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const submitRiskProfile = async () => {
    const answerScores = Object.values(answers);
    if (answerScores.length !== questionnaire.length) {
      alert("Please answer all questions.");
      return;
    }

    try {
      const res = await fetch(`${API_URL}/onboarding/risk-score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: 1, answers: answerScores }),
      });
      const data = await res.json();
      setRiskProfile(data.risk_profile);
    } catch {
      alert("Failed to submit risk profile.");
    }
  };

  return (
    <div className="card max-w-2xl mx-auto">
      <h2 className="text-lg font-semibold text-white mb-4">
        📄 KYC Document Upload
      </h2>
      <p className="text-sm text-gray-400 mb-6">
        Upload KYC documents (Aadhaar, PAN, ITR, bank statement) for
        AI-powered analysis and verification.
      </p>

      {/* File Upload */}
      <div className="mb-6">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full rounded-lg border-2 border-dashed border-gray-700 p-8 text-center transition hover:border-indigo-500"
        >
          <p className="text-sm text-gray-400">
            {files.length > 0
              ? `${files.length} file(s) selected: ${files.map((f) => f.name).join(", ")}`
              : "Click to select KYC documents"}
          </p>
        </button>

        <button
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
          className="mt-4 w-full rounded-lg bg-indigo-600 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {uploading ? "Analyzing with Gemini AI..." : "Upload & Analyze"}
        </button>
      </div>

      {/* KYC Results */}
      {kycResult && (
        <div className="mb-6 rounded-lg border border-gray-800 bg-gray-800/50 p-4">
          <h3 className="text-sm font-semibold text-white mb-3">
            Extracted Information
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-400">Name</p>
              <p className="text-white">{kycResult.name || "—"}</p>
            </div>
            <div>
              <p className="text-gray-400">Date of Birth</p>
              <p className="text-white">{kycResult.dob || "—"}</p>
            </div>
            <div>
              <p className="text-gray-400">PAN</p>
              <p className="text-white font-mono">{kycResult.pan || "—"}</p>
            </div>
            <div>
              <p className="text-gray-400">Aadhaar (last 4)</p>
              <p className="text-white font-mono">
                {kycResult.aadhaar_last4 || "—"}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-gray-400">Address</p>
              <p className="text-white">{kycResult.address || "—"}</p>
            </div>
            <div>
              <p className="text-gray-400">Annual Income Estimate</p>
              <p className="text-white">
                ₹{(kycResult.annual_income_estimate || 0).toLocaleString("en-IN")}
              </p>
            </div>
            <div>
              <p className="text-gray-400">KYC Status</p>
              <span
                className={`badge ${
                  kycResult.kyc_status === "verified"
                    ? "badge-green"
                    : kycResult.kyc_status === "flagged"
                    ? "badge-red"
                    : "badge-yellow"
                }`}
              >
                {kycResult.kyc_status}
              </span>
            </div>
          </div>
          {kycResult.risk_flags.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-red-400 font-medium">
                ⚠ Risk Flags: {kycResult.risk_flags.join(", ")}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Risk Questionnaire */}
      {questionnaire.length > 0 && !riskProfile && (
        <div className="rounded-lg border border-gray-800 bg-gray-800/50 p-4">
          <h3 className="text-sm font-semibold text-white mb-4">
            Risk Profiling Questionnaire
          </h3>
          <div className="space-y-5">
            {questionnaire.map((q, qi) => (
              <div key={qi}>
                <p className="text-sm text-gray-200 mb-2">
                  {qi + 1}. {q.question}
                </p>
                <div className="space-y-1.5">
                  {q.options.map((opt, oi) => (
                    <label
                      key={oi}
                      className={`flex cursor-pointer items-center gap-2 rounded-lg border p-2.5 text-sm transition ${
                        answers[qi] === opt.score
                          ? "border-indigo-500 bg-indigo-500/10 text-white"
                          : "border-gray-700 text-gray-400 hover:border-gray-600"
                      }`}
                    >
                      <input
                        type="radio"
                        name={`q${qi}`}
                        value={opt.score}
                        checked={answers[qi] === opt.score}
                        onChange={() =>
                          setAnswers((prev) => ({ ...prev, [qi]: opt.score }))
                        }
                        className="accent-indigo-500"
                      />
                      {opt.text}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={submitRiskProfile}
            className="mt-4 w-full rounded-lg bg-indigo-600 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500"
          >
            Submit & Get Risk Profile
          </button>
        </div>
      )}

      {/* Risk Profile Result */}
      {riskProfile && (
        <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-center">
          <p className="text-sm text-emerald-400 font-medium">
            Risk Profile Assigned
          </p>
          <p className="mt-1 text-2xl font-bold text-white">{riskProfile}</p>
        </div>
      )}
    </div>
  );
}
