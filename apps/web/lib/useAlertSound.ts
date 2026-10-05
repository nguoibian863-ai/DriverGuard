"use client";

import { useEffect, useRef } from "react";
import { beepPattern, type AlertStage } from "./alert-level";

let sharedAudioContext: AudioContext | null = null;

export function getOrCreateAudioContext(): AudioContext | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (!sharedAudioContext) {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioCtx) {
      sharedAudioContext = new AudioCtx();
    }
  }
  if (sharedAudioContext && sharedAudioContext.state === "suspended") {
    void sharedAudioContext.resume();
  }
  return sharedAudioContext;
}

function playBeep(
  ctx: AudioContext,
  config: { frequencyHz: number; durationMs: number; volume: number }
): void {
  try {
    if (ctx.state === "suspended") {
      void ctx.resume();
    }
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    const startTime = ctx.currentTime;
    const durSec = config.durationMs / 1000;
    const stopTime = startTime + durSec;

    osc.type = "sine";
    osc.frequency.setValueAtTime(config.frequencyHz, startTime);

    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(config.volume, startTime + 0.02);
    gain.gain.setValueAtTime(
      config.volume,
      Math.max(startTime + 0.02, stopTime - 0.03)
    );
    gain.gain.linearRampToValueAtTime(0.001, stopTime);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(startTime);
    osc.stop(stopTime);

    osc.onended = () => {
      osc.disconnect();
      gain.disconnect();
    };
  } catch {
    // Ignore audio errors if audio playback is prevented or suspended
  }
}

export function useAlertSound(stage: AlertStage, enabled: boolean): void {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Stop and clear interval if sound is disabled or stage is "off"
    if (!enabled || stage === "off") {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    const pattern = beepPattern(stage);
    if (!pattern) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    const ctx = getOrCreateAudioContext();
    if (ctx) {
      playBeep(ctx, pattern);
    }

    intervalRef.current = setInterval(() => {
      const activeCtx = getOrCreateAudioContext();
      if (activeCtx) {
        playBeep(activeCtx, pattern);
      }
    }, pattern.intervalMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [stage, enabled]);
}
