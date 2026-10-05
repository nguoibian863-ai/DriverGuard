import type { Telemetry } from "@/types/telemetry";

function Badge({ label, on, bad = true }: { label: string; on: boolean; bad?: boolean }) {
  const color = !on
    ? "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
    : bad
      ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
      : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300";
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${color}`}>{label}</span>;
}

function Stat({ name, value }: { name: string; value: string }) {
  return (
    <div>
      <dt className="inline text-zinc-500">{name} </dt>
      <dd className="inline">{value}</dd>
    </div>
  );
}

export function DriverStatus({ t }: { t: Telemetry }) {
  return (
    <section className="space-y-3 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-sm font-medium text-zinc-500">Trạng thái tài xế</h2>
      <div className="flex flex-wrap gap-2">
        <Badge label="Thấy mặt" on={t.face_detected} bad={false} />
        <Badge label="Đã hiệu chuẩn" on={t.calibrated} bad={false} />
        <Badge label="Nhắm mắt" on={t.eyes_closed} />
        <Badge label="Ngáp" on={t.yawning} />
        <Badge label="Quay đầu" on={t.looking_away} />
        <Badge label="Cúi đầu" on={t.looking_down} />
        <Badge label="Dùng điện thoại" on={t.phone_usage} />
        <Badge label="Thấy điện thoại" on={t.phone_detected} />
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm tabular-nums sm:grid-cols-3">
        <Stat name="EAR" value={t.ear.toFixed(2)} />
        <Stat name="MAR" value={t.mar.toFixed(2)} />
        <Stat name="Yaw" value={`${t.relative_yaw.toFixed(0)}°`} />
        <Stat name="Pitch" value={`${t.relative_pitch.toFixed(0)}°`} />
        <Stat name="FPS" value={`${t.fps.camera}/${t.fps.face}/${t.fps.phone}`} />
        <Stat name="Trễ" value={`${t.latency_ms.face}ms`} />
      </dl>
      {t.error && (
        <p className="text-sm text-red-600">
          Lỗi: {t.error === "camera_unavailable" ? "không mở được camera" : t.error}
        </p>
      )}
    </section>
  );
}
