import React, { useMemo } from "react";
import { ChatMessage, VerificationStep } from "../types";

interface VerificationStatusProps {
  messages: ChatMessage[];
  /** compact=true renders a horizontal scrollable strip for mobile */
  compact?: boolean;
}

/**
 * Monitors the chat transcript and shows KYC step progress.
 * Detects verification steps from agent messages using keywords.
 * Supports Hindi, Hinglish, and English keywords.
 */
export default function VerificationStatus({
  messages,
  compact = false,
}: VerificationStatusProps) {
  const steps = useMemo<VerificationStep[]>(() => {
    const agentTexts = messages
      .filter((m) => m.role === "agent")
      .map((m) => m.text.toLowerCase());

    const allText = agentTexts.join(" ");

    const getStatus = (
      verifiedKeywords: string[],
      failedKeywords: string[],
      inProgressKeywords: string[]
    ): VerificationStep["status"] => {
      if (verifiedKeywords.some((kw) => allText.includes(kw))) return "verified";
      if (failedKeywords.some((kw) => allText.includes(kw))) return "failed";
      if (inProgressKeywords.some((kw) => allText.includes(kw))) return "in-progress";
      return "pending";
    };

    return [
      {
        id: "identity",
        label: "Identity Confirmation",
        status: getStatus(
          [
            // Verified keywords
            "identity confirmed", "confirm you are", "verified successfully",
            "haan sahi", "sahi hai", "customer found", "aap hi hain",
            "arjun ji", "ashish ji", "priya ji", "rajesh ji",
            "bahut accha", "great", "thank you",
          ],
          [
            "customer not found", "not found", "nahi mila",
          ],
          [
            "can you confirm", "kya aap", "your name", "naam",
            "namaste", "hello", "sanjay hoon", "video kyc",
            "shuru karte", "ready hain", "chaliye",
          ]
        ),
      },
      {
        id: "pan",
        label: "PAN Card Verification",
        status: getStatus(
          [
            "pan verified", "pan verify ho gaya", "pan card verified",
            "pan verify", "pan ho gaya", "pan verification successful",
            "pan confirm", "pan sahi hai", "pan match",
          ],
          [
            "pan does not match", "pan not match", "pan nahi",
            "pan mismatch", "pan galat",
          ],
          [
            "pan card", "show your pan", "pan dikhayiye", "pan dikha",
            "pan number", "pan ke", "apna pan",
          ]
        ),
      },
      {
        id: "aadhaar",
        label: "Aadhaar Verification",
        status: getStatus(
          [
            "aadhaar verified", "aadhaar verify", "aadhaar last 4",
            "aadhaar ho gaya", "aadhaar confirm", "aadhaar sahi",
            "aadhaar match", "aadhar verified", "aadhar verify",
            "aadhar ho gaya",
          ],
          [
            "aadhaar does not match", "aadhaar not match", "aadhaar nahi",
            "aadhaar mismatch", "aadhar does not", "aadhar nahi",
          ],
          [
            "aadhaar card", "aadhaar dikhayiye", "last 4 digits",
            "aadhaar dikha", "aadhar card", "aadhar dikha",
            "last 4", "last four",
          ]
        ),
      },
      {
        id: "photo",
        label: "Profile Photo",
        status: getStatus(
          [
            "photo capture", "photo ho gayi", "photo captured",
            "photo le li", "photo save", "profile photo",
          ],
          [],
          [
            "photo leni", "still rahiye", "camera mein seedha",
            "photo ke liye", "stay still", "profile photo",
          ]
        ),
      },
      {
        id: "face",
        label: "Face / Liveness Check",
        status: getStatus(
          [
            "face verification ho gayi", "face verify", "face verified",
            "liveness verified", "face verification complete",
            "face ho gayi", "face match",
          ],
          [
            "face does not match", "liveness failed", "face nahi",
          ],
          [
            "look at the camera", "camera ke saamne", "smile",
            "look to your", "left mein", "right mein",
            "dekhiye", "smile kar", "face verification",
          ]
        ),
      },
      {
        id: "signature",
        label: "Signature Capture",
        status: getStatus(
          [
            "signature capture", "signature ho gayi", "signature captured",
            "signature save", "signature le li",
          ],
          [],
          [
            "sign karna", "blank paper", "signature", "sign kar",
            "signed paper", "sign dikhayiye", "sign dikha",
          ]
        ),
      },
      {
        id: "complete",
        label: "KYC Complete",
        status: getStatus(
          [
            "kyc completed", "kyc successfully complete", "kyc reference",
            "kyc complete ho gaya", "kyc ho gaya", "congratulations",
            "kyc-", "successfully complete",
          ],
          [
            "kyc incomplete", "kyc failed", "kyc nahi",
          ],
          [
            "completing kyc", "finalizing", "complete kar",
          ]
        ),
      },
    ];
  }, [messages]);

  // Don't show if no verification activity yet
  const hasActivity = steps.some((s) => s.status !== "pending");
  if (!hasActivity) return null;

  // Compact horizontal strip for mobile
  if (compact) {
    return (
      <div className="flex items-center gap-3 whitespace-nowrap">
        {steps.map((step) => {
          const icon =
            step.status === "verified" ? "✓" :
            step.status === "failed"   ? "✗" :
            step.status === "in-progress" ? "…" : "○";
          const colour =
            step.status === "verified"    ? "text-green-400" :
            step.status === "failed"      ? "text-red-400" :
            step.status === "in-progress" ? "text-yellow-400 animate-pulse" :
            "text-white/30";
          return (
            <div key={step.id} className={`flex items-center gap-1 text-xs font-medium ${colour}`}>
              <span>{icon}</span>
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="bg-black/60 backdrop-blur-sm rounded-lg p-2 sm:p-3 min-w-[160px] sm:min-w-[220px]">
      <p className="text-xs font-semibold text-white/80 mb-2 uppercase tracking-wider">
        Verification Progress
      </p>
      <div className="space-y-2">
        {steps.map((step) => (
          <div key={step.id} className="flex items-center space-x-2">
            {/* Status icon */}
            {step.status === "verified" && (
              <svg className="w-4 h-4 text-green-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
            {step.status === "failed" && (
              <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            )}
            {step.status === "in-progress" && (
              <svg className="w-4 h-4 text-yellow-400 animate-pulse flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
            )}
            {step.status === "pending" && (
              <div className="w-4 h-4 rounded-full border-2 border-white/30 flex-shrink-0" />
            )}
            <span
              className={`text-xs ${
                step.status === "verified"
                  ? "text-green-300"
                  : step.status === "failed"
                  ? "text-red-300"
                  : step.status === "in-progress"
                  ? "text-yellow-300"
                  : "text-white/50"
              }`}
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
