import React, { useState, useRef, useEffect, useCallback } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
}

const SUGGESTED_QUERIES = [
  "What is the Nifty 50 at right now?",
  "Get me a quote for Reliance Industries",
  "Compare TCS, Infosys and Wipro",
  "Top 5 Nifty 50 gainers today",
  "How has HDFC Bank performed in 6 months?",
  "Show IT sector performance",
  "Give me financials for Asian Paints",
  "What is the Sensex at?",
];

const INVESTMENTS_API_URL =
  (window as any).INVESTMENTS_API_URL ||
  import.meta.env?.VITE_INVESTMENTS_API_URL ||
  "https://nse-bse-mcp-server-mcj3w7ujpq-uc.a.run.app";

interface InvestmentsPageProps {
  onBack: () => void;
}

export default function InvestmentsPage({ onBack }: InvestmentsPageProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      text: `Hello! I'm your **NSE/BSE Market Intelligence** assistant, powered by Google ADK and live market data.

I can help you with:
- Real-time stock quotes for any NSE/BSE listed company
- Live index data: Nifty 50, Sensex, Nifty Bank, Nifty IT
- Historical price data and trend analysis
- Stock comparisons and sector performance
- Company financials and fundamentals

Try one of the suggested queries below or type your own question.`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isLoading) return;

      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: "user",
        text: query.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const res = await fetch(`${INVESTMENTS_API_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query.trim() }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const botMsg: Message = {
          id: `a-${Date.now()}`,
          role: "assistant",
          text: data.response || data.text || "No response received.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, botMsg]);
      } catch (err) {
        const errMsg: Message = {
          id: `err-${Date.now()}`,
          role: "assistant",
          text: `⚠️ Could not connect to the Investments AI backend.\n\nMake sure the MCP server is running at **${INVESTMENTS_API_URL}**.\n\nOnce deployed to Cloud Run, set the backend URL and I'll be fully operational.`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [isLoading]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const formatText = (text: string) => {
    // Basic markdown-like formatting for bold and newlines
    return text.split("\n").map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g).map((part, j) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return <strong key={j}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });
      return (
        <span key={i}>
          {parts}
          {i < text.split("\n").length - 1 && <br />}
        </span>
      );
    });
  };

  const formatTime = (d: Date) =>
    d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="min-h-screen flex flex-col bg-idfc-gray-50">
      {/* Header / Nav */}
      <nav className="bg-white border-b border-idfc-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBack}
              className="text-idfc-gray-400 hover:text-idfc-gray-600 transition-colors"
              aria-label="Go back"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <span className="text-xl font-bold text-idfc-maroon tracking-tight">
              Cymbal Wealth
            </span>
            <span className="text-sm text-idfc-gray-400">/ Investments / Market Intelligence</span>
          </div>
          <div className="flex items-center space-x-3">
            <span className="hidden sm:flex items-center space-x-1.5 text-xs font-medium text-green-600 bg-green-50 border border-green-200 rounded-full px-3 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
              <span>Live Market Data</span>
            </span>
            <div className="w-9 h-9 rounded-full bg-idfc-maroon flex items-center justify-center text-white text-sm font-bold">
              AK
            </div>
          </div>
        </div>
      </nav>

      {/* Page header */}
      <div className="bg-white border-b border-idfc-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-idfc-maroon/10 flex items-center justify-center text-idfc-maroon flex-shrink-0">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-idfc-gray-900">NSE/BSE Market Intelligence</h1>
            <p className="text-sm text-idfc-gray-500 mt-0.5">
              AI-powered stock market assistant — NSE &amp; BSE data via MCP + Google ADK
            </p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 flex gap-6">

        {/* Chat panel */}
        <div className="flex-1 flex flex-col bg-white rounded-2xl border border-idfc-gray-200 shadow-sm overflow-hidden min-h-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ minHeight: 0, maxHeight: "calc(100vh - 340px)" }}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-idfc-maroon flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mr-2.5 mt-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                )}
                <div className="max-w-[80%]">
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                      msg.role === "user"
                        ? "bg-idfc-maroon text-white rounded-tr-sm"
                        : "bg-idfc-gray-50 border border-idfc-gray-200 text-idfc-gray-900 rounded-tl-sm"
                    }`}
                  >
                    {msg.role === "assistant" ? formatText(msg.text) : msg.text}
                  </div>
                  <p className={`text-xs text-idfc-gray-400 mt-1 ${msg.role === "user" ? "text-right" : "text-left"}`}>
                    {formatTime(msg.timestamp)}
                  </p>
                </div>
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-idfc-gray-200 flex items-center justify-center text-idfc-gray-600 text-xs font-bold flex-shrink-0 ml-2.5 mt-1">
                    AK
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="w-8 h-8 rounded-full bg-idfc-maroon flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mr-2.5 mt-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div className="bg-idfc-gray-50 border border-idfc-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center space-x-1.5">
                  <span className="w-2 h-2 bg-idfc-maroon/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-2 h-2 bg-idfc-maroon/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-2 h-2 bg-idfc-maroon/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggested queries */}
          <div className="border-t border-idfc-gray-100 px-4 pt-3 pb-2">
            <p className="text-xs text-idfc-gray-400 font-medium mb-2">Suggested queries</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUERIES.slice(0, 4).map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  disabled={isLoading}
                  className="text-xs px-3 py-1.5 rounded-full border border-idfc-maroon/30 text-idfc-maroon hover:bg-idfc-maroon hover:text-white transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="border-t border-idfc-gray-200 p-4">
            <div className="flex items-end space-x-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                placeholder="Ask about any NSE/BSE stock, index, or sector..."
                rows={1}
                className="flex-1 resize-none rounded-xl border border-idfc-gray-300 focus:border-idfc-maroon focus:ring-2 focus:ring-idfc-maroon/20 outline-none px-4 py-3 text-sm text-idfc-gray-900 placeholder-idfc-gray-400 disabled:bg-idfc-gray-50 transition-all"
                style={{ maxHeight: "120px" }}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = Math.min(el.scrollHeight, 120) + "px";
                }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={isLoading || !input.trim()}
                className="flex-shrink-0 w-11 h-11 rounded-xl bg-idfc-maroon hover:bg-idfc-maroon-dark disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-all duration-150 shadow-sm"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-idfc-gray-400 mt-2 text-center">
              Press Enter to send · Shift+Enter for new line · Data from Yahoo Finance (NSE/BSE)
            </p>
          </div>
        </div>

        {/* Right sidebar — market info */}
        <div className="hidden lg:flex flex-col w-72 space-y-4 flex-shrink-0">

          {/* MCP Tools */}
          <div className="bg-white rounded-2xl border border-idfc-gray-200 p-5">
            <h3 className="text-sm font-bold text-idfc-gray-900 mb-3 flex items-center space-x-2">
              <svg className="w-4 h-4 text-idfc-maroon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
              </svg>
              <span>Available Tools</span>
            </h3>
            <div className="space-y-2">
              {[
                { tool: "get_stock_quote", label: "Stock Quote", desc: "Live price, P/E, 52W range" },
                { tool: "get_index_data", label: "Index Data", desc: "Nifty 50, Sensex, Bank Nifty" },
                { tool: "get_historical_data", label: "Historical Data", desc: "OHLCV up to 5 years" },
                { tool: "compare_stocks", label: "Compare Stocks", desc: "Side-by-side 2–5 stocks" },
                { tool: "get_top_movers", label: "Top Movers", desc: "Nifty 50 gainers & losers" },
                { tool: "get_sector_performance", label: "Sector Performance", desc: "IT, Banking, Pharma..." },
                { tool: "get_company_info", label: "Company Info", desc: "Business, sector, HQ" },
                { tool: "get_financials", label: "Financials", desc: "Revenue, ROE, debt/equity" },
              ].map(({ label, desc }) => (
                <div key={label} className="flex items-start space-x-2.5 py-1">
                  <div className="w-5 h-5 rounded-full bg-idfc-maroon/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-2.5 h-2.5 text-idfc-maroon" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-idfc-gray-800">{label}</p>
                    <p className="text-xs text-idfc-gray-500">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* More suggested queries */}
          <div className="bg-white rounded-2xl border border-idfc-gray-200 p-5">
            <h3 className="text-sm font-bold text-idfc-gray-900 mb-3">More Queries</h3>
            <div className="space-y-2">
              {SUGGESTED_QUERIES.slice(4).map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  disabled={isLoading}
                  className="w-full text-left text-xs text-idfc-gray-700 hover:text-idfc-maroon hover:bg-idfc-maroon/5 rounded-lg px-3 py-2 transition-all duration-150 disabled:opacity-40 border border-transparent hover:border-idfc-maroon/20"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <p className="text-xs text-amber-700 leading-relaxed">
              <strong>Disclaimer:</strong> Data sourced from Yahoo Finance for informational purposes only. Not financial advice. Verify with official NSE/BSE feeds before making investment decisions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
