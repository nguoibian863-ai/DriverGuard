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
    <main className="min-h-dvh flex flex-col justify-between p-6 sm:p-10 bg-zinc-950 text-zinc-100 select-none">
      {/* Top Header */}
      <header className="flex items-center justify-between w-full max-w-4xl mx-auto">
        <div className="flex items-center gap-2.5">
          <span className="flex h-3 w-3 rounded-full bg-emerald-500" aria-hidden="true" />
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">
            DriverGuard
          </h1>
          <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded font-medium">
            Tài xế
          </span>
        </div>

        <div
          className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${
            connected
              ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-400"
              : "bg-zinc-900 border-zinc-800 text-zinc-400"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-emerald-400" : "bg-zinc-500"
            }`}
            aria-hidden="true"
          />
          <span>{connected ? "Đã kết nối" : "Mất kết nối — đang thử lại…"}</span>
        </div>
      </header>

      {/* Main Center Section */}
      <section className="flex flex-col items-center justify-center text-center my-auto py-12 px-4 max-w-lg mx-auto w-full">
        {/* Shield Icon SVG */}
        <div
          className="w-20 h-20 sm:w-24 sm:h-24 rounded-3xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-8 shadow-xl"
          aria-hidden="true"
        >
          <svg
            className="w-10 h-10 sm:w-12 sm:h-12 text-emerald-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        </div>

        <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
          Chế độ Tài xế
        </h2>
        <p className="text-base sm:text-lg text-zinc-400 mt-3 mb-10 max-w-md leading-relaxed">
          Giao diện tối giản trong xe với cảnh báo âm thanh tức thì khi phát hiện mệt mỏi hoặc mất tập trung.
        </p>

        {/* Big Start Button */}
        <button
          type="button"
          onClick={handleStart}
          aria-label="Bắt đầu giám sát hành trình và mở khoá âm thanh cảnh báo"
          className="w-full h-16 sm:h-20 min-h-16 text-xl sm:text-2xl font-bold bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600 text-zinc-950 rounded-2xl shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-3 cursor-pointer focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-400/50"
        >
          <svg
            className="w-7 h-7"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          <span>Bắt đầu giám sát</span>
        </button>
      </section>

      {/* Footer Link */}
      <footer className="flex justify-center w-full max-w-4xl mx-auto py-2">
        <Link
          href="/monitor"
          className="text-xs text-zinc-500 hover:text-zinc-300 underline underline-offset-4 py-2 px-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 rounded"
        >
          Giám sát
        </Link>
      </footer>
    </main>
  );
}
