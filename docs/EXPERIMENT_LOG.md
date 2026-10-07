# Nhật ký thí nghiệm và tham số (để làm báo cáo)

Ghi ngày 2026-10-05. Số liệu thô: `docs/experiments/phone_detection_coco.csv`.
Mọi số trong tài liệu này lấy từ lần chạy thật; mục nào chưa đo thì ghi rõ "chưa đo".

## 1. Môi trường

| Mục | Giá trị |
|---|---|
| Hệ điều hành | Windows 11 Pro 10.0.26200 |
| GPU | NVIDIA GeForce RTX 3050 Laptop, 4 GB VRAM, driver 610.88 (CUDA UMD 13.3) |
| Python | 3.11.9 (venv `.venv`) |
| PyTorch | 2.11.0+cu128 (CUDA 12.8), torchvision 0.26.0+cu128 |
| Ultralytics | 8.4.173 |
| MediaPipe | 1.0.1 (Tasks API, `face_landmarker.task` float16) |
| OpenCV | 5.0.0 · NumPy 2.4.6 · ONNX Runtime 1.30.0 |
| Backend | FastAPI 0.142.2, Pydantic 2.13.5, SQLite (stdlib) |
| Frontend | Next.js 16.3.8, React 19.2.8, Tailwind 4, TypeScript |
| Camera | webcam của máy, 640×480, DirectShow (`cv2.CAP_DSHOW`) |
| Công cụ điều phối | Claude (điều phối, kiểm tra), Codex CLI 0.160.0, Antigravity `agy` 1.2.16 |

## 2. Thí nghiệm: chọn model YOLO phát hiện điện thoại

### 2.1 Mục tiêu
Chọn model và cấu hình YOLO để phát hiện lớp `cell phone` (COCO id 67) cho sự kiện `PHONE_USAGE`.

### 2.2 Dữ liệu
- Nguồn: bộ `detection-datasets/coco` trên HuggingFace, tách `val`, tương đương COCO val2017 (4.952 ảnh).
  Tải file `val/0.parquet` và `val/1.parquet` (khoảng 807 MB) qua API parquet của HuggingFace.
  Không dùng `images.cocodataset.org` vì chứng chỉ SSL của máy chủ đó sai tên miền.
- Lớp điện thoại: id 67 (chỉ số 0–79). Định dạng hộp: `xyxy` (đã kiểm: 0 hộp có x2≤x1 hoặc y2≤y1).
- Tập dương: **214 ảnh có điện thoại, 262 hộp**.
- Tập âm: **400 ảnh không có điện thoại**, lấy ngẫu nhiên từ 4.738 ảnh, `random.seed(0)`.
- "Hộp lớn": hộp chiếm ≥ 2% diện tích ảnh (68 hộp), gần với điện thoại cầm trước camera trong xe.
- Hạn chế: ảnh đời thường, **không phải trong xe**; điện thoại thường nhỏ nên Recall thấp hơn thực tế.

### 2.3 Quy trình đo
- Suy luận: `model.predict(img, classes=[67], conf=<conf>, device=0, imgsz=<imgsz>, verbose=False)`.
- Khớp dự đoán – nhãn: IoU ≥ 0,5, tham lam theo độ tin cậy giảm dần; mỗi dự đoán khớp tối đa một nhãn.
- Chỉ số: Precision = TP/(TP+FP) trên tập dương; Recall = TP/(TP+FN) trên tập dương;
  F1; "báo giả/ảnh" = số hộp dự đoán trên 400 ảnh âm chia 400.
- Độ trễ: **trung vị** thời gian `predict` mỗi ảnh (ms), không tính giải mã ảnh. Không khởi động nóng (warm-up) riêng.
- VRAM đỉnh: `torch.cuda.max_memory_allocated()` sau khi reset cho mỗi cấu hình.
- Mã: `scripts/eval_phone_coco.py` (vòng lặp cuối được thay đổi giữa các lần chạy, xem bảng ở mục 2.4).

### 2.4 Kết quả đầy đủ (mọi lần chạy)

| # | Model | imgsz | conf | Precision | Recall | F1 | Recall hộp lớn | FP âm (400 ảnh) | ms/ảnh | VRAM (MiB) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | yolo11n | 320 | 0,35 | 0,81 | 0,20 | 0,32 | 0,51 | 1 | 20,2 | – |
| 2 | yolo26n | 320 | 0,35 | 0,89 | 0,19 | 0,31 | 0,50 | 1 | 21,4 | – |
| 3 | yolo11n | 640 | 0,35 | 0,84 | 0,33 | 0,48 | 0,65 | 1 | 20,8 | – |
| 4 | yolo26n | 640 | 0,35 | 0,89 | 0,30 | 0,45 | 0,63 | 0 | 21,4 | – |
| 5 | yolo11n | 640 | 0,20 | 0,73 | 0,40 | 0,52 | 0,72 | 3 | 20,0 | – |
| 6 | yolo26n | 640 | 0,20 | 0,79 | 0,36 | 0,50 | 0,71 | 2 | 21,2 | – |
| 7 | yolo11n | 960 | 0,35 | 0,79 | 0,38 | 0,51 | 0,60 | 0 | 21,8 | – |
| 8 | yolo26n | 960 | 0,35 | 0,88 | 0,37 | 0,52 | 0,66 | 1 | 23,6 | – |
| 9 | yolo11n | 960 | 0,20 | 0,71 | 0,47 | 0,56 | 0,71 | 1 | 21,7 | – |
| 10 | yolo26n | 960 | 0,20 | 0,81 | 0,47 | 0,60 | 0,71 | 2 | 23,8 | – |
| 11 | yolo26n | 640 | 0,25 | 0,84 | 0,34 | 0,48 | 0,68 | 2 | 12,2 | 65 |
| 12 | yolo26n | 960 | 0,25 | 0,86 | 0,43 | 0,57 | 0,71 | 2 | 14,9 | 95 |
| 13 | yolo26s | 640 | 0,25 | 0,78 | 0,54 | 0,64 | 0,81 | 2 | 21,1 | 111 |
| 14 | yolo26m | 640 | 0,25 | 0,80 | 0,61 | 0,70 | 0,84 | 1 | 24,4 | 229 |
| 15 | yolo26l | 640 | 0,25 | 0,83 | 0,65 | 0,73 | 0,81 | 3 | 35,4 | 337 |
| 16 | **yolo26x** | 640 | 0,25 | 0,84 | 0,69 | 0,76 | 0,85 | 3 | 53,8 | 394 |
| 17 | yolo26x | 960 | 0,25 | 0,81 | 0,72 | 0,76 | 0,87 | 4 | 114,7 | 563 |

Số tham số: yolo26n 2,6M · s 10,0M · m 21,9M · l 26,3M · x 59,0M. Trọng số: bản COCO tiền huấn luyện, chưa fine-tune.

**Lưu ý về độ trễ (quan trọng khi viết báo cáo):** độ trễ yolo26n đo được 21,4 ms (dòng 2, 4) và 12,2 ms (dòng 11)
tuy cùng imgsz 640. GPU laptop đổi xung nhịp theo tải và nhiệt nên độ trễ dao động giữa các lần chạy;
chỉ so sánh độ trễ giữa các dòng trong **cùng một lần chạy** (dòng 1–4 / 5–10 / 11–12 và 16–17 / 13–15).
Chưa lặp nhiều lần để có khoảng tin cậy.

### 2.5 Kết quả trong worker thật (camera + YOLO cùng chạy, 25 giây, không có người trước camera)

| Model | FPS camera | FPS mặt | FPS điện thoại | Độ trễ điện thoại |
|---|---|---|---|---|
| yolo26x | 30 | 30 | 5 | 63 ms |
| yolo26n | 15 | 15 | 5 | 35 ms |

FPS camera khác nhau giữa hai lần chạy do tự động phơi sáng của webcam (thiếu sáng thì giảm FPS), không phải do model.
Đo riêng `PhoneDetector.detect` trên khung đen 640×480: yolo26n 19,6 ms; yolo26x 55,6 ms.

### 2.6 Quyết định
- Mặc định: **`yolo26x.pt`, `imgsz=640`, `conf=0,25`** (biến môi trường `DRIVERGUARD_YOLO_MODEL` để đổi).
- Lý do: F1 0,76 và Recall hộp lớn 0,85 cao nhất ở imgsz 640; imgsz 960 không cải thiện F1 mà chậm gấp đôi.
- Thiết bị yếu: dùng yolo26m (F1 0,70, ~24 ms) hoặc yolo26s; cần đo lại trên thiết bị.
- Cấu hình ban đầu (yolo11n, 320, 0,35) bị loại vì Recall chỉ 0,20.
- Chưa làm: thử với điện thoại thật trong xe; fine-tune trên State Farm; đo lặp nhiều lần để có khoảng tin cậy.

## 3. Tham số hệ thống (`ai/config/thresholds.yaml` và hằng số trong code)

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `ear_threshold` | 0,20 | Ngưỡng dự phòng khi chưa hiệu chuẩn |
| Ngưỡng EAR sau hiệu chuẩn | 0,7 × EAR mở mắt, kẹp [0,10; 0,25] | Cá nhân hóa theo tài xế |
| `eyes_closed_s` | 1,8 | Nhắm mắt liên tục → `DROWSINESS_ACUTE` |
| `mar_threshold` | **0,50** (trước 0,60; đổi theo mục 10) | MAR cao hơn → miệng mở rộng |
| `yawn_s` | 2,0 | Miệng mở liên tục → ngáp |
| `yaw_threshold` / `pitch_threshold` | 30° / 20° | So với tư thế chuẩn |
| `head_s` | 2,0 | Quay/cúi đầu liên tục → sự kiện |
| `phone_s` | 1,5 | Điện thoại ở vùng sử dụng liên tục → `PHONE_USAGE` |
| `absence_s` | 3,0 | Không thấy mặt → `DRIVER_ABSENCE` |
| `cooldown_s` | 3,0 | Hạ nhiệt FSM, chống báo lặp |
| `calibration_s` | 4,0 | Cửa sổ tính trung vị yaw/pitch/EAR |
| `perclos_window_s` | 60 | Cửa sổ PERCLOS; chỉ tin khi đã quan sát ≥ 30 s |
| `yawn_window_s` | 300 | Cửa sổ đếm số lần ngáp |
| `pitch_sign` | 1,0 | Đổi thành −1,0 nếu cúi đầu cho pitch âm (**chưa kiểm chứng**) |
| Rủi ro mãn tính | min(70, PERCLOS×200 + số ngáp×10) | Sự kiện `CHRONIC_FATIGUE` khi ≥ 50, tối đa 1 lần/60 s |
| Rủi ro tức thời (ACTIVE) | nhắm mắt 90 · điện thoại 80 · quay đầu 65 · cúi đầu 65 · mất mặt 60 · ngáp 45 | Điểm nền cho từng sự kiện |
| Suy hao | λ = 0,3 (hàm mũ), Acute Bypass khi nhắm mắt ≥ 2,0 s → DANGER, điểm ≥ 70 | `RiskEngine` |
| Mức rủi ro | < 40 NORMAL · < 70 WARNING · ≥ 70 DANGER | `level_from_score` |
| Vùng điện thoại "đang dùng" | ngang ±1,5 rộng mặt; dọc từ −0,5 đến +3 cao mặt | `is_usage_region` |
| Tần suất | MediaPipe theo FPS camera; YOLO ~5 FPS (luồng riêng); telemetry ≤ 15 Hz | Worker |

Tại sao ngưỡng EAR cá nhân hóa: ảnh chân dung mẫu của MediaPipe cho EAR mở mắt = 0,207, sát ngưỡng cố định 0,20,
nên ngưỡng cố định sẽ báo "buồn ngủ" giả với người mắt nhỏ.

### Điểm landmark MediaPipe dùng
- Mắt phải `[33,160,158,133,153,144]`, mắt trái `[362,385,387,263,373,380]` (p1..p6).
- Miệng `[61,81,13,311,291,402,14,178]` (0=khóe trái, 1–3 môi trên, 4=khóe phải, 5–7 môi dưới).
- Góc đầu: tách Euler từ ma trận biến đổi 4×4 (`atan2` theo yaw/pitch/roll).

## 4. Kết quả kiểm chứng khác

| Phép đo | Kết quả |
|---|---|
| Ảnh chân dung mẫu (MediaPipe `portrait.jpg`, 820×1024) | EAR 0,207 · MAR 0,178 · yaw 1,76° · pitch 4,17° · roll 0,59° |
| Camera thật 25 s, không có người | 0% khung có mặt (đúng), sự kiện `DRIVER_ABSENCE`, không lỗi, thoát sạch sau lệnh stop |
| Mô phỏng 22 s | 216 bản tin telemetry, 215 khung JPEG, sự kiện nhắm mắt, risk đỉnh 90 |
| Test tự động | 41 test lõi AI + 5 test backend = **46 pass** (tại commit 92f4438) |
| Build dashboard | `npm run build` thành công |
| Tích hợp đầu–cuối | Backend mô phỏng + dashboard trên Chrome: kết nối WebSocket, video, risk meter, đồ thị, bảng sự kiện đều hoạt động |

## 5. Lỗi phát hiện khi kiểm tra và cách sửa (cho mục "Bài học")

1. FSM không kích hoạt đúng biên do sai số số thực (2,8 − 1,0 = 1,7999…) → thêm dung sai 1e-9.
2. PERCLOS báo mệt mỏi mãn tính sau vài giây do cửa sổ quá ít dữ liệu → chỉ tính khi quan sát ≥ nửa cửa sổ.
3. Ngưỡng EAR cố định gây báo giả với mắt nhỏ → ngưỡng cá nhân hóa theo hiệu chuẩn.
4. MediaPipe (C++) sập với đường dẫn có dấu tiếng Việt → nạp mô hình từ bytes.
5. Worker không thoát sau lệnh stop do hàng đợi còn dữ liệu → `cancel_join_thread()`.
6. Backend: `camera_connected` phụ thuộc việc thấy mặt; sự kiện không gắn phiên; `/config` thiếu ngưỡng; không tự tìm package `ai`.
7. Cấu hình YOLO ban đầu (imgsz 320) bỏ sót nhiều → 640 và model lớn hơn.

## 6. Việc chưa đo (cần ghi rõ trong báo cáo)

- Nhận diện mặt/EAR/MAR/góc đầu **với người thật trước camera**.
- Dấu pitch; ngưỡng ngáp (MAR 0,60); độ chính xác ROI điện thoại với điện thoại thật.
- F1, độ trễ phát hiện, báo giả/phút trên NTHU-DDD, YawDD, State Farm (Phase 8).
- Độ trễ có khoảng tin cậy (lặp ≥ 5 lần); đo trên thiết bị biên (Jetson, mini PC); ONNX/TensorRT.

## 7. Cách chạy lại

```powershell
# Test
.\.venv\Scripts\python.exe -m pytest ai -q
cd apps\backend; ..\..\.venv\Scripts\python.exe -m pytest tests -q
# Hệ thống
.\scripts\run_backend.ps1 [-Simulate]
.\scripts\run_web.ps1
# Chọn model điện thoại
$env:DRIVERGUARD_YOLO_MODEL = "yolo26m.pt"
```
Đánh giá model: tải 2 file parquet về thư mục hiện tại rồi chạy `python scripts/eval_phone_coco.py`
(cần `pip install pyarrow pillow`); sửa vòng lặp cuối của script để chọn model/imgsz/conf cần so.

## 8. Thí nghiệm 2: phát hiện điện thoại trong xe (State Farm)

### 8.1 Dữ liệu và quy trình
- Nguồn: `gymprathap/Driver-Distracted-Dataset` trên HuggingFace, bản sao của State Farm Distracted Driver Detection
  (Kaggle), 22.424 ảnh train, 10 lớp; số ảnh mỗi lớp khớp với bản Kaggle. Giấy phép ghi `cc` do người đăng tải;
  gốc là dữ liệu cuộc thi Kaggle, chỉ dùng cho nghiên cứu/đánh giá ở đây.
- **Mẫu: 150 ảnh/lớp × 10 lớp = 1.500 ảnh** (`random.seed(0)`), tải bằng HTTP range từ file zip 4 GB (`scripts/fetch_state_farm_sample.py`).
  Ảnh 640×480; camera đặt **bên cạnh tài xế** (nhìn nghiêng), xe đứng yên.
- Nhãn mức ảnh (không có hộp): **dương** = c1 nhắn tin (phải), c2 gọi (phải), c3 nhắn tin (trái), c4 gọi (trái) (600 ảnh);
  **âm** = c0 lái an toàn, c5 radio, c6 uống nước, c7 với ra sau, c8 trang điểm, c9 nói chuyện với hành khách (900 ảnh).
- Quyết định của ảnh: có ít nhất một hộp `cell phone` với độ tin cậy ≥ ngưỡng (cột "Có-hộp"), hoặc
  hộp đó nằm trong vùng sử dụng quanh mặt (`is_usage_region`) **và** MediaPipe thấy mặt (cột "PHONE_USAGE").
- Model: yolo26n/s/m/l/x COCO tiền huấn luyện, `imgsz=640`, ngưỡng 0,10/0,25/0,40, GPU. Mỗi ảnh một lần suy luận (conf 0,10, lọc sau).
  MediaPipe tạo mới cho mỗi ảnh. Mã: `scripts/eval_phone_state_farm.py`. Số liệu thô: `docs/experiments/phone_state_farm.{json,csv}`.

### 8.2 Kết quả (mức ảnh, ngưỡng tin cậy 0,25)

| Model | Độ trễ (ms) | Precision | Recall | F1 | Báo giả (FPR) |
|---|---|---|---|---|---|
| yolo26n | 11,2 | 0,98 | 0,15 | 0,26 | 0,00 |
| yolo26s | 13,0 | 0,84 | 0,66 | 0,74 | 0,08 |
| yolo26m | 25,2 | 0,82 | 0,81 | 0,81 | 0,12 |
| yolo26l | 31,3 | 0,86 | 0,82 | 0,84 | 0,09 |
| **yolo26x** | 53,8 | 0,86 | **0,90** | **0,88** | 0,10 |

yolo26x theo ngưỡng: conf 0,10 → P 0,75 R 0,95 F1 0,84 FPR 0,21; conf 0,25 → P 0,86 R 0,90 F1 0,88 FPR 0,10;
conf 0,40 → P 0,89 R 0,81 F1 0,85 FPR 0,07. (Ma trận nhầm yolo26x, 0,25: TP 539, FP 90, FN 61, TN 810.)

Tỉ lệ phát hiện điện thoại theo lớp, yolo26x, 0,25: c1 0,92 · c2 0,93 · c3 0,97 · c4 0,77 (đúng);
báo giả: c0 0,13 · c5 0,07 · c6 0,12 · c7 0,09 · c8 0,13 · c9 0,07.
yolo26n: c1 0,09 · c2 0,23 · c3 0,19 · c4 0,08 (gần như không dùng được trong xe).

### 8.3 Phát hiện chính
1. **Cỡ model quyết định.** Trong xe, yolo26n chỉ tìm được 15% ca dùng điện thoại, yolo26x tìm được 90%.
   Kết quả này khớp thí nghiệm 1 (COCO) và xác nhận chọn `yolo26x` làm mặc định. Trên ảnh trong xe, F1 (0,88) cao hơn nhiều so với COCO (0,76).
   Điện thoại lớn hơn trong khung hình nên dễ hơn.
2. **Không cần fine-tune trước mắt**: F1 0,88 với trọng số COCO. Chưa đo trên xe thật của sếp.
3. **Lỗi thiết kế của lọc vùng (ROI): phụ thuộc vào việc thấy mặt.** Tỉ lệ MediaPipe thấy mặt theo lớp:
   c0 0,19 · c1 0,35 · **c2 0,06** · c3 0,20 · c4 0,45 · c5 0,53 · c6 0,27 · c7 0,57 · c8 0,32 · c9 0,86.
   Khi dùng điện thoại, tay che mặt và mặt nghiêng nên mất mặt; Recall của PHONE_USAGE (cần ROI + mặt) chỉ 0,10 ở yolo26x
   (F1 0,18) so với 0,90 khi chỉ cần có hộp.
   Mặt thấp một phần do camera State Farm nhìn nghiêng (hình học khác hệ thống của chúng ta đặt camera chính diện),
   nhưng việc tay che mặt khi gọi điện thoại cũng xảy ra với camera chính diện.
4. **Hệ quả nghiêm trọng hơn:** khi mất mặt, hệ thống cũ báo `DRIVER_ABSENCE` ("không thấy tài xế") đúng lúc tài xế đang gọi điện.

### 8.4 Đã sửa sau thí nghiệm này (commit kèm theo)
- `FaceBoxHold`: giữ hộp mặt cuối cùng 2 giây để vẫn lọc ROI khi tay che mặt.
- Không báo `DRIVER_ABSENCE` nếu có điện thoại ở vùng sử dụng. Có test cho cả hai.
- **Chưa kiểm chứng lại bằng State Farm** vì ở bộ này mặt hầu như không bao giờ được thấy ngay từ đầu (nên giữ hộp mặt cũ không có tác dụng).
  Cần thử trên camera chính diện thật.

### 8.5 Hạn chế
- Nhãn mức ảnh, không có hộp: không tính được Precision/Recall theo hộp, chỉ "có/không phát hiện điện thoại" trên ảnh.
- Mẫu 1.500 ảnh (6,7% bộ train); không chia theo từng người lái (không có mã tài xế trong bản sao này), không có khoảng tin cậy.
- Độ trễ lấy trung vị trên 1.500 ảnh, một lần chạy.
- Dữ liệu chụp xe đứng yên, ban ngày; không có ban đêm/hồng ngoại.

## 9. Thí nghiệm 3: EAR phân biệt mắt nhắm / mở (ảnh khuôn mặt do AI sinh)

### 9.1 Dữ liệu và quy trình
- Nguồn: `MichalMlodawski/closed-open-eyes` (HuggingFace, giấy phép `odc-by`), 126.560 ảnh 512×512; thẻ tác giả: `ai-generated`,
  `balanced-dataset`. **Đây là khuôn mặt do AI sinh**, đa dạng tuổi, giới tính, bối cảnh (trong tàu, bãi biển, rừng...), có trẻ em.
  Không phải ảnh người lái thật.
- Mẫu: 20 phần (shard) cách đều trong 1.268 phần, mỗi phần 100 ảnh, xáo trộn `random.seed(0)`: **2.000 ảnh** = 1.100 nhắm (`closed_eyes`) + 900 mở (`open_eyes`).
  Nhãn theo cả phần/ảnh do tác giả cung cấp, không kiểm tra thủ công.
- Quy trình: MediaPipe FaceLandmarker (tạo mới cho mỗi ảnh) -> EAR trung bình hai mắt (`ai/features/ear.py`). Dự đoán "nhắm" khi EAR < ngưỡng.
- Mã: `scripts/eval_eye_state.py`; số liệu thô: `docs/experiments/eye_state_synthetic.json`.

### 9.2 Kết quả
| Chỉ số | Giá trị |
|---|---|
| Tỉ lệ MediaPipe thấy mặt | 100% (2.000/2.000) cả hai nhãn |
| AUC (EAR mở > EAR nhắm) | **0,997** |
| Ngưỡng cố định 0,20 | P 1,000 · R 0,970 · F1 **0,985** · báo giả (FPR) 0,000 (TP 1.067, FP 0, FN 33, TN 900) |
| Ngưỡng tốt nhất theo F1 (0,215) | P 0,999 · R 0,978 · F1 0,989 · FPR 0,001 |
| EAR mắt mở: phân vị 1 / 5 / 25 / 50 / 75 | 0,239 / 0,263 / 0,309 / 0,346 / 0,397 |
| EAR mắt nhắm: phân vị 50 / 75 / 95 / 99 | 0,042 / 0,079 / 0,166 / 0,263 |
| Mắt mở có EAR < 0,20 | 0,0% |
| Mắt nhắm có EAR ≥ 0,20 | 3,0% (33/1.100) |

### 9.3 Nhận xét và hạn chế (ghi rõ trong báo cáo)
- Công thức EAR + MediaPipe phân tách mắt nhắm/mở gần như hoàn hảo trên ảnh chính diện chất lượng cao; ngưỡng 0,20 gần tối ưu (chỉ cách ngưỡng tốt nhất 0,015).
- **Kết quả này có khả năng lạc quan**: ảnh sạch, chính diện, mắt mở rõ (mắt mở thấp nhất ở phân vị 1 vẫn là EAR 0,239), không mô phỏng
  mắt nhỏ, kính, thiếu sáng, đầu nghiêng, chớp mắt, hay mờ chuyển động.
- **Không kiểm chứng được ngưỡng cá nhân hóa**: ở thí nghiệm này không có ảnh mắt mở nào có EAR sát 0,20 (khác với ảnh mẫu MediaPipe có EAR mắt mở 0,207),
  và mỗi ảnh là một người nên không có hiệu chuẩn theo người. Lập luận cho ngưỡng cá nhân hóa vẫn chỉ dựa trên một ảnh mẫu.
- Mắt nhắm mà EAR ≥ 0,20 (3%): chưa phân tích nguyên nhân (nhắm hờ, mi mắt vẽ, góc nhìn); cần xem thủ công mẫu lỗi.
- Đo trên ảnh tĩnh, chưa đo độ trễ phát hiện (cần video + FSM) hay tỉ lệ báo giả khi chớp mắt bình thường.


## 10. Thí nghiệm 4: MAR phân biệt ngáp / không ngáp (ảnh khuôn mặt do AI sinh)

### 10.1 Dữ liệu và quy trình
- Nguồn: `c3rl/yawning-people` (HuggingFace, giấy phép `mit`), 5.093 ảnh "yawning" + 4.907 ảnh "notyawning", PNG 512×512. README trống.
  `dataset.csv` có cột `prompt`, `yawn_label`, `sleepy_label`: ảnh **do AI sinh từ mô tả văn bản**, nhãn lấy theo lời nhắc sinh ảnh, **không kiểm tra thủ công**
  (xem ảnh mẫu: đa số mặt ngáp há rộng; có ảnh giống hát/la hét; ảnh "không ngáp" gần như toàn mặt trung tính khép miệng).
- Mẫu: 400 ảnh mỗi lớp, ngẫu nhiên `random.seed(0)` = 800 ảnh.
- Quy trình: MediaPipe FaceLandmarker (tạo mới mỗi ảnh) -> MAR (`ai/features/mar.py`); dự đoán "ngáp" khi MAR > ngưỡng.
- Mã: `scripts/eval_yawn_state.py`; số liệu thô: `docs/experiments/yawn_state_synthetic.json`.
- Ghi chú đo: các chỉ số P/R/F1 chỉ tính trên ảnh mà MediaPipe thấy mặt. Recall tính cả ảnh mất mặt = TP / 400.

### 10.2 Kết quả
| Chỉ số | Giá trị |
|---|---|
| MediaPipe thấy mặt | ngáp 91,5% (366/400), không ngáp 99,3% (397/400) |
| AUC (MAR ngáp > MAR không ngáp) | **0,986** |
| MAR ngáp: phân vị 5 / 25 / 50 / 75 / 95 | 0,359 / 0,564 / 0,667 / 0,776 / 0,894 |
| MAR không ngáp: phân vị 50 / 75 / 95 / 99 | 0,009 / 0,024 / 0,299 / 0,567 |

| Ngưỡng MAR | Precision | Recall (có mặt) | F1 | Báo giả (FPR) | Recall tính cả mất mặt |
|---|---|---|---|---|---|
| 0,30 | 0,946 | 0,956 | 0,951 | 0,050 | 0,875 |
| 0,40 | 0,969 | 0,932 | 0,950 | 0,028 | 0,853 |
| **0,50** | 0,975 | 0,847 | 0,906 | 0,020 | 0,775 |
| 0,60 (cũ) | 0,992 | 0,675 | 0,803 | 0,005 | 0,618 |
| 0,70 | 1,000 | 0,418 | 0,590 | 0,000 | 0,383 |
| Tốt nhất theo F1 (0,36) | 0,964 | 0,948 | 0,956 | 0,033 | 0,868 |

### 10.3 Kết luận và thay đổi
- MAR phân tách ngáp rõ (AUC 0,986), nhưng **ngưỡng cũ 0,60 quá cao**: bỏ sót 1/3 số ca ngáp (Recall 0,675; tính cả mất mặt chỉ 0,618).
- **Đổi mặc định `mar_threshold` 0,60 -> 0,50** (F1 0,906, báo giả 2%, Recall 0,847). Không chọn mức tối ưu 0,36 vì dữ liệu âm quá "dễ"
  (toàn mặt khép miệng): khi nói chuyện hoặc cười, MAR thực tế lên 0,2–0,5 nên ngưỡng thấp sẽ báo giả nhiều hơn số đo ở đây.
  Bộ lọc thời gian (miệng mở liên tục ≥ 2 giây) giảm báo giả do nói chuyện/cười thoáng qua nhưng chưa được đo.
- Ngoài ra 8,5% ảnh ngáp bị mất mặt (miệng há rộng, che khuất) -> cần xử lý ở tầng pipeline (đã có giữ mặt cuối 2 giây cho ROI điện thoại; ngáp chưa có).

### 10.4 Hạn chế
- Ảnh do AI sinh, nhãn theo lời nhắc, không kiểm tra thủ công; một số ảnh "ngáp" có thể là hát/la hét.
- Không có ảnh nói chuyện/cười/ăn/uống làm âm tính khó; FPR ở bảng là cận dưới (lạc quan).
- Ảnh tĩnh, chưa đo thời lượng miệng mở trong video (cần YawDD thật hoặc quay người thật).
- Ngưỡng 0,50 là thỏa hiệp chưa kiểm chứng trên người thật.

## 11. Thí nghiệm 5: phiên thử có hướng dẫn với người thật trên camera laptop

### 11.1 Thiết lập
- 1 người tham gia (n = 1), ngồi trước camera laptop, đèn trong nhà. Camera đặt trên màn hình nên nhìn từ trên xuống.
- Backend chạy camera thật (không mô phỏng), cấu hình khi đó: `mar_threshold` 0,50; ngưỡng mắt = 0,7 × EAR mở mắt (kẹp 0,10–0,25); YOLO `yolo26x`.
- Kịch bản `scripts/live_session.py` (trang đếm giờ + ghi telemetry): 16 pha, khoảng 87 giây ghi được, **823 bản tin**, chỉ lưu chỉ số (EAR, MAR, góc, cờ), không lưu hình.
- Số liệu thô: `docs/experiments/live_session.json`.
- **Lỗi thiết lập của tôi**: không bấm hiệu chuẩn lại ngay trước phiên, nên mốc tư thế chuẩn là tư thế lúc backend khởi động, không phải lúc bắt đầu; do đó các góc "tương đối" trong bảng bị lệch. Góc tuyệt đối (yaw/pitch) và EAR/MAR không bị ảnh hưởng.
- Hiệu năng: FPS camera/mặt trung vị **15** (mục tiêu UR-15 ≥ 20, chưa đạt do camera laptop ở 15 FPS trong nhà), độ trễ xử lý mặt trung vị **14 ms**, YOLO ~5 FPS.

### 11.2 Kết quả theo pha (thời gian liên tục dài nhất, giây, mặt thấy mặt)
| Pha | Việc người thử làm | EAR<0,20 | EAR<0,15 | MAR>0,30 | MAR>0,40 | MAR>0,50 | Cờ/sự kiện của hệ thống |
|---|---|---|---|---|---|---|---|
| nhắm mắt | nhắm mắt 4 giây | 3,95 | 3,82 | 0 | 0 | 0 | eyes_closed + DROWSINESS_ACUTE (**đúng**) |
| chớp mắt | chớp bình thường | 0,80 | 0,80 | 0 | 0 | 0 | không (**đúng**) |
| cúi đầu | cúi nhìn xuống | 2,21 | 2,21 | 0 | 0 | 0 | LOOKING_DOWN (**đúng**) + DROWSINESS_ACUTE (**báo giả**) |
| ngáp | há miệng to 4 giây | 2,61 | 0,34 | 3,22 | 3,07 | 0,94 | **không có cờ ngáp** (MAR ≤ 0,50 không đủ 2 giây) + DROWSINESS_ACUTE (**báo giả**) |
| nói chuyện | đếm 1–15 | 1,25 | 0,61 | 0 | 0 | 0 | không (**đúng**) |
| cười | cười to | 2,43 | 1,01 | 0 | 0 | 0 | DROWSINESS_ACUTE (**báo giả**) |
| quay trái | quay đầu trái | 0,26 | 0 | 0,34 | 0,13 | 0 | không có LOOKING_AWAY (thấy mặt 83%) |
| quay phải | quay đầu phải | 0 | 0 | 0,07 | 0 | 0 | không có LOOKING_AWAY (**mất mặt ~1,5 giây, thấy mặt 65%**) |
| điện thoại | cầm điện thoại trước ngực | 1,14 | 0,93 | 0 | 0 | 0 | `phone_detected` 5/54 bản tin, không có PHONE_USAGE |

### 11.3 Phát hiện
1. **Dấu của pitch đúng** (`pitch_sign = +1`): cúi đầu cho `relative_pitch` đạt +25,8°, vượt 20° trong 2,09 giây và hệ thống phát LOOKING_DOWN.
2. **Nhắm mắt thật được phát hiện** (EAR trung vị 0,095, liên tục 3,95 giây) và chớp mắt/nói chuyện không báo nhầm.
3. **Báo giả buồn ngủ ở 3 tình huống**: cúi đầu, ngáp, cười. EAR tụt dưới 0,20 liên tục hơn 1,8 giây vì nheo mắt khi cười/ngáp và vì góc nhìn từ camera khi cúi đầu.
   Với ngưỡng 0,15: cười (1,01 giây) và ngáp (0,34 giây) hết báo giả, nhưng cúi đầu vẫn 2,21 giây; nhắm mắt thật vẫn 3,82 giây.
4. **Ngáp không được phát hiện với MAR 0,50**: miệng mở có MAR 0,5–0,66 nhưng chỉ liên tục > 0,50 trong 0,94 giây. Với 0,40 là 3,07 giây (≥ 2 giây).
   Nói chuyện (MAR tối đa 0,30) và cười (tối đa 0,33) không vượt 0,40. Với người này, 0,40 tách sạch ngáp khỏi nói chuyện và cười.
5. **Lỗ hổng "mất mặt khi quay đầu lớn"**: khi quay phải khoảng 50°, MediaPipe mất mặt hơn 1 giây; vì tín hiệu LOOKING_AWAY yêu cầu thấy mặt nên không phát cảnh báo, và DRIVER_ABSENCE chưa tới 3 giây.
6. **Quay trái chưa đạt ngưỡng**: góc tương đối đạt khoảng 27–33° (ngưỡng 30°), không kéo dài 2 giây.
7. **Điện thoại: chưa kết luận được**: YOLO chỉ thấy điện thoại 5/54 bản tin khi cầm trước ngực. Chưa biết điện thoại có nằm trong khung hình camera laptop hay không.
8. **Hiệu chuẩn tư thế dễ sai** nếu người dùng chưa vào tư thế khi hệ thống tự hiệu chuẩn lần đầu (xem 11.1).

### 11.4 Hạn chế
- n = 1 người, một lần chạy, camera laptop góc nhìn từ trên, ánh sáng trong nhà; không có kính râm/ban đêm.
- Kịch bản diễn: mắt nhắm, ngáp và cười "theo lệnh" khác hành vi tự nhiên thật.
- Độ trễ phát hiện tính từ mốc hướng dẫn không chính xác vì người thử có thể phản ứng sớm hoặc muộn.
- Chưa có chấm điểm tự động theo nhãn thời gian; phân tích bằng thống kê theo pha.

## 12. Sửa lỗi sau thí nghiệm 5 và kiểm chứng bằng phát lại (task AI-001, Codex viết, Claude review)

### 12.1 Thay đổi (commit kèm theo)
| Mục | Trước | Sau | Lý do |
|---|---|---|---|
| `mar_threshold` | 0,50 | **0,40** | Ngáp thật liên tục MAR > 0,40 trong 3,07 giây; nói chuyện/cười tối đa 0,30/0,33 |
| Hệ số ngưỡng nhắm mắt (theo EAR mở mắt của người dùng) | 0,7, kẹp [0,10; 0,25] | **0,55, kẹp [0,10; 0,20]** | Cười/ngáp làm EAR < 0,20 hơn 1,8 giây (báo giả) |
| Ngưỡng nhắm mắt dự phòng (chưa hiệu chuẩn) | 0,20 | **0,15** | Cùng lý do |
| Không tính "nhắm mắt" khi | – | `relative_pitch > 20°` (đang cúi) hoặc `MAR > mar_threshold` (đang ngáp) | Cúi đầu và ngáp làm EAR giảm; đã có sự kiện LOOKING_DOWN / tín hiệu ngáp |
| Mất mặt sau khi quay đầu lớn | Không có cảnh báo, sau 3 giây là DRIVER_ABSENCE | Trong ≤ 3 giây kể từ lần thấy mặt cuối với \|yaw tương đối\| ≥ 24° (0,8 × 30°): tính là LOOKING_AWAY, không báo DRIVER_ABSENCE | MediaPipe mất mặt khi quay ≥ ~50° |

Test: 48 test lõi AI (trước 43) + 5 test backend, đều đạt; thêm 5 test mới cho các tình huống trên.

### 12.2 Kiểm chứng bằng phát lại dữ liệu thật (scripts/replay_live_session.py)
Phát lại 823 bản tin của phiên thử qua pipeline mới (hiệu chuẩn lại từ 4 giây đầu phiên: EAR mở mắt 0,233 -> ngưỡng nhắm mắt 0,128):
| Pha | Trước (ghi lúc thử) | Sau (phát lại) |
|---|---|---|
| nhắm mắt | DROWSINESS_ACUTE (đúng) | DROWSINESS_ACUTE (đúng) |
| cười | DROWSINESS_ACUTE (**báo giả**) | không cảnh báo |
| ngáp | DROWSINESS_ACUTE (**báo giả**), không có cờ ngáp | cờ `yawning` bật (**đúng**), không báo buồn ngủ |
| cúi đầu | LOOKING_DOWN + DROWSINESS_ACUTE (**báo giả**) | chỉ LOOKING_DOWN |
| quay phải | không cảnh báo (mất mặt) | LOOKING_AWAY (**đúng**) |
| quay trái | không cảnh báo | không cảnh báo (góc 27–33° chưa vượt ngưỡng 30° đủ lâu) |
| chớp mắt, nói chuyện | không cảnh báo | không cảnh báo |

### 12.3 Hạn chế (ghi rõ trong báo cáo)
- **Kiểm chứng trên chính dữ liệu đã dùng để chỉnh tham số** (không phải tập kiểm tra riêng); n = 1 người; sau khi chỉnh cần quay lại phiên mới.
- Quay trái vẫn không được phát hiện: góc 27–33° so với ngưỡng 30°; chưa đổi ngưỡng vì chỉ có một người thử.
- Xuất hiện `CHRONIC_FATIGUE` ở giữa phiên: PERCLOS đạt ≥ 25% trong cửa sổ ngắn do kịch bản nhắm mắt nhiều lần; hành vi hợp lý với kịch bản nhưng chưa đánh giá trên lái xe thực.
- Điện thoại vẫn chưa kết luận (phát lại không có thông tin vùng ROI).
- Phát lại dùng roll = 0 vì phiên không lưu roll (không ảnh hưởng logic hiện tại).

## 13. Thí nghiệm 6 (EXP-006): phiên thử người thật lần 2, chấm tự động

### 13.1 Thiết lập
- Cùng người tham gia như thí nghiệm 5 (n = 1), camera laptop, trong nhà. Cấu hình sau AI-001 (`mar_threshold` 0,40; hệ số EAR 0,55 kẹp [0,10; 0,20]). **Không chỉnh tham số trước phiên.**
- `scripts/live_session.py` (tự hiệu chuẩn 4 giây trước phiên), 22 pha, 101 giây, **1.164 bản tin** trong khoảng pha. Số liệu thô: `docs/experiments/live_session_2.json`; kết quả chấm: `live_session_2.csv` (`scripts/score_live_session.py`).
- Hiệu năng: FPS camera/mặt **30** (thí nghiệm 5: 15), YOLO 5 FPS.

### 13.2 Kết quả
Phát hiện đúng **4/9 pha cần cảnh báo**, **báo giả 0**, độ trễ trung vị 2,97 giây (chấm theo mốc hướng dẫn).

| Pha | Kết quả | Số đo liên quan |
|---|---|---|
| nhắm mắt | đúng, trễ 3,24 s | EAR nhỏ nhất 0,03 |
| quay phải (lần 1) | đúng | mất mặt, tính là LOOKING_AWAY |
| điện thoại trước ngực | đúng, trễ 2,96 s | |
| điện thoại ngang mặt | đúng, trễ 2,99 s | |
| quay trái (lần 1) | sót | \|yaw tương đối\| tối đa 60° |
| quay trái (lần 2) | sót | tối đa 37° |
| quay phải (lần 2) | sót | tối đa 39°, thấy mặt 52% |
| cúi đầu | sót | pitch tối đa 23°, thấy mặt 38% |
| ngáp | sót | **MAR tối đa 0,32** (< 0,40) |
Chớp mắt, nói chuyện, cười và các pha nghỉ: không báo nhầm.

### 13.3 Phân tích
1. **Ngưỡng MAR 0,40 không tổng quát**: ngáp ở thí nghiệm 5 đạt MAR 0,5–0,66, lần này chỉ 0,32 (cùng người). Kết quả "đúng" ở mục 12.2 là lạc quan do chỉnh và chấm trên cùng dữ liệu.
2. **Quay trái 60° bị sót không phải lỗi logic**: người thử bắt đầu quay sau mốc khoảng 1,7 giây, yaw chỉ vượt 30° trong khoảng 0,4 giây rồi mất mặt ở giây 3,8 (pha dài 4 giây). Cần pha dài hơn (≥ 6 giây) hoặc chấm theo hành vi thực, không theo mốc.
3. **Mất mặt khi cúi/quay** vẫn là điểm yếu: cúi đầu mất mặt 62%, quay phải lần 2 mất 48%.
4. **Điện thoại phát hiện 2/2** (thí nghiệm 5: không kết luận được). Chưa rõ nguyên nhân khác biệt; cần lặp lại.
5. Báo giả 0 nhưng bỏ sót cao: hệ thống đang thiên về im lặng.

### 13.4 Hạn chế
n = 1, một lần chạy, mỗi pha 1–2 lần lặp; chấm theo mốc hướng dẫn nên độ trễ chỉ ước chừng; camera laptop góc từ trên; kịch bản diễn. Chưa chỉnh tham số sau lần này.

## 14. Thí nghiệm 7 (EXP-007): phiên người thật lần 3, pha 7 giây, có dữ liệu pose

### 14.1 Thiết lập
- Cùng người tham gia (n = 1), camera laptop, trong nhà, hệ thống bản AI-001 + AI-002 với `use_pose_fallback` **tắt** (cảnh báo thật chạy như cũ; pose chỉ ghi dữ liệu). Không chỉnh tham số trước phiên.
- `scripts/live_session.py`: các pha hành vi dài 7 giây, tổng 128 giây, **3.847 bản tin** (723 trong các pha chấm). FPS camera/mặt 30, pose 11 FPS (độ trễ 36 ms), điện thoại 6 FPS. Số liệu thô: `docs/experiments/live_session_3.json`, `live_session_3.csv`.

### 14.2 Kết quả chấm
| Cách chấm | Phát hiện đúng | Báo giả | Độ trễ trung vị |
|---|---|---|---|
| (a) theo mốc | **9/9** | 1 | 3,80 s |
| (b) bỏ 2 giây đầu | **9/9** | 1 | 1,80 s |
Mọi pha cần cảnh báo đều được phát hiện (nhắm mắt, quay trái x2, quay phải x2, cúi đầu, ngáp, điện thoại x2). Chớp mắt, nói chuyện, cười: không báo nhầm. Báo giả 1: pha nghỉ `rest9` (sau khi hạ điện thoại) có `LOOKING_AWAY`; chưa phân biệt được do người thử quay đầu thật hay báo nhầm. Quay trái lần 2 phát hiện rất sát (độ trễ 7,06 s, cờ chỉ 1,3% bản tin).

### 14.3 Phân tích
1. **EXP-006 (4/9) sót chủ yếu do thiết kế phiên**: cùng người, cùng hệ thống, chỉ kéo pha lên 7 giây thì 9/9. Không dùng EXP-006 để kết luận hệ thống yếu hơn thực tế.
2. **Ngáp đạt lần này** (cờ 46%) dù ngưỡng MAR 0,40 không đổi; ở EXP-006 sót vì MAR chỉ 0,32. Hành vi ngáp giữa các lần diễn dao động; chưa kết luận về ngưỡng.
3. **Pose có tín hiệu tốt khi mất mặt**: trong 4 pha quay trái/phải, MediaPipe mất mặt 28–56 bản tin/pha và pose thấy người ở **100%** số khung đó (181/181). `yaw_rel` của pose đạt 0,42–0,59 khi quay (ngưỡng tạm 0,35), và ở pha cúi đầu/nhìn thẳng chỉ dao động −0,04–0,03, tức tách rõ.
4. **Phát lại với `--pose-fallback` không thay đổi số pha phát hiện** (đã 9/9 không cần pose); chỉ thêm cờ `looking_away` kéo dài sang pha nghỉ liền sau (rest2). Chưa đo độ trễ phát hiện theo từng cờ trong replay.
5. Pha cúi đầu: MediaPipe thấy mặt 100% lần này (EXP-006: 38%), nên chưa kiểm tra được pose khi mất mặt lúc cúi.

### 14.4 Hạn chế
n = 1, một lần chạy, cùng người ở cả ba phiên; ngưỡng pose (0,35/0,30) chưa được chỉnh hay kiểm chứng độc lập (chỉ so với dữ liệu này); chưa có người thứ hai; camera laptop góc từ trên; chưa đo ca pose cứu được khi MediaPipe sót (vì chưa có ca sót); phát lại chưa có thông tin ROI điện thoại.

## 15. Thí nghiệm 8 (EXP-008): pose fallback trên video công khai từ mạng (Codex viết script, Claude duyệt ảnh)

### 15.1 Thiết lập
- 4 video YouTube tải bằng `yt-dlp` (lưu `data/raw/web_videos/`, không đưa vào git): `FD5ctXyExqc` (camera hồng ngoại trong cabin, người đeo khẩu trang + kính, 317 s, 15 FPS), `VPnBwC1fOJY` (người đeo kính đen, có ngáp, 93 s), `lKIkpzwuaWs` (webcam, quay đầu, 43 s), `3psnER2oVUA` (nhiều người ghép cảnh, 587 s). Không có nhãn chuẩn.
- `scripts/eval_video_pose.py`: phát lại đồng bộ (t = chỉ số khung / fps), cùng quan sát MediaPipe + YOLO pose đưa vào hai `DriverPipeline`: A `use_pose_fallback=False`, B `True`. Ngưỡng giữ nguyên. Đầu ra: `docs/experiments/web_video/` (CSV từng khung, `summary.json`, 81 ảnh mẫu).

### 15.2 Kết quả
| Video | Mất mặt sau hiệu chuẩn | Pose thấy người (cả video) | Pose baseline | Khung A≠B |
|---|---|---|---|---|
| FD5ctXyExqc (hồng ngoại, khẩu trang) | 656/4.679 (14,0%) | 380/4.739 (8,0%) | **không đặt được** | 11 |
| VPnBwC1fOJY | 0 | 100% | có | 0 |
| lKIkpzwuaWs | 0 | 96% | có | 0 |
| 3psnER2oVUA (montage) | 65% | — | — | 9.685 (không có ý nghĩa) |

### 15.3 Phân tích (đã duyệt ảnh mẫu)
1. **Hai video webcam bình thường: MediaPipe không mất mặt, nên pose fallback không có cơ hội tác động.** Không chứng minh được có ích.
2. **Video khó nhất (hồng ngoại, khẩu trang): YOLO pose chỉ thấy người 8% số khung** và trong 4 giây hiệu chuẩn không có mẫu pose nào, nên `pose_yaw_baseline` không bao giờ được đặt, `pose_yaw_rel` luôn rỗng và nhánh `pose_away/pose_down` không bao giờ chạy. Mô hình pose yếu trên ảnh hồng ngoại hoặc khi mặt bị che.
3. **Cờ bật làm mất một phát hiện đúng.** Ở t≈313 s người quay hẳn nghiêng (nhìn qua ảnh mẫu là đúng LOOKING_AWAY): A (tắt) báo LOOKING_AWAY 11 khung, B (bật) báo không. Nguyên nhân từ mã: `held_away = recent_away and not (use_pose_fallback and pose_fresh)` (`ai/runtime/pipeline.py:175`) tắt cơ chế giữ cờ khi pose "tươi", dù pose chưa hiệu chuẩn nên không thay thế được.
4. **Cúi đầu mất mặt bị báo `DRIVER_ABSENCE` ở cả A và B** (ví dụ t=43,2 s, người cúi, mặt vẫn trong khung): pose không cứu được, vì cúi sát camera thì không thấy vai.
5. Video montage nhiều cảnh vô nghĩa cho phép đo này (pose thấy người khác trong cảnh).

### 15.4 Kết luận và hạn chế
Chưa có bằng chứng bật cờ có lợi; có bằng chứng bật cờ có hại ở một trường hợp. **Giữ `use_pose_fallback` TẮT.** Nếu muốn tiếp tục: (a) chỉ tắt `held_away` khi baseline pose đã có (sửa nhỏ, cần giao Codex); (b) cần video có MediaPipe mất mặt nhưng pose thấy người (quay nghiêng ánh sáng thường), hoặc thử weights pose khác cho ảnh hồng ngoại. Hạn chế: 3 video có nghĩa, không nhãn, một người mỗi video, nguồn quảng cáo/demo nên không chắc phản ánh điều kiện lái thật; số liệu mất mặt tính theo MediaPipe.

### 14.5 Điều tra báo giả rest9 (bổ sung, Claude phân tích từ `live_session_3.json`)
Báo giả `rest9` **không phải báo nhầm của hệ thống**: từ 1,4 s trước mốc `rest9` đến 0,75 s sau mốc, `relative_yaw` của MediaPipe giữ 44–49° (≥ ngưỡng 30°) trong 24 bản tin, và `yaw_rel` của pose độc lập cũng đạt 0,33 (cùng hướng). Người thử quay đầu thật khi hạ điện thoại; sự kiện LOOKING_AWAY phát lúc 0,57 s sau mốc. Đây là lỗi cách chấm (pha nghỉ bị gán nhãn "không có hành vi" trong lúc người thử còn đang quay). Số báo giả hiệu chỉnh: 0 trên EXP-007 nếu loại 2 giây đầu pha nghỉ liền sau pha hành vi (cách (b) đã gần đúng hướng này). Chưa sửa scorer.
