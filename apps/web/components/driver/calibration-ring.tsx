"use client";

import { useEffect, useState } from "react";

interface CalibrationRingProps {
  faceDetected?: boolean;
}

export function CalibrationRing({ faceDetected = true }: CalibrationRingProps) {
  const [progress, setProgress] = useState(0);
  const [secondsRemaining, setSecondsRemaining] = useState(4);

  useEffect(() => {
    if (!faceDetected) {
      return;
    }

    const TOTAL_MS = 4000;
    const startTime = Date.now();

    const intervalId = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const currentPct = Math.min(100, (elapsed / TOTAL_MS) * 100);
      const remainingSec = Math.max(1, Math.ceil((TOTAL_MS - elapsed) / 1000));

      setProgress(currentPct);
      setSecondsRemaining(remainingSec);

      if (elapsed >= TOTAL_MS) {
        clearInterval(intervalId);
      }
    }, 50);

    return () => {
      clearInterval(intervalId);
    };
  }, [faceDetected]);

  const size = 120;
  const strokeWidth = 4;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const isCompleted = progress >= 100;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Hiệu chuẩn tư thế"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/80 p-6 text-center select-none"
    >
      <div className="flex flex-col items-center max-w-sm w-full">
        {faceDetected ? (
          <>
            <div
              className="relative flex items-center justify-center"
              style={{ width: size, height: size }}
            >
              <svg
                width={size}
                height={size}
                viewBox={`0 0 ${size} ${size}`}
                className="-rotate-90"
                aria-hidden="true"
              >
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  stroke="var(--border)"
                  strokeWidth={strokeWidth}
                  fill="transparent"
                />
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  stroke="var(--accent)"
                  strokeWidth={strokeWidth}
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[20px] font-semibold text-white tabular-nums">
                  {isCompleted ? "" : `${secondsRemaining}s`}
                </span>
              </div>
            </div>

            <h2 className="text-[28px] font-semibold text-white mt-6 tracking-tight">
              {isCompleted ? "Đang hoàn tất…" : "Nhìn thẳng phía trước"}
            </h2>
          </>
        ) : (
          <h2 className="text-[28px] font-semibold text-white tracking-tight">
            Không thấy khuôn mặt
          </h2>
        )}
      </div>
    </div>
  );
}
