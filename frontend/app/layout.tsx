import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prestige Private Bank — Wealth Management",
  description: "AI-powered wealth management platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-950 text-gray-100 antialiased min-h-screen">
        <nav className="sticky top-0 z-50 border-b border-gray-800 bg-gray-950/80 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                P
              </div>
              <span className="text-lg font-semibold tracking-tight">
                Prestige Private Bank
              </span>
            </div>
            <div className="flex items-center gap-6 text-sm">
              <a
                href="/dashboard"
                className="text-gray-400 hover:text-white transition-colors"
              >
                RM Dashboard
              </a>
              <a
                href="/portfolio"
                className="text-gray-400 hover:text-white transition-colors"
              >
                Client Portfolio
              </a>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
