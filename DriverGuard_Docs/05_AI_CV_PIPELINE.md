# AI / Computer Vision Pipeline

## 1. Mục tiêu và Kiến trúc Đa Tần Số (Decoupled-Rate Inference)

Chuyển luồng video thành các sự kiện an toàn chính xác, tối ưu hóa phần cứng bằng cách phân tách chu kỳ suy luận:

```text
CAMERA (30 FPS)
     │
     ▼
Latest Frame Buffer
     │
     ├────────► Face & Landmarks (20–30 FPS) ──► EAR, MAR, Relative Head Pose
     │
     └────────► Phone Detector (3–5 FPS)      ──► ROI Filtering (Hand/Face)
                     │
                     ▼
             Temporal FSM (Smoothing)
                     │
                     ▼
             Dual Risk Engine (Acute & Chronic + Decay)
                     │
                     ▼
             Alert & Event Publishing
```

---

## 2. Face Landmarks & Hình Học Mắt, Miệng

Sử dụng **MediaPipe Face Mesh** trích xuất 468/478 điểm mốc với chi phí CPU thấp:
- **EAR (Eye Aspect Ratio)**: Ước lượng độ mở của mắt từ các landmark mí mắt trên/dưới và khóe mắt.
  - `EAR thấp` kéo dài > $T_{eye}$ (ví dụ 1.8s) $\rightarrow$ Nguy cơ buồn ngủ cấp tính.
- **MAR (Mouth Aspect Ratio)**: Ước lượng độ mở của miệng từ các landmark môi trên/dưới.
  - `MAR cao` thoáng qua $\rightarrow$ Nói chuyện/cười (bình thường).
  - `MAR cao` kéo dài (2–4s) $\rightarrow$ Ngáp (Yawning).

---

## 3. Head Pose & Hiệu Chuẩn Tư Thế Chuẩn (Neutral Pose Calibration)

### 3.1 Vấn đề lệch góc gắn camera
Trong ô tô thực tế, camera thường gắn lệch trục (cột A, taplo bên trái hoặc gương chiếu hậu), khiến $yaw, pitch$ có độ lệch tĩnh $\Delta yaw, \Delta pitch \ne 0^\circ$ ngay cả khi tài xế nhìn thẳng.

### 3.2 Thuật toán Neutral Pose Calibration
Khi bắt đầu phiên lái (Session Start):
1. Thu thập dữ liệu góc đầu trong cửa sổ **3–5 giây đầu tiên**.
2. Tính giá trị **Median** (Trung vị) của cửa sổ để loại trừ ngoại lai (outliers do tài xế chớp đầu hoặc camera vừa khởi động):
   $$\text{yaw}_0 = \text{median}(\{\text{yaw}_t\}), \quad \text{pitch}_0 = \text{median}(\{\text{pitch}_t\})$$
3. Trong suốt hành trình, mọi phép tính đều dựa trên góc tương đối:
   $$\text{relative\_yaw} = \text{yaw} - \text{yaw}_0$$
   $$\text{relative\_pitch} = \text{pitch} - \text{pitch}_0$$
4. Đánh giá mất tập trung:
   - $|\text{relative\_yaw}| > \text{threshold}_{yaw}$ kéo dài $\rightarrow$ `LOOKING_AWAY`
   - $\text{relative\_pitch} > \text{threshold}_{pitch}$ kéo dài $\rightarrow$ `LOOKING_DOWN`

---

## 4. Phone Detection: Phân Biệt PHONE_VISIBLE vs PHONE_USAGE

Để tránh báo sai khi điện thoại được gắn cố định trên giá đỡ taplo (làm bản đồ/GPS), hệ thống phân tách:

```text
YOLO detects phone (3–5 FPS)
        │
        ▼
   phone bbox
        │
        ├── Nằm trong / giao cắt Hand ROI?
        ├── Gần Face / Torso ROI của tài xế?
        └── Tồn tại liên tục > threshold thời gian?
                │
                ├─► Đạt điều kiện: PHONE_USAGE (Sự kiện nguy hiểm)
                └─► Không đạt: PHONE_VISIBLE (Chỉ ghi nhận trạng thái)
```

---

## 5. Temporal Engine & State Machine (FSM)

Để loại bỏ hoàn toàn cảnh báo giả đơn khung hình và chống spam chuông:

```text
IDLE (Bình thường)
  │
  ▼ Tín hiệu xuất hiện (EAR thấp, lệch đầu, phone)
CANDIDATE (Theo dõi thời gian duy trì)
  │
  ▼ Tồn tại đủ duration (ví dụ: > 1.8s)
ACTIVE (Kích hoạt Event & Alert)
  │
  ▼ Tín hiệu biến mất
COOLDOWN (Thời gian hạ nhiệt tối thiểu 3s, giữ alert không nhấp nháy)
  │
  ▼ Hết cooldown
IDLE
```

---

## 6. Dual Risk Engine: Acute vs Chronic Risk & Hàm Suy Hao (Decay)

Hệ thống phân tách rủi ro thành hai luồng độc lập:

```text
                     RISK ENGINE
            ┌─────────────┴─────────────┐
            ▼                           ▼
       ACUTE RISK                  CHRONIC RISK
    (Nguy cơ cấp tính)          (Mệt mỏi tích lũy)
  • Eyes closed > 1.8s        • PERCLOS tăng cao
  • Phone usage kéo dài       • Ngáp nhiều lần (lặp lại)
  • Looking away quá lâu      • Mất tập trung tái diễn
            │                           │
            ▼                           ▼
     Immediate Alert              Fatigue Score
   (DANGER ngay lập tức)      (Khuyến nghị nghỉ ngơi)
```

### 6.1 Cơ chế Acute Bypass
Nếu phát hiện dấu hiệu cấp tính (ví dụ `eyes_closed` liên tục đạt 2.0s), hệ thống lập tức nâng mức rủi ro lên **DANGER** và kích hoạt cảnh báo khẩn cấp, **không cần chờ phép cộng dồn tuyến tính đạt ngưỡng**.

### 6.2 Cơ chế Suy Hao (Exponential Decay)
Khi tài xế kết thúc hành vi nguy hiểm (ví dụ vừa mở mắt ra), điểm rủi ro không rớt thẳng về 0 mà suy giảm dần theo hàm mũ:
$$\text{Risk}_t = \max\left(\text{InstantRisk}_t, \; \text{Risk}_{t-1} \times e^{-\lambda \Delta t}\right)$$
Ví dụ thực tế:
$$\text{Risk} = 80 \longrightarrow 72 \longrightarrow 64 \longrightarrow 55 \longrightarrow \dots \longrightarrow 0$$
Cơ chế này ngăn chặn hiện tượng nhấp nháy cảnh báo (State Fluttering) và giúp tài xế giữ được sự tập trung sau khi vừa có cảnh báo.

---

## 7. Output Telemetry Schema

Định dạng bản tin dữ liệu từ AI Pipeline đưa vào IPC Queue:

```json
{
  "timestamp": "2026-10-04T17:30:00+07:00",
  "face_detected": true,
  "ear": 0.23,
  "mar": 0.31,
  "yaw": 12.4,
  "pitch": -3.2,
  "roll": 1.1,
  "relative_yaw": 4.2,
  "relative_pitch": -1.3,
  "signals": {
    "eyes_closed": false,
    "yawning": false,
    "looking_away": false,
    "phone_detected": false,
    "phone_usage": false
  },
  "durations": {
    "eyes_closed": 0.0,
    "looking_away": 0.0,
    "phone_usage": 0.0
  },
  "risk_score": 18,
  "risk_level": "NORMAL",
  "acute_active": false,
  "chronic_fatigue_score": 12,
  "fps": {
    "camera": 30,
    "face": 29,
    "phone": 5
  },
  "latency_ms": {
    "face": 12,
    "phone": 43
  },
  "reasons": []
}
```
