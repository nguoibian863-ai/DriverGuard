Review implementation hiện tại.

0. Đọc state/task-state.json để biết task đang ở status nào
1. Sử dụng agent reviewer, security, qa, skill code-review
2. Gọi scripts/run-review.ps1 để gộp báo cáo
3. update-state.ps1 theo kết quả (reviewing / approved / blocked)

Không approve nếu còn CRITICAL.
