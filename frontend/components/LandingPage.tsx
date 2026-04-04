import React from "react";

interface LandingPageProps {
  onStartKYC: () => void;
  onStartInvestments: () => void;
}

export default function LandingPage({ onStartKYC, onStartInvestments }: LandingPageProps) {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Header */}
      <header className="bg-white border-b border-idfc-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <span className="text-2xl font-bold text-idfc-maroon tracking-tight">
            Cymbal Wealth
          </span>
          <nav className="hidden md:flex items-center space-x-8 text-sm font-medium text-idfc-gray-600">
            <a href="#services" className="hover:text-idfc-maroon transition-colors">Services</a>
            <a href="#about" className="hover:text-idfc-maroon transition-colors">About</a>
            <a href="#contact" className="hover:text-idfc-maroon transition-colors">Contact</a>
          </nav>
          <button className="md:hidden p-2 text-idfc-gray-600 hover:text-idfc-maroon" aria-label="Menu">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="flex-1 flex items-center bg-gradient-to-br from-white via-idfc-gray-50 to-idfc-maroon/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 md:py-20 grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16 items-center">
          <div className="space-y-8">
            <div>
              <p className="text-sm font-semibold text-idfc-maroon uppercase tracking-wider mb-3">
                Wealth Management
              </p>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-idfc-gray-900 leading-tight">
                Your Wealth,
                <br />
                <span className="text-idfc-maroon">Our Expertise</span>
              </h1>
              <p className="mt-6 text-base sm:text-lg md:text-xl text-idfc-gray-600 leading-relaxed max-w-lg">
                Cymbal Wealth offers personalized wealth management, investment
                advisory, and financial planning services to help you build and
                preserve your legacy.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-3">
              <button
                onClick={onStartKYC}
                className="w-full sm:w-auto px-8 py-4 bg-idfc-maroon hover:bg-idfc-maroon-dark text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center space-x-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span>Complete Video KYC</span>
              </button>
              <button
                onClick={onStartInvestments}
                className="w-full sm:w-auto px-8 py-4 bg-idfc-maroon hover:bg-idfc-maroon-dark text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center space-x-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                <span>Investments</span>
              </button>
              <a
                href="#services"
                className="px-8 py-4 border-2 border-idfc-gray-300 text-idfc-gray-700 font-semibold rounded-xl hover:border-idfc-maroon hover:text-idfc-maroon transition-all duration-200"
              >
                Explore Services
              </a>
            </div>

            {/* Trust badges */}
            <div className="flex flex-wrap gap-4 pt-4">
              <div className="flex items-center space-x-2 text-idfc-gray-500">
                <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-medium">Secure & Regulated</span>
              </div>
              <div className="flex items-center space-x-2 text-idfc-gray-500">
                <svg className="w-5 h-5 text-idfc-maroon" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                </svg>
                <span className="text-sm font-medium">10,000+ Clients</span>
              </div>
            </div>
          </div>

          {/* Right side - Feature cards */}
          <div className="space-y-4">
            {[
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                ),
                title: "Investment Advisory",
                desc: "Tailored investment strategies across equities, fixed income, and alternative assets.",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                ),
                title: "Estate & Trust Planning",
                desc: "Comprehensive planning for wealth transfer and legacy preservation.",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                ),
                title: "Portfolio Management",
                desc: "Active portfolio management with real-time monitoring and rebalancing.",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ),
                title: "Tax Optimization",
                desc: "Strategic tax planning to maximize your after-tax returns.",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                ),
                title: "Investments — NSE/BSE Market Intelligence",
                desc: "AI-powered stock market assistant. Get live quotes, index data, sector performance, and company financials for any NSE/BSE listed stock — powered by MCP + Google ADK.",
                onClick: onStartInvestments,
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                  </svg>
                ),
                title: "Hyper-Personalized Marketing",
                desc: "AI-generated 30-second video ads tailored to your profile — powered by GenFlow Ad Studio with Gemini 3.1 Pro, Veo 3.1 & Imagen 4.",
              },
            ].map((card, i) => (
              <div
                key={i}
                onClick={(card as any).onClick}
                className={`flex items-start space-x-4 p-5 bg-white rounded-xl border border-idfc-gray-200 hover:border-idfc-maroon/30 hover:shadow-md transition-all duration-200 ${
                  (card as any).onClick ? "cursor-pointer" : ""
                }`}
              >
                <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-idfc-maroon/10 flex items-center justify-center text-idfc-maroon">
                  {card.icon}
                </div>
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="font-semibold text-idfc-gray-900">{card.title}</h3>
                    {(card as any).onClick && (
                      <span className="text-xs px-2 py-0.5 bg-idfc-maroon text-white rounded-full font-medium">Try Now</span>
                    )}
                  </div>
                  <p className="text-sm text-idfc-gray-500 mt-1">{card.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="bg-idfc-maroon">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex flex-col md:flex-row items-center justify-between space-y-4 md:space-y-0">
          <div className="text-center md:text-left">
            <h2 className="text-2xl font-bold text-white">Ready to get started?</h2>
            <p className="text-white/80 mt-1">
              Complete your Video KYC in minutes and unlock all Cymbal Wealth services — including AI-generated hyper-personalized video ads for your portfolio.
            </p>
          </div>
          <button
            onClick={onStartKYC}
            className="px-8 py-3 bg-white text-idfc-maroon font-semibold rounded-xl hover:bg-idfc-gray-100 transition-colors shadow-lg"
          >
            Start Video KYC Now
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-idfc-gray-900 text-idfc-gray-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row items-center justify-between space-y-4 md:space-y-0">
          <div className="flex items-center space-x-3">
            <span className="text-lg font-bold text-white">Cymbal Wealth</span>
            <span className="text-xs">|</span>
            <span className="text-xs">&copy; {new Date().getFullYear()} All rights reserved.</span>
          </div>
          <span className="text-xs">Powered by Google Gemini</span>
        </div>
      </footer>
    </div>
  );
}
