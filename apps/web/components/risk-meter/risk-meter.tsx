import type { RiskLevel } from "@/types/telemetry";

const LABELS: Record<RiskLevel, string> = {
  NORMAL: "Bình thường",
  WARNING: "Cảnh báo",
  DANGER: "NGUY HIỂM",
};

export function RiskMeter({ score, level, muted }: { score: number; level: RiskLevel; muted: boolean }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <section className="monitor-panel monitor-risk">
      {level === "DANGER" && !muted && (
        <div role="alert" className="monitor-danger-note">
          <span aria-hidden="true">!</span> Nguy hiểm — Tài xế cần chú ý ngay!
        </div>
      )}
      <div className="flex items-baseline justify-between">
        <h2 className="monitor-panel-title">Điểm rủi ro</h2>
        <span className="monitor-risk-score">{pct.toFixed(0)}</span>
      </div>
      <div className="monitor-risk-track">
        <div className={`monitor-risk-fill monitor-risk-fill-${level.toLowerCase()}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="monitor-risk-label">
        {LABELS[level]}
        {muted ? " · đã tắt tiếng" : ""}
      </p>
    </section>
  );
}
