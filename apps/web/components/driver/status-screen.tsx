"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { postCalibrate, postMute } from "@/lib/api";
import { activeReasons } from "@/lib/reasons";
import { alertStage, type AlertStage } from "@/lib/alert-level";
import { useAlertSound } from "@/lib/useAlertSound";
import { CalibrationRing } from "./calibration-ring";
import type { Telemetry, RiskLevel } from "@/types/telemetry";

interface StatusScreenProps {
  telemetry: Telemetry | null;
  connected: boolean;
}

export function StatusScreen({ telemetry, connected }: StatusScreenProps) {
  const [stage, setStage] = useState<AlertStage>("off");
  const [muting, setMuting] = useState(false);
  const [calibrating, setCalibrating] = useState(false);

  const dangerSinceMsRef = useRef<number | null>(null);

  const currentLevel: RiskLevel = telemetry?.risk_level ?? "NORMAL";
  const isMuted = telemetry?.muted ?? false;
  const isCalibrated = telemetry?.calibrated ?? false;
  const hasCameraError = telemetry?.error === "camera_unavailable";

  const stateRef = useRef({
    level: currentLevel,
    muted: isMuted,
    connected,
    calibrated: isCalibrated,
  });

  // Track the latest telemetry attributes and timestamp when DANGER state begins
  useEffect(() => {
    stateRef.current = {
      level: currentLevel,
      muted: isMuted,
      connected,
      calibrated: isCalibrated,
    };

    if (currentLevel === "DANGER") {
      if (dangerSinceMsRef.current === null) {
        dangerSinceMsRef.current = Date.now();
      }
    } else {
      dangerSinceMsRef.current = null;
    }
  }, [currentLevel, isMuted, connected, isCalibrated]);

  // Tick every 500ms to calculate alert stage without reading refs during render
  useEffect(() => {
    const timer = setInterval(() => {
      const s = stateRef.current;
      const nextStage = alertStage({
        level: s.level,
        muted: s.muted,
        connected: s.connected,
        calibrated: s.calibrated,
        dangerSinceMs: dangerSinceMsRef.current,
        nowMs: Date.now(),
      });
      setStage(nextStage);
    }, 500);

    return () => clearInterval(timer);
  }, []);

  // Play synthesized Web Audio alerts
  useAlertSound(stage, true);

  // Border glow class based on risk and connection state
  let glowClass = "glow-border-normal";
  if (!connected) {
    glowClass = "glow-border-disconnected";
  } else if (hasCameraError) {
    glowClass = "glow-border-warning";
  } else if (!telemetry) {
    glowClass = "glow-border-disconnected";
  } else if (currentLevel === "DANGER") {
    glowClass = "glow-border-danger";
  } else if (currentLevel === "WARNING") {
    glowClass = "glow-border-warning";
  } else {
    glowClass = "glow-border-normal";
  }

  const handleMute = async () => {
    if (muting) return;
    setMuting(true);
    try {
      await postMute(15);
    } catch {
      // Ignore network errors
    } finally {
      setMuting(false);
    }
  };

  const handleCalibrate = async () => {
    if (calibrating) return;
    setCalibrating(true);
    try {
      await postCalibrate();
    } catch {
      // Ignore network errors
    } finally {
      setCalibrating(false);
    }
  };

  // Up to 2 active reasons
  const reasons = telemetry ? activeReasons(telemetry).slice(0, 2) : [];

  // Calibration overlay is mounted only when connected, not calibrated, and face is detected
  const showCalibration = connected && !isCalibrated && (telemetry?.face_detected ?? false);

  return (
    <main
      className={`min-h-dvh flex flex-col justify-between p-4 sm:p-8 bg-zinc-950 text-zinc-100 select-none relative transition-all duration-300 ${glowClass}`}
    >
      {/* Calibration Overlay */}
      {showCalibration && <CalibrationRing />}

      {/* Top Bar */}
      <header className="flex items-center justify-between w-full max-w-5xl mx-auto z-10">
        {/* Connection status chip */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs sm:text-sm font-medium border ${
            connected
              ? "bg-zinc-900/90 border-zinc-800 text-zinc-300"
              : "bg-zinc-900/90 border-zinc-700 text-zinc-400"
          }`}
        >
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              connected ? "bg-emerald-400" : "bg-zinc-500 animate-pulse"
            }`}
            aria-hidden="true"
          />
          <span>{connected ? "Đã kết nối" : "Mất kết nối — đang thử lại…"}</span>
        </div>

        {/* Risk score & Mute status */}
        <div className="flex items-center gap-2">
          {isMuted && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs sm:text-sm font-semibold">
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M11 5L6 9H2v6h4l5 4V5z" />
                <line x1="23" y1="9" x2="17" y2="15" />
                <line x1="17" y1="9" x2="23" y2="15" />
              </svg>
              <span>Đã tắt tiếng</span>
            </div>
          )}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900/90 border border-zinc-800 text-xs sm:text-sm font-medium text-zinc-400">
            <span>Rủi ro:</span>
            <span className="font-bold text-white">
              {telemetry ? Math.round(telemetry.risk_score) : "--"}
            </span>
          </div>
        </div>
      </header>

      {/* Main Status Display */}
      <section
        role={currentLevel === "DANGER" ? "alert" : "status"}
        aria-live={currentLevel === "DANGER" ? "assertive" : "polite"}
        className="flex flex-col items-center justify-center text-center my-auto py-8 px-4 max-w-4xl mx-auto w-full z-10"
      >
        {!connected ? (
          <div className="flex flex-col items-center">
            <div
              className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-6 text-zinc-500"
              aria-hidden="true"
            >
              <svg
                className="w-10 h-10 sm:w-12 sm:h-12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="1" y1="1" x2="23" y2="23" />
                <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
                <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
                <path d="M10.71 5.05A16 16 0 0 1 22.58 9" />
                <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                <line x1="12" y1="20" x2="12.01" y2="20" />
              </svg>
            </div>
            <h2 className="text-3xl sm:text-5xl md:text-6xl font-black text-zinc-400 tracking-tight">
              Mất kết nối — đang thử lại…
            </h2>
            <p className="text-base sm:text-xl text-zinc-500 mt-4 max-w-md">
              Hệ thống đang tự động kết nối lại máy chủ AI...
            </p>
          </div>
        ) : hasCameraError ? (
          <div className="flex flex-col items-center">
            <div
              className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-6 text-amber-400"
              aria-hidden="true"
            >
              <svg
                className="w-10 h-10 sm:w-12 sm:h-12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m1 1 22 22" />
                <path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34m-7.72-2.06a4 4 0 1 1-5.56-5.56" />
              </svg>
            </div>
            <h2 className="text-4xl sm:text-6xl md:text-7xl font-black text-amber-400 tracking-tight">
              Không mở được camera
            </h2>
            <p className="text-base sm:text-xl text-zinc-400 mt-4 max-w-md">
              Vui lòng kiểm tra cáp kết nối hoặc quyền truy cập camera.
            </p>
          </div>
        ) : !telemetry ? (
          <div className="flex flex-col items-center">
            <div
              className="w-16 h-16 sm:w-20 sm:h-20 rounded-full border-4 border-zinc-800 border-t-zinc-400 animate-spin mb-6"
              aria-hidden="true"
            />
            <h2 className="text-3xl sm:text-5xl md:text-6xl font-black text-zinc-400 tracking-tight">
              Đang chờ dữ liệu từ AI worker…
            </h2>
            <p className="text-base sm:text-xl text-zinc-500 mt-4 max-w-md">
              Đang khởi tạo mô hình phân tích thời gian thực.
            </p>
          </div>
        ) : currentLevel === "DANGER" ? (
          <div className="flex flex-col items-center">
            <div
              className="inline-flex items-center justify-center w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-red-500/20 border-2 border-red-500 mb-6 text-red-500 shadow-lg shadow-red-500/30"
              aria-hidden="true"
            >
              <svg
                className="w-12 h-12 sm:w-14 sm:h-14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <h2 className="text-6xl sm:text-8xl md:text-9xl font-black text-red-500 tracking-tight">
              NGUY HIỂM
            </h2>
            {reasons.length > 0 && (
              <div className="mt-6 flex flex-col items-center gap-2">
                {reasons.map((reason, idx) => (
                  <span
                    key={idx}
                    className="text-2xl sm:text-4xl md:text-5xl font-bold text-red-200 tracking-normal px-4 py-1.5 rounded-xl bg-red-950/60 border border-red-800/60"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : currentLevel === "WARNING" ? (
          <div className="flex flex-col items-center">
            <div
              className="inline-flex items-center justify-center w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-amber-500/20 border-2 border-amber-500 mb-6 text-amber-400 shadow-lg shadow-amber-500/30"
              aria-hidden="true"
            >
              <svg
                className="w-12 h-12 sm:w-14 sm:h-14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 className="text-6xl sm:text-8xl md:text-9xl font-black text-amber-400 tracking-tight">
              Chú ý
            </h2>
            {reasons.length > 0 && (
              <div className="mt-6 flex flex-col items-center gap-2">
                {reasons.map((reason, idx) => (
                  <span
                    key={idx}
                    className="text-2xl sm:text-4xl md:text-5xl font-bold text-amber-200 tracking-normal px-4 py-1.5 rounded-xl bg-amber-950/60 border border-amber-800/60"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div
              className="inline-flex items-center justify-center w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-emerald-500/20 border-2 border-emerald-500 mb-6 text-emerald-400 shadow-lg shadow-emerald-500/30"
              aria-hidden="true"
            >
              <svg
                className="w-12 h-12 sm:w-14 sm:h-14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <h2 className="text-5xl sm:text-7xl md:text-8xl font-black text-emerald-400 tracking-tight">
              Đang theo dõi
            </h2>
            {reasons.length > 0 ? (
              <div className="mt-6 flex flex-col items-center gap-2">
                {reasons.map((reason, idx) => (
                  <span
                    key={idx}
                    className="text-2xl sm:text-3xl font-semibold text-zinc-300"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-lg sm:text-2xl text-zinc-400 mt-4 font-medium">
                Tư thế và tầm nhìn an toàn
              </p>
            )}
          </div>
        )}
      </section>

      {/* Bottom Controls */}
      <footer className="flex flex-col items-center gap-4 w-full max-w-xl mx-auto z-10 pb-2">
        {/* Large Mute Button (min-h-16) */}
        <button
          type="button"
          onClick={handleMute}
          disabled={!connected || muting}
          aria-label={
            isMuted
              ? "Cảnh báo âm thanh đang được tắt tiếng trong 15 giây"
              : "Tắt tiếng cảnh báo trong 15 giây"
          }
          className={`w-full min-h-16 h-16 sm:h-20 text-xl sm:text-2xl font-bold rounded-2xl shadow-lg transition-all flex items-center justify-center gap-3 cursor-pointer focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-400 disabled:opacity-50 disabled:cursor-not-allowed ${
            isMuted
              ? "bg-zinc-800 text-zinc-400 border border-zinc-700"
              : "bg-zinc-100 hover:bg-white active:bg-zinc-200 text-zinc-950 shadow-white/10"
          }`}
        >
          <svg
            className="w-7 h-7 sm:w-8 sm:h-8"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M11 5L6 9H2v6h4l5 4V5z" />
            <line x1="23" y1="9" x2="17" y2="15" />
            <line x1="17" y1="9" x2="23" y2="15" />
          </svg>
          <span>
            {muting ? "Đang gửi…" : isMuted ? "Đã tắt tiếng" : "Tắt tiếng 15 giây"}
          </span>
        </button>

        {/* Smaller Recalibrate Button */}
        <div className="flex items-center justify-center w-full">
          <button
            type="button"
            onClick={handleCalibrate}
            disabled={!connected || calibrating}
            aria-label="Hiệu chuẩn lại tư thế tài xế"
            className="min-h-12 h-12 px-6 rounded-xl bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-700 border border-zinc-800 text-zinc-300 hover:text-white text-sm sm:text-base font-medium transition-all flex items-center justify-center gap-2 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg
              className="w-4 h-4 sm:w-5 sm:h-5 text-zinc-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="22" y1="12" x2="18" y2="12" />
              <line x1="6" y1="12" x2="2" y2="12" />
              <line x1="12" y1="6" x2="12" y2="2" />
              <line x1="12" y1="22" x2="12" y2="18" />
            </svg>
            <span>{calibrating ? "Đang gửi…" : "Hiệu chuẩn lại"}</span>
          </button>
        </div>

        {/* Small Link to /monitor */}
        <div className="pt-1">
          <Link
            href="/monitor"
            className="text-xs text-zinc-500 hover:text-zinc-300 underline underline-offset-4 py-2 px-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 rounded"
          >
            Giám sát
          </Link>
        </div>
      </footer>
    </main>
  );
}
