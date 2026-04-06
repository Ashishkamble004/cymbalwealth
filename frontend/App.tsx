import React, { useState, useCallback } from "react";
import LandingPage from "./components/LandingPage";
import LoginPage from "./components/LoginPage";
import KYCSession from "./components/KYCSession";
import InvestmentsPage from "./components/InvestmentsPage";
import CustomerSupportPage from "./components/CustomerSupportPage";

type AppView = "landing" | "login" | "kyc" | "investments" | "customer-support";

function getInitialView(): AppView {
  const hash = window.location.hash.slice(1);
  if (hash === "customer-support") return "customer-support";
  return "landing";
}

export default function App() {
  const [view, setView] = useState<AppView>(getInitialView);
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

  const handleStartInvestments = useCallback(() => {
    setView("investments");
  }, []);

  const handleStartCustomerSupport = useCallback(() => {
    setView("customer-support");
  }, []);

  return (
    <div className="min-h-screen bg-idfc-gray-50">
      {view === "landing" && (
        <LandingPage
          onStartKYC={handleStartKYC}
          onStartInvestments={handleStartInvestments}
          onStartCustomerSupport={handleStartCustomerSupport}
        />
      )}
      {view === "login" && <LoginPage onLogin={handleLogin} />}
      {view === "kyc" && (
        <KYCSession
          referenceNumber={referenceNumber}
          onEndSession={handleEndSession}
        />
      )}
      {view === "investments" && (
        <InvestmentsPage onBack={handleEndSession} />
      )}
      {view === "customer-support" && (
        <CustomerSupportPage onBack={() => setView("landing")} />
      )}
    </div>
  );
}
