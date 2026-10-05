"use client";

import { useState } from "react";
import { postCalibrate, postMute } from "@/lib/api";

export function Controls({ disabled }: { disabled: boolean }) {
  const [busy, setBusy] = useState<string | null>(null);

  async function run(name: string, fn: () => Promise<void>) {
    setBusy(name);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  }

  const base =
    "rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900";
  return (
    <div className="flex flex-wrap gap-3">
      <button className={base} disabled={disabled || busy !== null} onClick={() => run("cal", postCalibrate)}>
        {busy === "cal" ? "Đang gửi…" : "Hiệu chuẩn tư thế"}
      </button>
      <button className={base} disabled={disabled || busy !== null} onClick={() => run("mute", () => postMute(15))}>
        {busy === "mute" ? "Đang gửi…" : "Tắt tiếng 15 giây"}
      </button>
    </div>
  );
}
