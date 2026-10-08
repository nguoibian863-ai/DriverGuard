"use client";

import Link from "next/link";
import { getOrCreateAudioContext } from "@/lib/useAlertSound";

interface StartGateProps {
  connected: boolean;
  onStart: () => void;
}

export function StartGate({ connected, onStart }: StartGateProps) {
  const handleStart = () => {
    getOrCreateAudioContext();
    onStart();
  };

  return (
    <main className="min-h-dvh flex flex-col justify-between p-6 select-none bg-[var(--bg)] text-[var(--text)]">
      <header className="w-full max-w-md mx-auto flex items-center justify-between">
        <h1 className="text-[20px] font-semibold text-[var(--text)]">
          DriverGuard
        </h1>
        {!connected && (
          <span className="text-[12px] font-medium text-[var(--text-muted)]">
            Mất kết nối
          </span>
        )}
      </header>

      <section className="flex flex-col items-center justify-center my-auto py-8 px-4 max-w-md mx-auto w-full">
        <button
          type="button"
          onClick={handleStart}
          aria-label="Bắt đầu"
          className="w-full h-16 min-h-[64px] text-[20px] font-semibold text-white bg-[var(--accent)] hover:opacity-90 active:opacity-100 rounded-[var(--radius-lg)] transition-opacity flex items-center justify-center cursor-pointer border-0"
        >
          Bắt đầu
        </button>
        <p className="text-[14px] text-[var(--text-muted)] mt-3 text-center">
          Âm thanh cảnh báo sẽ được bật.
        </p>
      </section>

      <footer className="flex flex-wrap items-center justify-center gap-2 w-full max-w-md mx-auto py-2">
        <Link
          href="/monitor"
          className="min-h-[48px] inline-flex items-center text-[14px] text-[var(--text-muted)] hover:text-[var(--text)] underline underline-offset-4 px-3 transition-colors"
        >
          Giám sát
        </Link>
        <Link
          href="/camera"
          className="min-h-[48px] inline-flex items-center text-[14px] text-[var(--text-muted)] hover:text-[var(--text)] underline underline-offset-4 px-3 transition-colors"
        >
          Camera
        </Link>
      </footer>
    </main>
  );
}
