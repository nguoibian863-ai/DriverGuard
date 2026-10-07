# Phiên thử có hướng dẫn với camera thật: trang đếm giờ + ghi telemetry (chỉ số, KHÔNG ghi hình).
# Chạy: python scripts/live_session.py --out docs/experiments/live_session_2.json --label "EXP-006" (backend ở cổng 8000)
# Mở http://localhost:8777/ , bấm "Bắt đầu".
import argparse
import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import websockets

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "experiments" / "live_session.json"
PORT = 8777
CALIBRATE_URL = "http://localhost:8000/api/v1/sessions/calibrate"

# (mã, hướng dẫn tiếng Việt, số giây)
STEPS = [
    ("baseline", "Ngồi tự nhiên, nhìn thẳng màn hình", 10),
    ("blink", "Chớp mắt bình thường", 8),
    ("eyes_closed", "NHẮM MẮT lại (giữ nhắm) (giữ yên đến khi hết giờ)", 7),
    ("rest1", "Mở mắt, nghỉ", 3),
    ("look_left", "Quay đầu sang TRÁI (nhìn ra cửa sổ trái; giữ yên đến khi hết giờ)", 7),
    ("rest2", "Nhìn thẳng lại", 3),
    ("look_left", "Quay sang trái ĐẾN KHI nhìn thấy mép cửa sổ (giữ yên đến khi hết giờ)", 7),
    ("rest7", "Nhìn thẳng lại", 3),
    ("look_right", "Quay đầu sang PHẢI (giữ yên đến khi hết giờ)", 7),
    ("rest3", "Nhìn thẳng lại", 3),
    ("look_right", "Quay sang phải ĐẾN KHI nhìn thấy mép cửa sổ (giữ yên đến khi hết giờ)", 7),
    ("rest8", "Nhìn thẳng lại", 3),
    ("look_down", "CÚI ĐẦU nhìn xuống (như nhìn vào lòng; giữ yên đến khi hết giờ)", 7),
    ("rest4", "Ngẩng lên, nhìn thẳng", 3),
    ("yawn", "Há miệng to như NGÁP (giữ yên đến khi hết giờ)", 7),
    ("rest5", "Khép miệng, nghỉ", 3),
    ("talk", "NÓI CHUYỆN: đếm to từ 1 đến 15", 8),
    ("smile", "CƯỜI thật to / cười nói", 5),
    ("rest6", "Nhìn thẳng lại", 3),
    ("phone", "Cầm ĐIỆN THOẠI trước ngực, gần mặt (nếu có) (giữ yên đến khi hết giờ)", 7),
    ("rest9", "Hạ điện thoại xuống, nhìn thẳng và nghỉ", 3),
    ("phone_near_face", "Đưa điện thoại lên NGANG MẶT như đang nhắn tin, mắt nhìn vào điện thoại (giữ yên đến khi hết giờ)", 7),
    ("end", "Xong! Cảm ơn sếp", 1),
]
COUNTDOWN_SECONDS = 3
CALIBRATION_SECONDS = 4
SESSION_SECONDS = (
    sum(seconds for phase, _, seconds in STEPS if phase != "end")
    + COUNTDOWN_SECONDS
    + CALIBRATION_SECONDS
)

marks: list[dict] = []
frames: list[dict] = []
done = threading.Event()
calibrate_t: float | None = None
calibration_error: str | None = None

PAGE = """<!doctype html><html lang="vi"><meta charset="utf-8"><title>Phiên thử DriverGuard</title>
<style>body{font:16px system-ui,sans-serif;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#121314;color:#ececea}
main{text-align:center;padding:24px;max-width:800px}h1{font-size:56px;margin:12px 0}#t{font-size:96px;font-weight:600}
button{font-size:24px;padding:18px 40px;border:0;border-radius:8px;background:#6b93ff;color:#fff;cursor:pointer}small{color:#a3a39d}</style>
<main><small id="n">Phiên thử có hướng dẫn (~__SESSION_SECONDS__ giây). Chỉ ghi chỉ số, không ghi hình.</small>
<h1 id="s">Sẵn sàng?</h1><div id="t"></div><br><button id="b">Bắt đầu</button></main>
<script>
const STEPS=__STEPS__;
const s=document.getElementById('s'),t=document.getElementById('t'),b=document.getElementById('b'),n=document.getElementById('n');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
b.onclick=async()=>{b.style.display='none';
 for(let c=__COUNTDOWN_SECONDS__;c>0;c--){s.textContent='Chuẩn bị…';t.textContent=c;await sleep(1000)}
 try{
  const response=await fetch('/calibrate',{method:'POST'});
  if(!response.ok)throw new Error(await response.text());
  for(let r=__CALIBRATION_SECONDS__;r>0;r--){s.textContent='Hiệu chuẩn: Ngồi thẳng, nhìn thẳng';t.textContent=r;await sleep(1000)}
  for(const [id,text,sec] of STEPS){
   await fetch('/mark?phase='+encodeURIComponent(id));s.textContent=text;
   if(id==='end'){t.textContent='';break}
   for(let r=sec;r>0;r--){t.textContent=r;await sleep(1000)}
  }
  await fetch('/done');n.textContent='Đã ghi xong. Sếp có thể đóng trang.'
 }catch(error){
  s.textContent='Không thể hiệu chuẩn hoặc ghi phiên thử';t.textContent='';n.textContent=String(error);
  await fetch('/done');
 }
};
</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/mark":
            marks.append({"phase": parse_qs(u.query)["phase"][0], "t": time.time()})
            self._send(b"ok")
        elif u.path == "/done":
            done.set()
            self._send(b"ok")
        else:
            page = PAGE.replace("__STEPS__", json.dumps(STEPS, ensure_ascii=False))
            page = page.replace("__SESSION_SECONDS__", str(SESSION_SECONDS))
            page = page.replace("__COUNTDOWN_SECONDS__", str(COUNTDOWN_SECONDS))
            page = page.replace("__CALIBRATION_SECONDS__", str(CALIBRATION_SECONDS))
            body = page.encode("utf-8")
            self._send(body, "text/html; charset=utf-8")

    def do_POST(self):
        global calibrate_t, calibration_error
        if urlparse(self.path).path != "/calibrate":
            self._send(b"not found", status=404)
            return

        request = Request(CALIBRATE_URL, data=b"", method="POST")
        try:
            with urlopen(request, timeout=5) as response:
                response.read()
            calibrate_t = time.time()
        except (URLError, TimeoutError, OSError) as exc:
            calibration_error = str(exc)
            done.set()
            self._send(json.dumps({"error": calibration_error}).encode("utf-8"), "application/json", 502)
            return

        self._send(json.dumps({"calibrate_t": calibrate_t}).encode("utf-8"), "application/json")

    def _send(self, body: bytes, ctype="text/plain", status=200):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def collect():
    keep = (
        "face_detected", "calibrated", "ear", "mar", "yaw", "pitch", "relative_yaw", "relative_pitch",
        "eyes_closed", "yawning", "looking_away", "looking_down", "phone_detected", "phone_usage",
        "risk_score", "risk_level",
    )
    async with websockets.connect("ws://localhost:8000/ws/status") as ws:
        while not done.is_set():
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), 1.0))
            except asyncio.TimeoutError:
                continue
            row = {k: m[k] for k in keep if k in m}
            # Lưu ROI/hộp/vùng điện thoại nếu backend có phát ra; không suy diễn dữ liệu còn thiếu.
            for key, value in m.items():
                normalized = key.casefold().replace("-", "_")
                if "phone" in normalized and any(part in normalized for part in ("roi", "bbox", "box", "region")):
                    row[key] = value
            row["t"] = time.time()
            row["events"] = [e["event_type"] if isinstance(e, dict) else e for e in m.get("events", [])]
            for key in ("fps", "latency_ms"):
                if key in m:
                    row[key] = m[key]
            if "pose" in m:
                row["pose"] = m["pose"]
            frames.append(row)


def parse_args():
    parser = argparse.ArgumentParser(description="Ghi telemetry cho phiên thử người thật DriverGuard.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Tệp JSON đầu ra (mặc định: docs/experiments/live_session.json).")
    parser.add_argument("--label", help="Nhãn phiên thử được ghi vào JSON.")
    parser.add_argument("--force", action="store_true", help="Cho phép ghi đè tệp đích đã tồn tại.")
    return parser.parse_args()


def main():
    args = parse_args()
    target = args.out if args.out.is_absolute() else ROOT / args.out
    target = target.resolve()
    if target.exists() and not args.force:
        raise SystemExit(f"Tệp đích đã tồn tại; không ghi đè: {target} (dùng --force nếu cần)")

    target.parent.mkdir(parents=True, exist_ok=True)
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Mở http://localhost:{PORT}/ và bấm Bắt đầu", flush=True)
    try:
        asyncio.run(collect())
        if calibrate_t is None:
            raise RuntimeError(f"Không hiệu chuẩn được; không ghi phiên thử. {calibration_error or ''}")
        result = {
            "label": args.label,
            "calibrate_t": calibrate_t,
            "steps": STEPS,
            "marks": marks,
            "frames": frames,
        }
        mode = "w" if args.force else "x"
        with target.open(mode, encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False)
        print("Đã ghi", len(frames), "bản tin ->", target, flush=True)
    finally:
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    main()
