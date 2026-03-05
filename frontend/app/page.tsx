export default function Home() {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-6">
      <div className="max-w-2xl text-center">
        <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-2xl font-bold text-white">
          P
        </div>
        <h1 className="mb-4 text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Wealth Management Platform
        </h1>
        <p className="mb-8 text-lg text-gray-400">
          AI-powered private banking with Gemini intelligence at every layer —
          from KYC onboarding to portfolio analytics and voice interaction.
        </p>
        <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
          <a
            href="/dashboard"
            className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:bg-indigo-500"
          >
            RM Dashboard →
          </a>
          <a
            href="/portfolio"
            className="rounded-lg border border-gray-700 px-6 py-3 text-sm font-semibold text-gray-300 transition hover:bg-gray-800"
          >
            Client Portfolio →
          </a>
        </div>
      </div>
    </div>
  );
}
