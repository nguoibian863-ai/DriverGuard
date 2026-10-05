Khi người dùng yêu cầu một feature mới:

0. Đọc state/task-state.json và state/workflow-state.json — kiểm tra có task dang dở không
1. Đọc memory/summary.md (không đọc architecture.md đầy đủ trừ khi cần chi tiết)
2. (Tùy chọn) Gọi Retriever nếu task có tài liệu/API bên ngoài liên quan
3. Gọi Architect thiết kế
4. Gọi Planner chia task → khởi tạo entry trong state/task-state.json cho mỗi task
5. Với mỗi task:
   a. Sinh prompt (theo template Mục 9) → gọi scripts/run-gemini.ps1
   b. update-state.ps1 -Status implementing
   c. Chạy scripts/run-checks.ps1
      - FAIL → tạo fix-prompt ngay, quay lại bước a (tính vào fix_attempts)
      - PASS → update-state.ps1 -Status checked
   d. Gọi Reviewer + Security + QA → scripts/run-review.ps1
   e. update-state.ps1 -Status reviewing
   f. Còn CRITICAL/HIGH → update-state.ps1 -Status fixing -IncrementFixAttempts 1
      → sinh fix-prompt → quay lại bước a
      → chạm max_fix_attempts → update-state.ps1 -Status blocked → dừng, báo người dùng
   g. Đạt yêu cầu → update-state.ps1 -Status approved
6. Cập nhật memory/decisions.md, memory/architecture.md (nếu đổi kiến trúc),
   memory/roadmap.md, memory/summary.md

Không bao giờ bỏ qua bước review hoặc bước kiểm tra tự động.
