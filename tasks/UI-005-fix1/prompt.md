Tự viết code TRỰC TIẾP bằng công cụ ghi file. KHÔNG giao subagent, KHÔNG chạy lệnh shell. Khi ghi xong, trả lời theo định dạng ở cuối (bắt đầu bằng "## OUTPUT_START", kết thúc bằng "## OUTPUT_END").

Vòng sửa lỗi 1/3 cho task UI-005. CHỈ sửa file apps/web/components/camera/live-view.tsx, không đổi giao diện hay hành vi hiển thị.

Lỗi eslint `react-hooks/set-state-in-effect` (gọi setState đồng bộ trong thân effect), 2 chỗ:
1. Effect "Reset frame state when connection is lost": `if (!connected) setHasLoadedFrame(false)`. Nguyên nhân gốc: dùng state + effect cho giá trị có thể suy ra. Cách sửa: bỏ effect, suy ra `const frameReady = connected && hasLoadedFrame;` và dùng `frameReady` ở mọi nơi đang dùng `hasLoadedFrame` để quyết định hiển thị. Khi mất kết nối rồi kết nối lại, đảm bảo thẻ <img> được tạo mới để onLoad chạy lại (ví dụ thêm `key` thay đổi theo lần kết nối, như một biến đếm tăng trong callback sự kiện, hoặc key theo `connected`), để lớp phủ "Đang chờ hình từ camera…" hiện đúng.
2. Effect phát hiện Fullscreen: `setSupportsFullscreen(supported)` trong thân effect. Cách sửa: dùng `useSyncExternalStore` với `subscribe` rỗng (trả về hàm hủy rỗng), `getSnapshot` trả `Boolean(doc.fullscreenEnabled ?? doc.webkitFullscreenEnabled)` và `getServerSnapshot` trả `false`, thay cho state `supportsFullscreen`. Phần theo dõi `isFullscreen` bằng sự kiện `fullscreenchange` (setState nằm trong callback sự kiện) giữ nguyên.

Do Not Modify: mọi file khác. Out Of Scope: mọi thay đổi khác.
Tiêu chí: `npx eslint components/camera app/camera` không lỗi; giao diện và hành vi giữ nguyên.

## OUTPUT_START
1. File đã sửa
2. Cách sửa từng lỗi (tối đa 5 dòng)
3. Điểm chưa chắc
## OUTPUT_END
