import type { RiskLevel } from "@/types/telemetry";

const COLORS: Record<RiskLevel, string> = {
  NORMAL: "bg-emerald-500",
  WARNING: "bg-amber-400",
  DANGER: "bg-red-600",
};
const LABELS: Record<RiskLevel, string> = {
  NORMAL: "Bình thường",
  WARNING: "Cảnh báo",
  DANGER: "NGUY HIỂM",
};

export function RiskMeter({ score, level, muted }: { score: number; level: RiskLevel; muted: boolean }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <section className="space-y-3 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
      {level === "DANGER" && !muted && (
        <div role="alert" className="animate-pulse rounded-lg bg-red-600 px-3 py-2 text-center font-bold text-white">
          ⚠ NGUY HIỂM — Tài xế cần chú ý ngay!
        </div>
      )}
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-medium text-zinc-500">Điểm rủi ro</h2>
        <span className="text-3xl font-bold tabular-nums">{pct.toFixed(0)}</span>
      </div>
      <div className="h-4 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
        <div className={`h-full transition-all duration-300 ${COLORS[level]}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-sm font-semibold">
        {LABELS[level]}
        {muted ? " · đã tắt tiếng" : ""}
      </p>
    </section>
  );
}
