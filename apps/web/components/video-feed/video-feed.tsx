import { API_URL } from "@/lib/api";

export function VideoFeed({ active }: { active: boolean }) {
  return (
    <div className="monitor-video">
      {active ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={`${API_URL}/api/v1/video/stream?overlay=true`}
          alt="Luồng camera tài xế"
          className="h-full w-full object-contain"
        />
      ) : (
        <div className="flex h-full items-center justify-center text-sm text-[var(--text-muted,#5c5c57)]">
          Chưa kết nối tới backend…
        </div>
      )}
    </div>
  );
}
