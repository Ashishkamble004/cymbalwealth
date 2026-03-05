"use client";

interface Props {
  allocation: Record<string, number>;
}

const COLORS = [
  { bg: "bg-indigo-500", text: "text-indigo-400" },
  { bg: "bg-emerald-500", text: "text-emerald-400" },
  { bg: "bg-amber-500", text: "text-amber-400" },
  { bg: "bg-purple-500", text: "text-purple-400" },
  { bg: "bg-rose-500", text: "text-rose-400" },
  { bg: "bg-cyan-500", text: "text-cyan-400" },
];

export default function AllocationChart({ allocation }: Props) {
  const entries = Object.entries(allocation).sort((a, b) => b[1] - a[1]);

  return (
    <div className="card">
      <h3 className="card-header">Asset Allocation</h3>

      {/* Bar chart */}
      <div className="mb-6 flex h-6 w-full overflow-hidden rounded-full bg-gray-800">
        {entries.map(([type, pct], i) => (
          <div
            key={type}
            className={`${COLORS[i % COLORS.length].bg} transition-all`}
            style={{ width: `${pct}%` }}
            title={`${type}: ${pct.toFixed(1)}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="space-y-3">
        {entries.map(([type, pct], i) => (
          <div key={type} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className={`h-3 w-3 rounded-sm ${
                  COLORS[i % COLORS.length].bg
                }`}
              />
              <span className="text-sm text-gray-300">{type}</span>
            </div>
            <span
              className={`text-sm font-medium ${
                COLORS[i % COLORS.length].text
              }`}
            >
              {pct.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
