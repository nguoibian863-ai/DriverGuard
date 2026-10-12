# Project Directory Structure

## 1. Cấu trúc đề xuất

```text
driverguard/
│
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│   ├── 00_PROJECT_OVERVIEW.md
│   ├── 01_ACTORS_AND_USER_REQUIREMENTS.md
│   ├── 02_TECH_STACK.md
│   ├── 03_PROJECT_STRUCTURE.md
│   ├── 04_SYSTEM_ARCHITECTURE.md
│   ├── 05_AI_CV_PIPELINE.md
│   ├── 06_REQUIREMENTS.md
│   ├── 07_API_AND_DATA_MODEL.md
│   ├── 08_TESTING_AND_EVALUATION.md
│   └── 09_ROADMAP.md
│
├── apps/
│   │
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   │
│   │   │   ├── api/
│   │   │   │   ├── routes_health.py
│   │   │   │   ├── routes_events.py
│   │   │   │   ├── routes_sessions.py
│   │   │   │   └── routes_config.py
│   │   │   │
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   └── logging.py
│   │   │   │
│   │   │   ├── schemas/
│   │   │   │   ├── event.py
│   │   │   │   ├── session.py
│   │   │   │   └── status.py
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── event_service.py
│   │   │   │   ├── session_service.py
│   │   │   │   └── websocket_service.py
│   │   │   │
│   │   │   └── db/
│   │   │       ├── database.py
│   │   │       └── models.py
│   │   │
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── web/
│       ├── app/
│       ├── components/
│       │   ├── camera/
│       │   ├── driver-status/
│       │   ├── risk-meter/
│       │   ├── event-list/
│       │   └── charts/
│       ├── lib/
│       ├── types/
│       ├── public/
│       ├── package.json
│       └── tsconfig.json
│
├── ai/
│   ├── config/
│   │   ├── thresholds.yaml
│   │   └── models.yaml
│   │
│   ├── capture/
│   │   ├── camera.py
│   │   └── video_reader.py
│   │
│   ├── perception/
│   │   ├── face_landmarks.py
│   │   ├── eye_state.py
│   │   ├── mouth_state.py
│   │   ├── head_pose.py
│   │   └── phone_detector.py
│   │
│   ├── features/
│   │   ├── ear.py
│   │   ├── mar.py
│   │   └── pose_features.py
│   │
│   ├── temporal/
│   │   ├── buffers.py
│   │   ├── drowsiness.py
│   │   ├── distraction.py
│   │   └── phone_usage.py
│   │
│   ├── risk/
│   │   ├── engine.py
│   │   └── rules.py
│   │
│   ├── runtime/
│   │   ├── pipeline.py
│   │   ├── worker.py
│   │   └── metrics.py
│   │
│   └── tests/
│
├── models/
│   ├── README.md
│   ├── pytorch/
│   ├── onnx/
│   └── tensorrt/
│
├── data/
│   ├── README.md
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── samples/
│
├── scripts/
│   ├── run_camera.py
│   ├── evaluate.py
│   ├── export_onnx.py
│   └── benchmark.py
│
├── tests/
│   ├── integration/
│   └── e2e/
│
└── artifacts/
    ├── reports/
    ├── metrics/
    └── demo/
```

---

# 2. Nguyên tắc tổ chức

## apps/

Chứa application layer:

- Backend.
- Frontend.

Không đặt logic CV trực tiếp trong API route.

## ai/

Chứa toàn bộ AI/CV core.

AI pipeline phải có thể chạy độc lập với frontend.

## models/

Chứa model artifact, nhưng tránh commit model quá lớn trực tiếp vào Git.

## data/

Dùng để tổ chức data local.

Không commit dataset lớn hoặc dữ liệu nhạy cảm.

## scripts/

Chứa các entry point phục vụ:

- Benchmark.
- Export model.
- Evaluation.
- Demo.

## tests/

Chứa test xuyên module hoặc toàn hệ thống.

---

# 3. Dependency direction

Ưu tiên:

```text
Frontend
   ↓
Backend API
   ↓
Application Services
   ↓
AI Runtime
   ↓
Perception / Temporal / Risk
```

Không để:

```text
AI Core → Frontend
```

AI core phải độc lập UI.
