# Hướng dẫn triển khai Orchestrator: Claude CLI điều phối Gemini CLI (v2)

> Tài liệu tổng quát — áp dụng cho bất kỳ dự án nào, không khóa cứng vào một stack cụ thể.
> Ví dụ minh họa trong tài liệu (Next.js, MongoDB...) chỉ để làm rõ cách dùng — hãy thay bằng stack thật của dự án khi áp dụng.
> **v2** bổ sung: State Management, Context Compression, Retriever Agent, Gemini prompt chặt hơn, script automation đầy đủ, Knowledge Base riêng.

---

## 1. Mục tiêu & Kiến trúc tổng quan

Xây dựng một quy trình phát triển phần mềm có AI trong đó:

- **Claude CLI** đóng vai trò *kiến trúc sư + người điều phối + người review* — không viết code sản xuất.
- **Gemini CLI** đóng vai trò *người thực thi* — sinh code theo đúng bản thiết kế và constraints do Claude đưa ra.
- Mọi code sinh ra đều phải qua **kiểm tra tự động (lint/test)** rồi mới đến **review bằng AI**, và không được duyệt nếu còn lỗi mức CRITICAL.
- Mỗi task có **state riêng, theo dõi được**, không phụ thuộc vào việc Claude "nhớ" trong hội thoại.

Mỗi agent trong hệ thống này được định nghĩa theo ba thành phần, không chỉ là một đoạn prompt:

```
Agent = Role (prompt định nghĩa vai trò)
      + State (task đang ở đâu, đã thử bao nhiêu lần — state/)
      + Knowledge (nguồn tri thức agent được phép đọc — memory/ + docs/)
```

Việc tách riêng ba phần này là điểm khác biệt chính so với một hệ thống chỉ gồm các file prompt tĩnh.

```
Người dùng
    │
    ▼
Claude CLI (Orchestrator) ── đọc/ghi state/ mỗi bước
    │
    ├── Retriever         → đọc docs/API/RFC, tóm tắt
    ├── Architect          → thiết kế hệ thống
    ├── Planner            → chia nhỏ task
    ├── Reviewer           → review chất lượng code
    ├── Security Auditor   → review bảo mật
    ├── QA                 → review test coverage
    │
    ▼
Gọi Gemini CLI qua PowerShell (script wrapper)
    │
    ▼
Gemini sinh code → ghi ra file
    │
    ▼
Lint / Build / Test tự động (script)
    │
    ▼
Reviewer + Security + QA (Claude) chấm điểm
    │
    ├── Còn CRITICAL/HIGH → sinh fix-prompt → quay lại Gemini (tối đa N vòng, theo dõi qua state/)
    └── Đạt yêu cầu → Approve → cập nhật memory/ + state/
```

**Nguyên tắc cốt lõi:** Claude không code chính — Claude thiết kế, điều phối và gác cổng chất lượng; Gemini code; mọi thay đổi kiến trúc/quyết định kỹ thuật đều được ghi lại vào `memory/`; mọi tiến trình task đều được ghi lại vào `state/`.

---

## 2. Yêu cầu môi trường

- **Claude CLI** đã cài đặt và đăng nhập, chạy trong thư mục gốc của dự án.
- **Gemini CLI** đã cài đặt, có thể gọi bằng lệnh `gemini` trong PowerShell (kiểm tra bằng `gemini --version`).
- **PowerShell 7+** khuyến nghị (dùng `pwsh`, hỗ trợ UTF-8/JSON tốt hơn `powershell.exe` 5.1).
- Dự án có sẵn: trình quản lý gói (npm/pnpm/pip/...), linter, test runner — vì bước "kiểm tra tự động" phụ thuộc vào các công cụ này.

> ⚠️ Gemini là một hệ thống AI bên ngoài — output cần được coi là **chưa đáng tin cậy hoàn toàn** cho đến khi qua lint/test/review. Không merge trực tiếp.

---

## 3. Cấu trúc thư mục

```
<PROJECT_ROOT>
│
├── .claude/                     # cấu hình Claude CLI (nếu có)
│
├── agents/
│   ├── retriever.md             # MỚI — đọc & tóm tắt tri thức trước khi thiết kế
│   ├── architect.md
│   ├── planner.md
│   ├── reviewer.md
│   ├── security.md
│   └── qa.md
│
├── skills/
│   ├── <tech>-architecture/
│   │   ├── SKILL.md
│   │   ├── rules.md
│   │   ├── checklist.md
│   │   └── anti-patterns.md
│   ├── <db>-patterns/
│   │   ├── SKILL.md
│   │   ├── rules.md
│   │   └── anti-patterns.md
│   ├── security-audit/
│   │   ├── SKILL.md
│   │   └── checklist.md
│   └── code-review/
│       └── SKILL.md
│
├── commands/
│   ├── feature.md
│   ├── review.md
│   ├── fix.md
│   └── orchestrator.md
│
├── scripts/
│   ├── run-gemini.ps1           # gọi Gemini CLI
│   ├── run-checks.ps1           # lint + build + test tự động
│   ├── run-review.ps1           # MỚI — chạy 3 agent review, gộp báo cáo
│   └── update-state.ps1         # MỚI — cập nhật state/task-state.json an toàn
│
├── state/                       # MỚI — trạng thái từng task, không phụ thuộc trí nhớ hội thoại
│   ├── task-state.json
│   └── workflow-state.json
│
├── memory/
│   ├── summary.md                # MỚI — bản tóm tắt nén, đọc trước, xem Mục 8
│   ├── architecture.md
│   ├── roadmap.md
│   ├── decisions.md
│   ├── tech-stack.md
│   └── known-issues.md
│
├── docs/                         # MỚI — Knowledge Base dùng chung cho Claude & Gemini
│   ├── business-rules.md
│   ├── api-contracts.md
│   └── architecture-rules.md
│
├── reviews/                      # log các lần review (theo task)
├── tasks/                        # prompt + kết quả gửi Gemini theo từng task
└── src/
```

---

## 4. AGENTS

Mỗi agent dưới đây có: **Role** (file `.md`), **State** (đọc/ghi qua `state/task-state.json`), **Knowledge** (được phép đọc những file nào trong `memory/` và `docs/`). Phần "Được đọc" trong mỗi agent quy định rõ để tránh agent tự ý đọc lan man, tốn context.

### agents/retriever.md *(mới)*

```markdown
Bạn là Retriever — người thu thập và tóm tắt tri thức.

Được đọc: docs/*, README dự án, tài liệu API bên thứ ba (nếu người dùng cung cấp link/file),
memory/summary.md.

Trách nhiệm:
- Trước khi Architect thiết kế, đọc các tài liệu liên quan đến task
  (business rules, API contract, RFC nội bộ, tài liệu thư viện ngoài)
- Tóm tắt thành các điểm liên quan trực tiếp đến task hiện tại — không tóm tắt lan man
- Gắn cờ nếu phát hiện mâu thuẫn giữa tài liệu và memory/architecture.md hiện tại

Quy tắc:
- Không tự suy diễn khi tài liệu không rõ — liệt kê là "chưa rõ, cần hỏi người dùng"
- Không thiết kế, không đề xuất giải pháp — chỉ tổng hợp thông tin

Output:
# Tóm tắt tri thức cho task <task-id>
## Business rules liên quan
## API / contract liên quan
## Ràng buộc kỹ thuật phát hiện được
## Mâu thuẫn / điểm chưa rõ (nếu có)
```

Workflow cập nhật: **Retriever → Architect → Planner → Gemini** (Retriever chạy trước Architect, chỉ khi task có tài liệu bên ngoài liên quan; với task nhỏ, đơn giản có thể bỏ qua bước này).

### agents/architect.md

```markdown
Bạn là Chief Software Architect.

Được đọc: memory/summary.md, memory/architecture.md, docs/architecture-rules.md,
output của Retriever (nếu có).

Trách nhiệm:
- Thiết kế kiến trúc hệ thống
- Thiết kế database
- Thiết kế API contract
- Cấu trúc thư mục
- Lên kế hoạch khả năng mở rộng
- Ra quyết định kỹ thuật

Quy tắc:
- Thiết kế trước, code sau
- Phân tích yêu cầu trước khi thiết kế
- Chỉ ra rủi ro
- Chia thành các giai đoạn triển khai

Không bao giờ viết code sản xuất.

Output:
# Đề xuất kiến trúc
## Mục tiêu
## Ràng buộc
## Rủi ro
## Cấu trúc thư mục
## Thiết kế database
## Thiết kế API
## Các giai đoạn
## Tiêu chí nghiệm thu
```

### agents/planner.md

```markdown
Bạn là Technical Project Planner.

Được đọc: output của Architect, memory/roadmap.md.

Trách nhiệm:
- Chia feature thành các task nhỏ
- Xác định dependency giữa các task
- Xác định thứ tự thực hiện
- Khởi tạo entry mới trong state/task-state.json cho mỗi task (xem Mục 5)

Quy tắc:
- Mỗi task phải test độc lập được
- Task nên nhỏ, không gộp nhiều việc
- Tránh task khổng lồ

Output:
# Feature
## Task 1
Mục tiêu:
Phụ thuộc:
Tiêu chí nghiệm thu:
## Task 2
Mục tiêu:
Phụ thuộc:
Tiêu chí nghiệm thu:
```

### agents/reviewer.md

```markdown
Bạn là Principal Engineer, review toàn bộ code.

Được đọc: code vừa sinh (diff), docs/architecture-rules.md, skill code-review.

Kiểm tra:
- Tính đúng đắn
- Bảo mật
- Hiệu năng
- Khả năng mở rộng
- Khả năng bảo trì
- Tuân thủ kiến trúc
- Type safety
- Xử lý lỗi
- Test coverage

Thang mức độ nghiêm trọng (DÙNG CHUNG cho mọi agent review — xem Mục 4.4):
CRITICAL / HIGH / MEDIUM / LOW

Output:
# Báo cáo Review
## CRITICAL
## HIGH
## MEDIUM
## LOW
## Quyết định duyệt
```

### agents/security.md

```markdown
Bạn là Security Auditor.

Được đọc: code vừa sinh (diff), docs/business-rules.md (để biết dữ liệu nào nhạy cảm),
skill security-audit.

Review:
- Authentication
- Authorization
- Validation
- Quản lý secrets
- XSS / CSRF / SSRF
- OWASP Top 10

Thang mức độ nghiêm trọng: DÙNG CHUNG với reviewer — CRITICAL / HIGH / MEDIUM / LOW

Output:
# Báo cáo bảo mật
## CRITICAL
## HIGH
## MEDIUM
## LOW
Với mỗi mục ghi: Rủi ro / Tác động / Cách khắc phục
## Quyết định duyệt
```

### agents/qa.md

```markdown
Bạn là QA Engineer.

Được đọc: kết quả scripts/run-checks.ps1, tiêu chí nghiệm thu từ Planner.

Trách nhiệm:
- Kiểm tra test coverage của code vừa sinh
- Đánh giá test case có phủ đúng acceptance criteria không
- Phát hiện edge case còn thiếu (input rỗng, lỗi mạng, quyền truy cập sai, v.v.)
- Xác nhận kết quả lint/build/test có PASS không

Thang mức độ nghiêm trọng: DÙNG CHUNG — CRITICAL / HIGH / MEDIUM / LOW

Output:
# Báo cáo QA
## Kết quả lint/build/test tự động
## CRITICAL
## HIGH
## MEDIUM
## LOW
## Quyết định duyệt
```

### 4.4. Quy ước thang mức độ nghiêm trọng chung

Tất cả agent review (Reviewer, Security, QA) **bắt buộc dùng chung** thang `CRITICAL / HIGH / MEDIUM / LOW`, để Orchestrator gộp thành một báo cáo tổng hợp duy nhất.

- **CRITICAL**: lỗ hổng bảo mật khai thác được, mất dữ liệu, crash hệ thống, sai logic nghiệp vụ cốt lõi.
- **HIGH**: ảnh hưởng nghiêm trọng nhưng chưa gây sập hệ thống ngay.
- **MEDIUM**: vi phạm best practice, ảnh hưởng khả năng bảo trì/hiệu năng ở mức vừa phải.
- **LOW**: vấn đề nhỏ, style, tối ưu không bắt buộc.

**Không bao giờ approve nếu còn CRITICAL** (ở bất kỳ agent nào trong ba agent trên).

---

## 5. STATE MANAGEMENT *(mới)*

Đây là phần khắc phục vấn đề chính của bản v1: Claude không có nơi lưu trạng thái ổn định bên ngoài hội thoại, dễ "quên" task đang ở phase nào, đặc biệt khi phiên làm việc bị ngắt hoặc project chạy nhiều ngày.

### 5.1. `state/task-state.json`

Lưu trạng thái từng task riêng lẻ:

```json
{
  "tasks": {
    "AUTH-001": {
      "title": "Implement user login API",
      "status": "reviewing",
      "phase_history": ["designed", "planned", "implemented", "checked", "reviewing"],
      "fix_attempts": 2,
      "max_fix_attempts": 3,
      "last_review_summary": "reviews/AUTH-001-round2.md",
      "branch": "feature/AUTH-001",
      "updated_at": "2026-09-15T10:22:00+07:00"
    }
  }
}
```

Các giá trị `status` hợp lệ: `designed` → `planned` → `implementing` → `checked` (đã qua lint/build/test) → `reviewing` → `fixing` → `approved` | `blocked` (chạm giới hạn vòng lặp, cần người dùng can thiệp).

### 5.2. `state/workflow-state.json`

Lưu trạng thái tổng của cả feature (gồm nhiều task):

```json
{
  "feature": "Course Enrollment",
  "current_phase": "review-loop",
  "tasks": ["ENROLL-001", "ENROLL-002"],
  "blocked_tasks": [],
  "started_at": "2026-09-14T09:00:00+07:00"
}
```

### 5.3. Quy tắc bắt buộc

- **Trước mỗi bước** trong `commands/*.md`, Claude phải đọc `state/task-state.json` để biết task đang ở phase nào — không dựa vào việc "nhớ" trong hội thoại.
- **Sau mỗi bước**, Claude gọi `scripts/update-state.ps1` để ghi lại status mới — tránh việc Claude tự ghi đè JSON bằng tay (dễ lỗi format, dễ mất dữ liệu khi ghi song song).
- Nếu một phiên làm việc mới bắt đầu (`/orchestrator` được gọi lại), **bước đầu tiên luôn là đọc `state/`** để biết có task nào đang dang dở hay không, trước khi hỏi người dùng muốn làm gì.

### 5.4. `scripts/update-state.ps1`

```powershell
param(
    [Parameter(Mandatory=$true)][string]$TaskId,
    [Parameter(Mandatory=$true)][string]$Status,
    [int]$IncrementFixAttempts = 0
)

$ErrorActionPreference = "Stop"
$statePath = Join-Path $PSScriptRoot "..\state\task-state.json"

$state = if (Test-Path $statePath) {
    Get-Content $statePath -Raw | ConvertFrom-Json
} else {
    [PSCustomObject]@{ tasks = @{} }
}

if (-not $state.tasks.$TaskId) {
    $state.tasks | Add-Member -NotePropertyName $TaskId -NotePropertyValue ([PSCustomObject]@{
        status = $Status
        phase_history = @($Status)
        fix_attempts = 0
        max_fix_attempts = 3
        updated_at = (Get-Date).ToString("o")
    })
} else {
    $state.tasks.$TaskId.status = $Status
    $state.tasks.$TaskId.phase_history += $Status
    $state.tasks.$TaskId.fix_attempts += $IncrementFixAttempts
    $state.tasks.$TaskId.updated_at = (Get-Date).ToString("o")
}

$state | ConvertTo-Json -Depth 10 | Out-File -FilePath $statePath -Encoding UTF8
Write-Host "State cập nhật: $TaskId -> $Status"
```

> Ghi state qua script (thay vì Claude tự viết JSON) để tránh lỗi cú pháp và đảm bảo mỗi lần ghi đều có timestamp nhất quán.

---

## 6. CONTEXT COMPRESSION — `memory/summary.md` *(mới)*

Sau vài tháng, `architecture.md` và `decisions.md` có thể phình lên hàng nghìn dòng — nếu Claude đọc toàn bộ mỗi lần sẽ tốn context và dễ bỏ sót thông tin quan trọng ở giữa file dài.

Giải pháp: `memory/summary.md` là bản **nén**, luôn được đọc **đầu tiên** trước khi đọc các file chi tiết khác — chỉ đọc file chi tiết khi thực sự cần (ví dụ Architect cần xem toàn bộ lịch sử quyết định về database thì mới mở `decisions.md`).

```markdown
# Tóm tắt dự án (cập nhật lần cuối: <ngày>)

## Kiến trúc hiện tại (3-5 dòng)
<Framework> + <Database> + <Auth> + <AI service>. Theo mô hình <pattern chính, vd: feature-based, repository pattern>.

## Phase hiện tại
Phase <N>: <tên phase> — <trạng thái: đang làm / hoàn thành / blocked>

## Rủi ro đang mở (tối đa 5 dòng)
- <rủi ro 1>
- <rủi ro 2>

## Quyết định gần nhất quan trọng (tối đa 5 dòng, không phải toàn bộ lịch sử)
- <ngày> — <quyết định> (chi tiết đầy đủ xem decisions.md)
```

### Quy tắc cập nhật

- Mỗi khi `commands/feature.md` hoàn thành một feature (task đạt `approved`), Claude cập nhật lại `summary.md` — **ghi đè phần liên quan**, không append vô hạn.
- `summary.md` giới hạn khoảng 40-60 dòng. Nếu vượt, đó là dấu hiệu cần rút gọn hơn nữa, không phải viết dài thêm.
- File chi tiết (`architecture.md`, `decisions.md`, `roadmap.md`) vẫn giữ đầy đủ lịch sử — `summary.md` không thay thế chúng, chỉ là điểm vào nhanh.

---

## 7. KNOWLEDGE BASE — `docs/` *(mới)*

Nguồn tri thức dùng chung giữa Claude và Gemini, tách biệt với `memory/` (vốn là nhật ký quyết định/kiến trúc theo thời gian). `docs/` là tri thức **tĩnh, tham chiếu**, ít thay đổi:

- `docs/business-rules.md` — quy tắc nghiệp vụ (vd: "một user chỉ được đăng ký tối đa 5 khóa học cùng lúc").
- `docs/api-contracts.md` — hợp đồng API nội bộ/bên ngoài (request/response schema).
- `docs/architecture-rules.md` — các rule kiến trúc bắt buộc tuân thủ (tương tự nội dung `rules.md` trong skill, nhưng ở mức toàn dự án thay vì riêng từng công nghệ).

Retriever (Mục 4) là agent chính đọc và tóm tắt các file này khi cần cho một task cụ thể — các agent khác không tự ý đọc toàn bộ `docs/`, chỉ nhận phần liên quan do Retriever hoặc Orchestrator trích ra.

---

## 8. CƠ CHẾ GỌI GEMINI CLI TỪ CLAUDE CLI QUA POWERSHELL

### 8.1. Hợp đồng input/output (I/O contract)

- **Input**: `tasks/<task-id>/prompt.md`.
- **Output**: `tasks/<task-id>/output.md`, tách biệt hoàn toàn khỏi log console.
- **Exit code**: `0` = Gemini chạy xong (không đồng nghĩa code đúng); khác `0` = lỗi gọi CLI — Claude dừng lại, báo người dùng.

### 8.2. `scripts/run-gemini.ps1`

```powershell
param(
    [Parameter(Mandatory=$true)][string]$TaskId,
    [int]$TimeoutSec = 300
)

$ErrorActionPreference = "Stop"

$taskDir    = Join-Path $PSScriptRoot "..\tasks\$TaskId"
$promptPath = Join-Path $taskDir "prompt.md"
$outputPath = Join-Path $taskDir "output.md"
$logPath    = Join-Path $taskDir "gemini.log"

if (-not (Test-Path $promptPath)) {
    Write-Error "Không tìm thấy prompt: $promptPath"
    exit 1
}

$promptContent = Get-Content -Path $promptPath -Raw -Encoding UTF8

try {
    $result = $promptContent | gemini --yolo 2>&1
} catch {
    $_.Exception.Message | Out-File -FilePath $logPath -Encoding UTF8
    Write-Error "Gemini CLI lỗi khi chạy — xem $logPath"
    exit 1
}

$result | Out-File -FilePath $logPath -Encoding UTF8

$text = $result -join "`n"
if ($text -match "(?s)## OUTPUT_START(.*)## OUTPUT_END") {
    $matches[1].Trim() | Out-File -FilePath $outputPath -Encoding UTF8
} else {
    "> ⚠️ Không tìm thấy marker OUTPUT_START/OUTPUT_END — ghi log gốc.`n`n$text" |
        Out-File -FilePath $outputPath -Encoding UTF8
}

Write-Host "Xong. Kết quả tại: $outputPath"
```

> `--yolo` (hoặc cờ tương đương bỏ qua xác nhận thủ công) chỉ dùng trong môi trường đã cô lập (branch riêng) — không chạy trên nhánh chính không kiểm soát.

### 8.3. `scripts/run-checks.ps1`

```powershell
param([int]$TimeoutSec = 300)

Write-Host "== Lint =="
npm run lint

Write-Host "== Build =="
npm run build

Write-Host "== Test =="
npm test -- --ci
```

> Thay bằng lệnh tương ứng stack thật (pnpm, pytest, cargo test...). Fail bất kỳ bước nào → dừng loop, tạo fix-prompt ngay, không chuyển sang Reviewer.

### 8.4. `scripts/run-review.ps1` *(mới)*

Gộp cả ba báo cáo Reviewer/Security/QA thành một file duy nhất để Orchestrator không phải tự ráp tay:

```powershell
param([Parameter(Mandatory=$true)][string]$TaskId)

$taskDir = Join-Path $PSScriptRoot "..\tasks\$TaskId"
$reviewDir = Join-Path $PSScriptRoot "..\reviews"
New-Item -ItemType Directory -Force -Path $reviewDir | Out-Null

# Giả định Claude đã ghi 3 file riêng trước khi gọi script này:
# tasks/<id>/reviewer-output.md, security-output.md, qa-output.md
$reviewer = Get-Content (Join-Path $taskDir "reviewer-output.md") -Raw
$security = Get-Content (Join-Path $taskDir "security-output.md") -Raw
$qa       = Get-Content (Join-Path $taskDir "qa-output.md") -Raw

$merged = @"
# Báo cáo tổng hợp — $TaskId
## Từ Reviewer
$reviewer

## Từ Security Auditor
$security

## Từ QA
$qa
"@

$outPath = Join-Path $reviewDir "$TaskId-$(Get-Date -Format 'yyyyMMdd-HHmmss').md"
$merged | Out-File -FilePath $outPath -Encoding UTF8
Write-Host "Báo cáo tổng hợp: $outPath"
```

### 8.5. Cách Claude gọi các script này

Trong `commands/feature.md` / `commands/fix.md`:
1. Ghi prompt vào `tasks/<task-id>/prompt.md` theo template Mục 9.
2. Chạy `pwsh -File scripts/run-gemini.ps1 -TaskId <task-id>`.
3. Đọc `tasks/<task-id>/output.md`.
4. Chạy `pwsh -File scripts/run-checks.ps1`.
5. Nếu pass, chạy 3 agent review, ghi từng output ra `tasks/<task-id>/{reviewer,security,qa}-output.md`, sau đó gọi `scripts/run-review.ps1 -TaskId <task-id>`.
6. Gọi `scripts/update-state.ps1` sau mỗi bước quan trọng.
7. Nếu output rỗng hoặc chứa cảnh báo marker — dừng lại, báo người dùng, không tự đoán nội dung.

---

## 9. TEMPLATE PROMPT GỬI GEMINI (nâng cấp — chặt hơn)

So với v1, thêm 4 mục để giảm nguy cơ Gemini sửa nhầm phạm vi: **Existing Files** (file đã tồn tại, liên quan), **Relevant Code** (đoạn code liên quan trực tiếp, không phải cả file), **Do Not Modify** (danh sách file/thư mục cấm đụng vào), **Out Of Scope** (việc rõ ràng không thuộc task này, dù có vẻ liên quan).

```text
Yêu cầu Gemini trả lời đúng định dạng sau, bắt đầu bằng "## OUTPUT_START"
và kết thúc bằng "## OUTPUT_END". Không thêm text nào ngoài hai marker này.

Mục tiêu:
<mô tả task>

Kiến trúc liên quan (trích từ memory/summary.md — không gửi toàn bộ):
<phần liên quan>

Existing Files (file đã có, liên quan đến task):
<đường dẫn + mô tả ngắn>

Relevant Code (đoạn code liên quan trực tiếp, đã trích sẵn — không yêu cầu Gemini tự đọc toàn repo):
<snippet>

Do Not Modify:
<vd: src/auth/*, src/database/schema.ts>

Out Of Scope (không làm, dù có vẻ liên quan):
<vd: không refactor lại module payment trong task này>

Ràng buộc:
- Giữ nguyên kiến trúc hiện có
- Tuân thủ rules.md / anti-patterns.md của skill liên quan
- Bao gồm test cho các thay đổi

Tiêu chí nghiệm thu:
<danh sách acceptance criteria từ Planner>

## OUTPUT_START
1. Danh sách file thay đổi
2. Code
3. Giải thích
4. Rủi ro
## OUTPUT_END
```

> Chỉ trích phần kiến trúc **liên quan trực tiếp** đến task (từ `memory/summary.md`, không phải toàn bộ `architecture.md`) — giữ prompt gọn theo đúng tinh thần Context Compression ở Mục 6.

---

## 10. GIỚI HẠN VÒNG LẶP FIX

- Theo dõi qua `state/task-state.json` (`fix_attempts` / `max_fix_attempts`), không dùng file `state.json` rời rạc như bản v1 — gộp về một nguồn state duy nhất để tránh lệch dữ liệu.
- Mỗi lần chạy `commands/fix.md`: gọi `update-state.ps1 -TaskId <id> -Status fixing -IncrementFixAttempts 1`.
- Nếu `fix_attempts >= max_fix_attempts` mà vẫn còn CRITICAL/HIGH:
  - Dừng vòng lặp ngay, set `status = blocked`.
  - Ghi lịch sử review vào `reviews/<task-id>-summary.md`.
  - Báo người dùng: vấn đề còn tồn đọng, đề xuất hướng xử lý thủ công.

---

## 11. QUẢN LÝ MEMORY

- `memory/summary.md` — đọc **đầu tiên** mỗi phiên làm việc (xem Mục 6).
- `memory/architecture.md` — cập nhật khi có thay đổi kiến trúc thật.
- `memory/roadmap.md` — cập nhật khi thêm/hoàn thành phase.
- `memory/decisions.md` — mỗi quyết định kỹ thuật thật thêm một mục mới (Ngày / Quyết định / Lý do / Trạng thái), không xóa lịch sử cũ.
- `memory/tech-stack.md` — phản ánh đúng stack thật.
- `memory/known-issues.md` — vấn đề tồn đọng thật, có mức ưu tiên.

> ⚠️ Khi khởi tạo dự án, các file này nên để rỗng hoặc ghi "chưa có quyết định" thay vì để sẵn ví dụ minh họa — tránh Claude đọc nhầm thành ngữ cảnh thật.

---

## 12. GIT / KIỂM SOÁT PHIÊN BẢN

- Mỗi task chạy trên branch riêng (`feature/<task-id>`), lưu tên branch vào `state/task-state.json`.
- Commit message: `[gemini] <task-id>: <mô tả ngắn>`.
- Sau khi approve, tạo Pull Request hoặc merge thủ công — không tự động merge vào nhánh chính mà không có xác nhận người dùng.
- Nếu `status = blocked` (chạm giới hạn fix) → giữ nguyên branch, không merge.

---

## 13. COMMANDS

### commands/feature.md

```markdown
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
```

### commands/review.md

```markdown
Review implementation hiện tại.

0. Đọc state/task-state.json để biết task đang ở status nào
1. Sử dụng agent reviewer, security, qa, skill code-review
2. Gọi scripts/run-review.ps1 để gộp báo cáo
3. update-state.ps1 theo kết quả (reviewing / approved / blocked)

Không approve nếu còn CRITICAL.
```

### commands/fix.md

```markdown
Đọc kết quả review gần nhất (reviews/<task-id>-*.md) và state/task-state.json.

Nếu fix_attempts >= max_fix_attempts: DỪNG, báo người dùng, không gọi Gemini thêm.

Ngược lại, sinh fix-prompt cho Gemini gồm:
- Vấn đề
- Nguyên nhân gốc
- File liên quan
- Yêu cầu sửa cụ thể

Chỉ sửa đúng lỗi đã báo cáo. Không thiết kế lại kiến trúc.
update-state.ps1 -Status fixing -IncrementFixAttempts 1
```

### commands/orchestrator.md

```markdown
Bạn là Project Orchestrator.

Trách nhiệm:
- Điều phối các agent (Retriever, Architect, Planner, Reviewer, Security, QA)
- Đọc/ghi state/ ở mỗi bước — không dựa vào trí nhớ hội thoại
- Duy trì memory/summary.md gọn, cập nhật sau mỗi feature hoàn thành
- Giao việc triển khai cho Gemini qua scripts/run-gemini.ps1
- Quản lý vòng lặp fix (tối đa 3 vòng, theo dõi qua state/task-state.json)

Quy trình:
Bước 0: Đọc state/ — resume task dang dở nếu có
Bước 1: Retriever thu thập tri thức (nếu cần)
Bước 2: Architect thiết kế
Bước 3: Planner chia task
Bước 4: Sinh prompt cho Gemini
Bước 5: Gemini triển khai (scripts/run-gemini.ps1)
Bước 6: scripts/run-checks.ps1 (lint/build/test)
Bước 7: Reviewer + Security + QA review (scripts/run-review.ps1)
Bước 8: Sinh fix-prompt nếu cần
Bước 9: Gemini fix
Lặp lại bước 5–9 cho đến khi:
- Không còn CRITICAL
- Đạt tiêu chí nghiệm thu
- Kiến trúc không bị phá vỡ
- HOẶC chạm giới hạn vòng lặp → dừng, báo người dùng

Output cuối cùng:
# Tổng kết
## Task đã hoàn thành
## Kết quả review
## Rủi ro còn lại
## Nợ kỹ thuật
## Trạng thái duyệt
## Số vòng lặp đã dùng
```

---

## 14. SKILLS

Giữ cấu trúc tương tự bản v1: `SKILL.md` + `rules.md` + `checklist.md` + `anti-patterns.md` cho mỗi công nghệ. Nếu muốn Claude tự động trigger đúng skill, viết `description` trong frontmatter chi tiết (khi nào dùng, ví dụ cụ thể) — tương tự cách skill chính thức của Claude được mô tả, thay vì chỉ một dòng ngắn.

---

## 15. CÁCH SỬ DỤNG HẰNG NGÀY

```text
/orchestrator

Build a learning platform with:
- <framework>
- <database>
- <auth>
- <ai-service>
```

```text
/feature
Add course enrollment feature
```

```text
/review
```

```text
/fix
```

---

## 16. QUY TẮC QUAN TRỌNG NHẤT

1. Claude không code chính — Claude thiết kế và review.
2. Mỗi agent = Role + State + Knowledge, không chỉ là một prompt tĩnh.
3. Mọi bước đều đọc/ghi `state/task-state.json` trước và sau khi thực hiện — không dựa vào trí nhớ hội thoại.
4. Đọc `memory/summary.md` trước, chỉ mở file chi tiết khi thật sự cần (Context Compression).
5. Gemini code, gọi qua `scripts/run-gemini.ps1`; mọi code đều qua lint/build/test tự động trước khi review.
6. Prompt gửi Gemini luôn có `Do Not Modify` và `Out Of Scope` để giới hạn phạm vi sửa đổi.
7. Reviewer + Security + QA dùng chung thang CRITICAL/HIGH/MEDIUM/LOW, gộp báo cáo qua `run-review.ps1`.
8. Không approve nếu còn CRITICAL.
9. Vòng lặp fix giới hạn tối đa 3 lần, theo dõi qua state — vượt quá phải dừng và báo người dùng.
10. Mọi quyết định kỹ thuật thật phải ghi vào `memory/decisions.md`; mọi thay đổi kiến trúc phải cập nhật `memory/architecture.md` và `memory/summary.md`.
11. Không merge vào nhánh chính mà không qua Pull Request / xác nhận thủ công.
