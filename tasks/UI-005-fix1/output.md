1. File đã sửa
- [apps/web/components/camera/live-view.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/camera/live-view.tsx)

2. Cách sửa từng lỗi (tối đa 5 dòng)
- Lỗi 1: Bỏ [`useEffect`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/camera/live-view.tsx#L54) reset frame; tính giá trị suy ra `frameReady = connected && hasLoadedFrame` cho hiển thị `overlayMessage` và `showNoFaceAlert`; gắn `key` theo `connected` cho thẻ `<img>` và reset `hasLoadedFrame` về `false` khi prop `connected` thay đổi trong lúc render.
- Lỗi 2: Bỏ state `supportsFullscreen` và lệnh gọi đồng bộ `setSupportsFullscreen`; thay bằng [`useSyncExternalStore`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/camera/live-view.tsx#L39-L43) với `subscribe` rỗng, `getSnapshot` đọc `fullscreenEnabled`/`webkitFullscreenEnabled` và `getServerSnapshot` trả `false`; giữ nguyên listener sự kiện `fullscreenchange`.

3. Điểm chưa chắc
- Do tuân thủ yêu cầu không chạy lệnh shell, chưa chạy trực tiếp lệnh `npx eslint components/camera app/camera` trong môi trường terminal để kiểm tra kết quả linter thực tế.
