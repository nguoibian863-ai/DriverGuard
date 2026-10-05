import type { HistoryPoint } from "@/lib/useTelemetry";

const W = 300;
const H = 90;
const MAX = 1;

function toPath(values: number[]): string {
  if (values.length < 2) return "";
  return values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * W;
      const y = H - (Math.min(v, MAX) / MAX) * H;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function EarMarChart({ history }: { history: HistoryPoint[] }) {
  const thresholdY = H - (0.2 / MAX) * H;
  return (
    <section className="space-y-2 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex items-center justify-between text-sm">
        <h2 className="font-medium text-zinc-500">EAR / MAR (60 mẫu gần nhất)</h2>
        <span className="flex gap-3 text-xs">
          <span className="text-sky-500">● EAR</span>
          <span className="text-fuchsia-500">● MAR</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-24 w-full" role="img" aria-label="Đồ thị EAR và MAR">
        <line x1="0" x2={W} y1={thresholdY} y2={thresholdY} className="stroke-zinc-300 dark:stroke-zinc-700" strokeDasharray="4 4" />
        <path d={toPath(history.map((h) => h.ear))} fill="none" className="stroke-sky-500" strokeWidth="1.5" />
        <path d={toPath(history.map((h) => h.mar))} fill="none" className="stroke-fuchsia-500" strokeWidth="1.5" />
      </svg>
      <p className="text-xs text-zinc-500">Đường đứt: ngưỡng nhắm mắt (EAR 0.20)</p>
    </section>
  );
}
