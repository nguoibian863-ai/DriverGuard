"use client";

import Link from "next/link";
import { useTelemetry } from "@/lib/useTelemetry";
import { LiveView } from "@/components/camera/live-view";
import "./camera.css";

export default function CameraPage() {
  const { telemetry, connected } = useTelemetry();

  return (
    <main className="camera-page">
      <div className="camera-content">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="camera-title">DriverGuard · Camera</h1>
          <div className="flex flex-wrap items-center gap-4">
            <span className="camera-connection">
              <span
                className={`camera-connection-square ${connected ? "is-connected" : ""}`}
                aria-hidden="true"
              />
              {connected ? "Đã kết nối" : "Mất kết nối"}
            </span>
            <Link href="/" className="camera-button">
              Tài xế
            </Link>
            <Link href="/monitor" className="camera-button">
              Giám sát
            </Link>
          </div>
        </header>

        <LiveView telemetry={telemetry} connected={connected} />

        <footer className="camera-footer">
          <p className="camera-caption">
            Hình có chú thích nhận diện từ AI worker. Không lưu hình.
          </p>
        </footer>
      </div>
    </main>
  );
}
