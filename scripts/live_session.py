# Phiên thử có hướng dẫn với camera thật: trang đếm giờ + ghi telemetry (chỉ số, KHÔNG ghi hình).
# Chạy: python scripts/live_session.py  (backend phải đang chạy camera thật ở cổng 8000)
# Mở http://localhost:8765/ , bấm "Bắt đầu", làm theo hướng dẫn. Kết quả: docs/experiments/live_session.json
import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import websockets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "experiments" / "live_session.json"
PORT = 8777

# (mã, hướng dẫn tiếng Việt, số giây)
STEPS = [
    ("baseline", "Ngồi tự nhiên, nhìn thẳng màn hình", 10),
    ("blink", "Chớp mắt bình thường", 8),
    ("eyes_closed", "NHẮM MẮT lại (giữ nhắm)", 4),
    ("rest1", "Mở mắt, nghỉ", 4),
    ("look_left", "Quay đầu sang TRÁI (nhìn ra cửa sổ trái)", 4),
    ("rest2", "Nhìn thẳng lại", 3),
    ("look_right", "Quay đầu sang PHẢI", 4),
    ("rest3", "Nhìn thẳng lại", 3),
    ("look_down", "CÚI ĐẦU nhìn xuống (như nhìn vào lòng)", 4),
    ("rest4", "Ngẩng lên, nhìn thẳng", 4),
    ("yawn", "Há miệng to như NGÁP (giữ há)", 4),
    ("rest5", "Khép miệng, nghỉ", 3),
    ("talk", "NÓI CHUYỆN: đếm to từ 1 đến 15", 8),
    ("smile", "CƯỜI thật to / cười nói", 5),
    ("rest6", "Nhìn thẳng lại", 3),
    ("phone", "Cầm ĐIỆN THOẠI trước ngực, gần mặt (nếu có)", 6),
    ("end", "Xong! Cảm ơn sếp", 1),
]

marks: list[dict] = []
frames: list[dict] = []
done = threading.Event()

PAGE = """<!doctype html><html lang="vi"><meta charset="utf-8"><title>Phiên thử DriverGuard</title>
<style>body{font:16px system-ui,sans-serif;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#121314;color:#ececea}
main{text-align:center;padding:24px;max-width:800px}h1{font-size:56px;margin:12px 0}#t{font-size:96px;font-weight:600}
button{font-size:24px;padding:18px 40px;border:0;border-radius:8px;background:#6b93ff;color:#fff;cursor:pointer}small{color:#a3a39d}</style>
<main><small id="n">Phiên thử có hướng dẫn (~100 giây). Chỉ ghi chỉ số, không ghi hình.</small>
<h1 id="s">Sẵn sàng?</h1><div id="t"></div><br><button id="b">Bắt đầu</button></main>
<script>
const STEPS=__STEPS__;
const s=document.getElementById('s'),t=document.getElementById('t'),b=document.getElementById('b'),n=document.getElementById('n');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
b.onclick=async()=>{b.style.display='none';
 for(let c=3;c>0;c--){s.textContent='Chuẩn bị…';t.textContent=c;await sleep(1000)}
 for(const [id,text,sec] of STEPS){
  await fetch('/mark?phase='+id);s.textContent=text;
  if(id==='end'){t.textContent='';break}
  for(let r=sec;r>0;r--){t.textContent=r;await sleep(1000)}
 }
 await fetch('/done');n.textContent='Đã ghi xong. Sếp có thể đóng trang.'};
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
            body = PAGE.replace("__STEPS__", json.dumps(STEPS, ensure_ascii=False)).encode("utf-8")
            self._send(body, "text/html; charset=utf-8")

    def _send(self, body: bytes, ctype="text/plain"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def collect():
    keep = ("face_detected", "calibrated", "ear", "mar", "yaw", "pitch", "relative_yaw", "relative_pitch", "eyes_closed",
            "yawning", "looking_away", "looking_down", "phone_detected", "phone_usage", "risk_score", "risk_level")
    async with websockets.connect("ws://localhost:8000/ws/status") as ws:
        while not done.is_set():
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), 1.0))
            except asyncio.TimeoutError:
                continue
            row = {k: m.get(k) for k in keep}
            row["t"] = time.time()
            row["events"] = [e["event_type"] for e in m.get("events", [])]
            row["fps"] = m.get("fps")
            row["latency_ms"] = m.get("latency_ms")
            frames.append(row)


def main():
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Mở http://localhost:{PORT}/ và bấm Bắt đầu", flush=True)
    asyncio.run(collect())
    OUT.write_text(json.dumps({"steps": STEPS, "marks": marks, "frames": frames}, ensure_ascii=False), encoding="utf-8")
    print("đã ghi", len(frames), "bản tin ->", OUT, flush=True)
    srv.shutdown()


if __name__ == "__main__":
    main()

