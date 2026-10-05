"use client";

import { useEffect, useState } from "react";

export function CalibrationRing() {
  const [progress, setProgress] = useState(0);
  const [secondsRemaining, setSecondsRemaining] = useState(4);

  useEffect(() => {
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
  }, []);

  // SVG ring geometry
  const size = 180;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const isCompleted = progress >= 100;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Hướng dẫn hiệu chuẩn tư thế"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/85 backdrop-blur-md p-6 text-center select-none"
    >
      <div className="flex flex-col items-center max-w-md w-full">
        {/* SVG Countdown Ring */}
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
            {/* Track circle */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="currentColor"
              strokeWidth={strokeWidth}
              fill="transparent"
              className="text-zinc-800"
            />
            {/* Progress arc */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="currentColor"
              strokeWidth={strokeWidth}
              fill="transparent"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              className="text-emerald-500 transition-all duration-75 ease-linear"
            />
          </svg>
          {/* Center countdown seconds or completion label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center p-2">
            {isCompleted ? (
              <span className="text-lg sm:text-xl font-bold text-white text-center leading-tight">
                Đang hoàn tất…
              </span>
            ) : (
              <span className="text-4xl sm:text-5xl font-black text-white tracking-tight">
                {secondsRemaining}s
              </span>
            )}
          </div>
        </div>

        <h2 className="text-2xl sm:text-3xl font-bold text-white mt-8 tracking-tight">
          {isCompleted ? "Đang hoàn tất…" : "Nhìn thẳng phía trước"}
        </h2>
        <p className="text-sm sm:text-base text-zinc-400 mt-3 max-w-xs leading-relaxed">
          Giữ nguyên đầu và hướng mắt về trước kính lái để hiệu chuẩn tư thế chuẩn.
        </p>
      </div>
    </div>
  );
}
