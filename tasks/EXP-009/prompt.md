Nhiệm vụ EXP-009: so sánh weights YOLO pose và tiền xử lý trên ảnh hồng ngoại. Đọc AGENTS.md, MEMORY.md (EXP-008, AI-003), docs/EXPERIMENT_LOG.md mục 15, ai/perception/pose_tracker.py, scripts/eval_video_pose.py.
Lý do: ở video hồng ngoại FD5ctXyExqc (người đeo khẩu trang, kính) YOLO26m-pose chỉ thấy người ở 8% khung, nên pose fallback vô dụng ở ca khó nhất. Cần biết đổi weights hoặc tăng tương phản có cải thiện không.
Dữ liệu: data/raw/web_videos/{FD5ctXyExqc,VPnBwC1fOJY,lKIkpzwuaWs}.mp4 (không sửa, không tải lại). GPU RTX 3050 4 GB đang dùng chung với backend (~1,2 GB), nên chạy lần lượt từng model, giải phóng bộ nhớ giữa các model; nếu hết VRAM thì ghi "OOM" cho model đó và đi tiếp.
Được chạy: py_compile, script mới, pytest ai (kỳ vọng 56 passed). Được tải weights bằng ultralytics (auto-download) vào models/ (đã gitignore *.pt). Chỉ được tạo: scripts/eval_pose_weights.py và đầu ra trong docs/experiments/web_video/ (pose_weights.json, pose_weights.csv). KHÔNG sửa ai/, apps/, tệp khác, không đổi ngưỡng, không thêm dependency, không bật use_pose_fallback.

Việc cần làm: viết scripts/eval_pose_weights.py. Với mỗi video, đọc mọi khung (hoặc mỗi 2 khung nếu quá chậm, ghi rõ), chạy MediaPipe FaceLandmarkTracker để biết khung nào mất mặt, và với mỗi cấu hình (weights x tiền xử lý x conf) chạy YOLO pose và đo:
- tỷ lệ khung có phát hiện người (bất kỳ);
- tỷ lệ khung mà compute_pose_features trả về khác None (mũi và hai vai conf ≥ 0,3), dùng đúng hàm trong pose_tracker.py;
- hai tỷ lệ trên tính riêng trong các khung MediaPipe mất mặt;
- độ trễ trung vị (ms/khung) và VRAM đỉnh (torch.cuda.max_memory_allocated).
Cấu hình: weights = yolo26m-pose.pt (hiện tại), yolo26l-pose.pt, yolo26x-pose.pt, yolo11m-pose.pt, yolo11x-pose.pt (bỏ cái nào không tải được và ghi rõ); tiền xử lý = none, CLAHE trên kênh xám (cv2.createCLAHE clip 3,0 tile 8x8, nhân ra 3 kênh), và gamma 0,6 (làm sáng ảnh tối); conf = 0,25 và 0,10; imgsz=640. Không cần chạy đủ tổ hợp trên cả 3 video: chạy đủ tổ hợp trên FD5ctXyExqc, và chỉ chạy 2 cấu hình tốt nhất cộng cấu hình hiện tại trên hai video còn lại để kiểm tra không tệ đi. Dùng cache kết quả MediaPipe mất mặt để khỏi chạy lại.
Báo cáo ngắn: bảng kết quả theo cấu hình (FD), cấu hình tốt nhất, độ trễ/VRAM, pytest, điểm chưa chắc. Không kết luận có nên đổi weights hay không, chỉ số đo.
