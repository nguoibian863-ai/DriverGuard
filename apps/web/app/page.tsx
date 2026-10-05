"use client";

import { useState } from "react";
import { useTelemetry } from "@/lib/useTelemetry";
import { StartGate } from "@/components/driver/start-gate";
import { StatusScreen } from "@/components/driver/status-screen";

export default function DriverPage() {
  const [started, setStarted] = useState(false);
  const { telemetry, connected } = useTelemetry();

  if (!started) {
    return <StartGate connected={connected} onStart={() => setStarted(true)} />;
  }

  return <StatusScreen telemetry={telemetry} connected={connected} />;
}
