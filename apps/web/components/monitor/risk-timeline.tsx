import type { TimelinePoint } from "@/lib/timeline";
import type { TimelineEvent } from "@/lib/useRiskHistory";
import { levelBand } from "@/lib/timeline";

const W = 720;
const H = 180;
const left = 40;
const right = 12;
const top = 12;
const bottom = 22;
const plotH = H - top - bottom;
const x = (time: number, now: number) => left + (time - (now - 300_000)) / 300_000 * (W - left - right);
const y = (score: number) => top + (100 - Math.max(0, Math.min(100, score))) / 100 * plotH;

export function RiskTimeline({ points, events, now }: { points: TimelinePoint[]; events: TimelineEvent[]; now: number }) {
  const visible = points.filter((point) => point.time >= now - 300_000 && point.time <= now);
  const path = visible.map((point, index) => `${index ? "L" : "M"}${x(point.time, now).toFixed(1)},${y(point.score).toFixed(1)}`).join(" ");
  return <section className="monitor-panel">
    <h2 className="monitor-panel-title">Dòng thời gian rủi ro</h2>
    {visible.length === 0 ? <p className="py-12 text-center text-[var(--text-muted,#5c5c57)]">Đang chờ điểm rủi ro từ camera.</p> :
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Điểm rủi ro trong 5 phút gần nhất, hiện tại ${visible[visible.length - 1].score.toFixed(0)} điểm; ${events.length} sự kiện`}>
        <rect x={left} y={y(100)} width={W-left-right} height={y(70)-y(100)} fill="var(--danger-bg, #fde8e6)" />
        <rect x={left} y={y(70)} width={W-left-right} height={y(40)-y(70)} fill="var(--warn-bg, #fff3d6)" />
        <rect x={left} y={y(40)} width={W-left-right} height={y(0)-y(40)} fill="var(--ok-bg, #e6f4ec)" />
        {[0,40,70,100].map((score) => <g key={score}><line x1={left} x2={W-right} y1={y(score)} y2={y(score)} stroke="var(--border, #d9d9d4)"/><text x={left-6} y={y(score)+4} textAnchor="end" fill="var(--text-muted, #5c5c57)" fontSize="12">{score}</text></g>)}
        <path d={path} fill="none" stroke="var(--accent, #1f5eff)" strokeWidth="2.5" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        {events.filter((event) => event.time >= now-300_000 && event.time <= now).map((event) => <g key={event.key}><circle cx={x(event.time, now)} cy={y(event.score)} r="5" fill={levelBand(event.score) === "DANGER" ? "var(--danger, #b3261e)" : levelBand(event.score) === "WARNING" ? "var(--warn, #8a5a00)" : "var(--ok, #1d7a46)"} stroke="var(--surface, #fff)" strokeWidth="2"><title>{`${event.eventType}: ${event.score.toFixed(0)} điểm`}</title></circle></g>)}
        <text x={left} y={H-3} fill="var(--text-muted, #5c5c57)" fontSize="12">-5 phút</text><text x={W-right} y={H-3} textAnchor="end" fill="var(--text-muted, #5c5c57)" fontSize="12">Bây giờ</text>
      </svg>}
  </section>;
}
