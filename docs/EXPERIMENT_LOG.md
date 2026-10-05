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
| `mar_threshold` | 0,60 | MAR cao hơn → miệng mở rộng |
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
