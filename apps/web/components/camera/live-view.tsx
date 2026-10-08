"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { API_URL } from "@/lib/api";
import type { Telemetry, RiskLevel } from "@/types/telemetry";

const RISK_LABELS: Record<RiskLevel, string> = {
  NORMAL: "Bình thường",
  WARNING: "Chú ý",
  DANGER: "Nguy hiểm",
};

const emptySubscribe = () => () => {};

function getFullscreenSnapshot(): boolean {
  const doc = document as Document & {
    webkitFullscreenEnabled?: boolean;
  };
  return Boolean(doc.fullscreenEnabled ?? doc.webkitFullscreenEnabled);
}

function getFullscreenServerSnapshot(): boolean {
  return false;
}

interface LiveViewProps {
  telemetry: Telemetry | null;
  connected: boolean;
}

export function LiveView({ telemetry, connected }: LiveViewProps) {
  const videoContainerRef = useRef<HTMLDivElement | null>(null);
  const [hasLoadedFrame, setHasLoadedFrame] = useState(false);
  const [prevConnected, setPrevConnected] = useState(connected);
  const [tabVisible, setTabVisible] = useState(() =>
    typeof document === "undefined" ? true : document.visibilityState !== "hidden"
  );
  const [streamKey, setStreamKey] = useState<number>(() => Date.now());
  const supportsFullscreen = useSyncExternalStore(
    emptySubscribe,
    getFullscreenSnapshot,
    getFullscreenServerSnapshot
  );
  const [isFullscreen, setIsFullscreen] = useState(false);

  if (!connected && prevConnected) {
    setPrevConnected(false);
    setHasLoadedFrame(false);
  } else if (connected && !prevConnected) {
    setPrevConnected(true);
    setHasLoadedFrame(false);
  }

  // Bandwidth saving: disconnect stream when tab hidden, reconnect with timestamp when visible
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "hidden") {
        setTabVisible(false);
        setHasLoadedFrame(false);
      } else {
        setStreamKey(Date.now());
        setTabVisible(true);
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, []);

  // Fullscreen state tracking
  useEffect(() => {
    const onFsChange = () => {
      const fsEl =
        document.fullscreenElement ??
        (document as Document & { webkitFullscreenElement?: Element })
          .webkitFullscreenElement;
      setIsFullscreen(Boolean(fsEl));
    };

    document.addEventListener("fullscreenchange", onFsChange);
    document.addEventListener("webkitfullscreenchange", onFsChange);
    return () => {
      document.removeEventListener("fullscreenchange", onFsChange);
      document.removeEventListener("webkitfullscreenchange", onFsChange);
    };
  }, []);

  const handleToggleFullscreen = async () => {
    const container = videoContainerRef.current;
    if (!container) return;
    const doc = document as Document & {
      webkitFullscreenElement?: Element;
      webkitExitFullscreen?: () => Promise<void>;
    };
    const isFs = Boolean(document.fullscreenElement ?? doc.webkitFullscreenElement);
    try {
      if (!isFs) {
        const el = container as HTMLDivElement & {
          webkitRequestFullscreen?: () => Promise<void>;
        };
        if (el.requestFullscreen) {
          await el.requestFullscreen();
        } else if (el.webkitRequestFullscreen) {
          await el.webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if (doc.webkitExitFullscreen) {
          await doc.webkitExitFullscreen();
        }
      }
    } catch {
      // Browser may reject fullscreen request if not triggered directly by user gesture
    }
  };

  const isCameraUnavailable = telemetry?.error === "camera_unavailable";
  const shouldStream = connected && tabVisible && !isCameraUnavailable;
  const streamSrc = shouldStream
    ? `${API_URL}/api/v1/video/stream?overlay=true&t=${streamKey}`
    : undefined;

  const frameReady = connected && hasLoadedFrame;

  // Single overlay priority
  let overlayMessage: string | null = null;
  if (!connected) {
    overlayMessage = "Chưa kết nối tới backend…";
  } else if (isCameraUnavailable) {
    overlayMessage =
      "Không mở được camera. Kiểm tra camera có đang được ứng dụng khác dùng không.";
  } else if (!frameReady) {
    overlayMessage = "Đang chờ hình từ camera…";
  }

  // Face detection alert only shown when video is actively rendered with frame
  const showNoFaceAlert =
    frameReady &&
    !overlayMessage &&
    Boolean(telemetry && !telemetry.face_detected);

  const level: RiskLevel = telemetry?.risk_level ?? "NORMAL";
  const fpsCamera =
    telemetry?.fps?.camera !== undefined ? telemetry.fps.camera.toFixed(1) : "—";
  const fpsFace =
    telemetry?.fps?.face !== undefined ? telemetry.fps.face.toFixed(1) : "—";
  const fpsPhone =
    telemetry?.fps?.phone !== undefined ? telemetry.fps.phone.toFixed(1) : "—";
  const latencyFace =
    telemetry?.latency_ms?.face !== undefined
      ? telemetry.latency_ms.face.toFixed(0)
      : "—";
  const latencyPhone =
    telemetry?.latency_ms?.phone !== undefined
      ? telemetry.latency_ms.phone.toFixed(0)
      : "—";

  return (
    <div className="camera-panel">
      {/* Khung video: 4:3, max 960px, căn giữa, viền 1px, bo 6px, nền đen */}
      <div ref={videoContainerRef} className="camera-video">
        {shouldStream && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={connected ? "connected" : "disconnected"}
            src={streamSrc}
            alt="Luồng camera tài xế"
            onLoad={() => setHasLoadedFrame(true)}
            className="camera-img"
          />
        )}
        {overlayMessage && (
          <div className="camera-overlay" role="status">
            {overlayMessage}
          </div>
        )}
      </div>

      {/* Dòng cảnh báo không thấy khuôn mặt ở dưới khung khi có hình */}
      {showNoFaceAlert && (
        <p className="camera-face-alert" role="status">
          Không thấy khuôn mặt
        </p>
      )}

      {/* Hàng thông tin gọn dưới khung video */}
      <div className="camera-info-bar">
        <div className="camera-metrics">
          {/* Mức rủi ro + điểm */}
          <div className="camera-metric-item">
            <span className="camera-metric-label">Rủi ro:</span>
            <span className={`camera-level camera-level-${level.toLowerCase()}`}>
              <svg
                width="16"
                height="16"
                viewBox="0 0 20 20"
                fill="none"
                aria-hidden="true"
              >
                <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.7" />
                <text
                  x="10"
                  y="14"
                  textAnchor="middle"
                  fill="currentColor"
                  fontSize="12"
                  fontWeight="600"
                >
                  {level === "NORMAL" ? "✓" : level === "WARNING" ? "!" : "⚠"}
                </text>
              </svg>
              {RISK_LABELS[level]}
            </span>
            <span className="camera-score tabular-nums">
              {telemetry ? telemetry.risk_score.toFixed(0) : "—"}
            </span>
          </div>

          {/* FPS camera / mặt / điện thoại */}
          <div className="camera-metric-item">
            <span className="camera-metric-label">FPS:</span>
            <span className="tabular-nums">
              {telemetry
                ? `${fpsCamera} cam · ${fpsFace} mặt · ${fpsPhone} đt`
                : "—"}
            </span>
          </div>

          {/* Độ trễ mặt / điện thoại */}
          <div className="camera-metric-item">
            <span className="camera-metric-label">Độ trễ:</span>
            <span className="tabular-nums">
              {telemetry
                ? `${latencyFace} ms mặt · ${latencyPhone} ms đt`
                : "—"}
            </span>
          </div>
        </div>

        {/* Nút Toàn màn hình */}
        {supportsFullscreen && (
          <button
            type="button"
            onClick={handleToggleFullscreen}
            aria-label={isFullscreen ? "Thoát toàn màn hình" : "Xem toàn màn hình"}
            className="camera-button"
          >
            {isFullscreen ? "Thoát toàn màn hình" : "Toàn màn hình"}
          </button>
        )}
      </div>
    </div>
  );
}
