Đọc kết quả review gần nhất (reviews/<task-id>-*.md) và state/task-state.json.

Nếu fix_attempts >= max_fix_attempts: DỪNG, báo người dùng, không gọi Gemini thêm.

Ngược lại, sinh fix-prompt cho Gemini gồm:
- Vấn đề
- Nguyên nhân gốc
- File liên quan
- Yêu cầu sửa cụ thể

Chỉ sửa đúng lỗi đã báo cáo. Không thiết kế lại kiến trúc.
update-state.ps1 -Status fixing -IncrementFixAttempts 1
