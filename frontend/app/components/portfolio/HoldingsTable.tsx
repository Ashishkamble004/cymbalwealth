"use client";

interface Holding {
  instrument_name: string;
  instrument_type: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  invested_value: number;
  current_value: number;
  unrealized_pnl: number;
  return_pct: number;
}

interface Props {
  holdings: Holding[];
}

function formatINR(value: number): string {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
  return `₹${value.toLocaleString("en-IN")}`;
}

function typeBadge(type: string) {
  const colors: Record<string, string> = {
    Equity: "badge-blue",
    MF: "badge-green",
    Bond: "badge-yellow",
    Gold: "bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/20",
    Alternate: "bg-purple-500/10 text-purple-400 ring-1 ring-inset ring-purple-500/20",
  };
  return (
    <span className={`badge ${colors[type] || "badge-blue"}`}>{type}</span>
  );
}

export default function HoldingsTable({ holdings }: Props) {
  return (
    <div className="card overflow-hidden">
      <h3 className="card-header">Holdings</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase tracking-wider">
              <th className="pb-3 pr-4">Instrument</th>
              <th className="pb-3 pr-4">Type</th>
              <th className="pb-3 pr-4 text-right">Invested</th>
              <th className="pb-3 pr-4 text-right">Current</th>
              <th className="pb-3 pr-4 text-right">P&L</th>
              <th className="pb-3 text-right">Return</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h, i) => (
              <tr
                key={i}
                className="border-b border-gray-800/50 hover:bg-gray-800/30 transition"
              >
                <td className="py-3 pr-4">
                  <span className="font-medium text-gray-200">
                    {h.instrument_name}
                  </span>
                </td>
                <td className="py-3 pr-4">{typeBadge(h.instrument_type)}</td>
                <td className="py-3 pr-4 text-right text-gray-400">
                  {formatINR(h.invested_value)}
                </td>
                <td className="py-3 pr-4 text-right text-gray-200">
                  {formatINR(h.current_value)}
                </td>
                <td
                  className={`py-3 pr-4 text-right font-medium ${
                    h.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {h.unrealized_pnl >= 0 ? "+" : ""}
                  {formatINR(h.unrealized_pnl)}
                </td>
                <td
                  className={`py-3 text-right font-medium ${
                    h.return_pct >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {h.return_pct >= 0 ? "+" : ""}
                  {h.return_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
