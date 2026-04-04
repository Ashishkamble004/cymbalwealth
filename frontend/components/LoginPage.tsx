import React, { useState } from "react";

// Valid reference numbers for demo
const VALID_REFS = ["CW-2026-001", "CW-2026-002"];

interface LoginPageProps {
  onLogin: (referenceNumber: string) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [refNumber, setRefNumber] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(false);

    const ref = refNumber.trim().toUpperCase();
    if (!ref) {
      setError("Please enter your Customer Reference Number");
      return;
    }

    if (!VALID_REFS.includes(ref)) {
      setError(
        "Invalid reference number. Please check and try again."
      );
      return;
    }

    setIsLoading(true);
    onLogin(ref);
  };

  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Header */}
      <header className="bg-idfc-maroon text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {/* Cymbal Wealth Logo Text */}
            <div>
              <span className="text-xl font-bold tracking-tight">
                Cymbal Wealth
              </span>
            </div>
          </div>
          <div className="text-sm font-medium opacity-90">Video KYC Portal</div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex items-center justify-center px-4 py-6 sm:py-12">
        <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-12 items-center">
          {/* Left side - Info */}
          <div className="space-y-6 order-last lg:order-first">
            <div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-idfc-gray-900 leading-tight">
                Complete Your{" "}
                <span className="text-idfc-maroon">Video KYC</span>
                <br />
                From Anywhere
              </h1>
              <p className="mt-4 text-lg text-idfc-gray-600 leading-relaxed">
                Complete your Know Your Customer verification through a
                quick and secure video call with our AI-powered KYC agent.
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-idfc-maroon/10 flex items-center justify-center">
                  <svg className="w-4 h-4 text-idfc-maroon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-idfc-gray-800">Quick &amp; Easy</p>
                  <p className="text-sm text-idfc-gray-500">Complete in just 5-7 minutes</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-idfc-maroon/10 flex items-center justify-center">
                  <svg className="w-4 h-4 text-idfc-maroon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-idfc-gray-800">Secure &amp; Encrypted</p>
                  <p className="text-sm text-idfc-gray-500">End-to-end secure video session</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-idfc-maroon/10 flex items-center justify-center">
                  <svg className="w-4 h-4 text-idfc-maroon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-idfc-gray-800">AI-Powered Verification</p>
                  <p className="text-sm text-idfc-gray-500">Smart agent guides you through the process</p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-idfc-gray-200">
              <p className="text-xs text-idfc-gray-400">
                Keep your PAN Card and Aadhaar Card ready before starting the
                video KYC process.
              </p>
            </div>
          </div>

          {/* Right side - Login Form */}
          <div className="bg-white rounded-2xl shadow-xl border border-idfc-gray-200 p-5 sm:p-8">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-idfc-maroon/10 mb-4">
                <svg className="w-8 h-8 text-idfc-maroon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-idfc-gray-900">
                Start Video KYC
              </h2>
              <p className="mt-2 text-sm text-idfc-gray-500">
                Enter the Customer Reference Number from your account
                opening letter or email
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label
                  htmlFor="refNumber"
                  className="block text-sm font-medium text-idfc-gray-700 mb-2"
                >
                  Customer Reference Number
                </label>
                <input
                  id="refNumber"
                  type="text"
                  value={refNumber}
                  onChange={(e) => {
                    setRefNumber(e.target.value.toUpperCase());
                    setError("");
                  }}
                  placeholder="e.g., CW-2026-001"
                  className="w-full px-4 py-3 rounded-lg border border-idfc-gray-300 focus:ring-2 focus:ring-idfc-maroon/50 focus:border-idfc-maroon outline-none transition-all text-idfc-gray-900 placeholder-idfc-gray-400 text-center font-mono text-lg tracking-wider"
                  autoFocus
                  autoComplete="off"
                />
                {error && (
                  <p className="mt-2 text-sm text-red-600 flex items-center space-x-1">
                    <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <span>{error}</span>
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 bg-idfc-maroon hover:bg-idfc-maroon-dark text-white font-semibold rounded-lg shadow-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Verifying...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>Start Video KYC</span>
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-xs text-idfc-gray-400">
                By proceeding, you consent to video recording as per
                Video KYC guidelines
              </p>
            </div>

            {/* Demo hint - only shown in non-production */}
            {import.meta.env.DEV && (
              <div className="mt-6 pt-6 border-t border-idfc-gray-100">
                <p className="text-xs text-idfc-gray-400 text-center mb-3">
                  Dev Mode — Demo Reference Numbers
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {VALID_REFS.map((ref) => (
                    <button
                      key={ref}
                      type="button"
                      onClick={() => {
                        setRefNumber(ref);
                        setError("");
                      }}
                      className="px-3 py-1.5 text-xs font-mono bg-idfc-gray-50 hover:bg-idfc-maroon/5 text-idfc-gray-600 hover:text-idfc-maroon rounded-md border border-idfc-gray-200 transition-colors"
                    >
                      {ref}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-idfc-gray-50 border-t border-idfc-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-idfc-gray-400">
          <span>&copy; {new Date().getFullYear()} Cymbal Wealth. All rights reserved.</span>
          <span>Powered by Google Gemini</span>
        </div>
      </footer>
    </div>
  );
}
