import React, { useState, useCallback } from "react";
import LandingPage from "./components/LandingPage";
import LoginPage from "./components/LoginPage";
import KYCSession from "./components/KYCSession";

type AppView = "landing" | "login" | "kyc";

export default function App() {
  const [view, setView] = useState<AppView>("landing");
  const [referenceNumber, setReferenceNumber] = useState("");

  const handleStartKYC = useCallback(() => {
    setView("login");
  }, []);

  const handleLogin = useCallback((ref: string) => {
    setReferenceNumber(ref);
    setView("kyc");
  }, []);

  const handleEndSession = useCallback(() => {
    setView("landing");
    setReferenceNumber("");
  }, []);

  return (
    <div className="min-h-screen bg-idfc-gray-50">
      {view === "landing" && <LandingPage onStartKYC={handleStartKYC} />}
      {view === "login" && <LoginPage onLogin={handleLogin} />}
      {view === "kyc" && (
        <KYCSession
          referenceNumber={referenceNumber}
          onEndSession={handleEndSession}
        />
      )}
    </div>
  );
}
