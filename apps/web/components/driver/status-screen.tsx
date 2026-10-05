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

  // Background and color classes based on level and connection
  const isDisconnected = !connected;
  const isDanger = connected && currentLevel === "DANGER";
  const isWarning = connected && currentLevel === "WARNING";
  const isEscalated = isDanger && stage === "danger_escalated";

  let containerBg = "bg-[var(--bg)] text-[var(--text)]";
  if (isDisconnected) {
    containerBg = "bg-[var(--bg)] text-[var(--text)] border-t-[4px] border-[var(--border)]";
  } else if (isDanger) {
    containerBg = `bg-[var(--danger-solid)] text-white ${isEscalated ? "danger-escalated-bg" : ""}`;
  } else if (isWarning) {
    containerBg = "bg-[var(--warn-solid)] text-[#1a1a18]";
  }

  // Button styles based on state
  let muteButtonClass = "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] hover:bg-[var(--bg)]";
  let recalibrateButtonClass = "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] hover:bg-[var(--bg)]";
  let linkClass = "text-[var(--text-muted)] hover:text-[var(--text)]";
  let topInfoClass = "text-[var(--text-muted)]";

  if (isDanger) {
    muteButtonClass = "bg-transparent text-white border-2 border-white hover:bg-white/10 active:bg-white/20";
    recalibrateButtonClass = "bg-transparent text-white border border-white/80 hover:bg-white/10 active:bg-white/20";
    linkClass = "text-white/80 hover:text-white";
    topInfoClass = "text-white/80";
  } else if (isWarning) {
    muteButtonClass = "bg-transparent text-[#1a1a18] border-2 border-[#1a1a18] hover:bg-black/5 active:bg-black/10";
    recalibrateButtonClass = "bg-transparent text-[#1a1a18] border border-[#1a1a18]/80 hover:bg-black/5 active:bg-black/10";
    linkClass = "text-[#1a1a18]/80 hover:text-[#1a1a18]";
    topInfoClass = "text-[#1a1a18]/80";
  }

  return (
    <main
      className={`min-h-dvh flex flex-col justify-between p-6 select-none relative transition-colors duration-150 ${containerBg}`}
    >
      {/* Calibration Overlay */}
      {showCalibration && (
        <CalibrationRing faceDetected={telemetry?.face_detected ?? false} />
      )}

      {/* Top Header: Mute status & small risk score in corner */}
      <header className="flex items-center justify-between w-full max-w-4xl mx-auto">
        <div className={`text-[14px] font-medium ${topInfoClass}`}>
          {isDisconnected ? "" : isMuted ? "Đã tắt tiếng" : ""}
        </div>
        <div className={`text-[14px] font-medium tabular-nums ${topInfoClass}`}>
          Rủi ro: {telemetry ? Math.round(telemetry.risk_score) : "--"}
        </div>
      </header>

      {/* Main Status Display */}
      <section
        role={isDanger ? "alert" : "status"}
        aria-live={isDanger ? "assertive" : "polite"}
        className="flex flex-col items-center justify-center text-center my-auto py-8 px-4 max-w-4xl mx-auto w-full"
      >
        {isDisconnected ? (
          <h2 className="text-[20px] font-semibold text-[var(--text)] tracking-tight">
            Mất kết nối. Đang thử lại…
          </h2>
        ) : hasCameraError ? (
          <div className="flex flex-col items-center">
            <h2 className="text-[28px] font-semibold text-[var(--warn)] tracking-tight">
              Không mở được camera
            </h2>
            <p className="text-[14px] text-[var(--text-muted)] mt-2">
              Vui lòng kiểm tra cáp kết nối hoặc quyền truy cập camera.
            </p>
          </div>
        ) : !telemetry ? (
          <h2 className="text-[20px] font-medium text-[var(--text-muted)] tracking-tight">
            Đang chờ dữ liệu từ AI worker…
          </h2>
        ) : isDanger ? (
          <div className="flex flex-col items-center">
            <div className="flex items-center justify-center gap-4 sm:gap-6 flex-wrap sm:flex-nowrap">
              <svg
                className="w-16 h-16 sm:w-20 sm:h-20 shrink-0 text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="4"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <h2 className="text-[56px] sm:text-[72px] md:text-[96px] leading-none font-semibold text-white tracking-tight">
                NGUY HIỂM
              </h2>
            </div>
            {reasons.length > 0 && (
              <div className="mt-6 flex flex-col items-center gap-2">
                {reasons.map((reason, idx) => (
                  <span
                    key={idx}
                    className="text-[20px] sm:text-[28px] font-medium text-white"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : isWarning ? (
          <div className="flex flex-col items-center">
            <h2 className="text-[56px] sm:text-[72px] md:text-[96px] leading-none font-semibold text-[#1a1a18] tracking-tight">
              CHÚ Ý
            </h2>
            {reasons.length > 0 && (
              <div className="mt-6 flex flex-col items-center gap-2">
                {reasons.map((reason, idx) => (
                  <span
                    key={idx}
                    className="text-[20px] sm:text-[28px] font-medium text-[#1a1a18]"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="flex items-center justify-center gap-3">
              <span
                className="w-[12px] h-[12px] bg-[var(--ok)] shrink-0 rounded-[2px]"
                aria-hidden="true"
              />
              <span className="text-[20px] font-medium text-[var(--text-muted)]">
                Đang theo dõi
              </span>
            </div>
            {reasons.length > 0 && (
              <div className="mt-4 flex flex-col items-center gap-1.5">
                {reasons.map((reason, idx) => (
                  <span
                    key={idx}
                    className="text-[16px] font-medium text-[var(--text-muted)]"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Bottom Controls */}
      <footer className="flex flex-col items-center gap-3 w-full max-w-md mx-auto pb-2">
        {/* Large Mute Button (min-h-16, h-16, rounded 8px) */}
        <button
          type="button"
          onClick={handleMute}
          disabled={!connected || muting}
          aria-label={
            isMuted
              ? "Cảnh báo âm thanh đang được tắt tiếng trong 15 giây"
              : "Tắt tiếng cảnh báo trong 15 giây"
          }
          className={`w-full h-16 min-h-[64px] text-[16px] sm:text-[20px] font-semibold rounded-[var(--radius-lg)] transition-opacity flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${muteButtonClass}`}
        >
          {muting ? "Đang gửi…" : isMuted ? "Đã tắt tiếng" : "Tắt tiếng 15 giây"}
        </button>

        {/* Recalibrate Button (min-h-12, h-12, outline) */}
        <button
          type="button"
          onClick={handleCalibrate}
          disabled={!connected || calibrating}
          aria-label="Hiệu chuẩn lại tư thế tài xế"
          className={`h-12 min-h-[48px] px-6 rounded-[var(--radius-lg)] transition-opacity text-[14px] sm:text-[16px] font-medium flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${recalibrateButtonClass}`}
        >
          {calibrating ? "Đang gửi…" : "Hiệu chuẩn lại"}
        </button>

        {/* Link to /monitor */}
        <div className="pt-1">
          <Link
            href="/monitor"
            className={`min-h-[48px] inline-flex items-center text-[14px] underline underline-offset-4 px-3 transition-colors ${linkClass}`}
          >
            Giám sát
          </Link>
        </div>
      </footer>
    </main>
  );
}
