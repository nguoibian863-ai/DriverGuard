# Tải mẫu State Farm (150 ảnh/lớp, seed 0) từ gymprathap/Driver-Distracted-Dataset qua HTTP range. Xem docs/EXPERIMENT_LOG.md.
import io, os, random, struct, zipfile, zlib, requests
from concurrent.futures import ThreadPoolExecutor

URL = "https://huggingface.co/datasets/gymprathap/Driver-Distracted-Dataset/resolve/main/Distracted-Driver-Detection-Dataset.zip"
PER_CLASS, SEED = 150, 0

class RangeFile(io.RawIOBase):
    def __init__(self, url):
        h = requests.head(url, allow_redirects=True, timeout=60)
        self.url, self.size, self.pos = h.url, int(h.headers["content-length"]), 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0: return b""
        r = requests.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos+n-1}"}, timeout=120)
        r.raise_for_status(); self.pos += len(r.content); return r.content
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

rf = RangeFile(URL)
z = zipfile.ZipFile(io.BufferedReader(rf, 1 << 20))
infos = [i for i in z.infolist() if i.filename.startswith("imgs/train/c") and not i.is_dir()]
random.seed(SEED)
by_class = {}
for i in infos: by_class.setdefault(i.filename.split("/")[2], []).append(i)
picked = []
for c in sorted(by_class): picked += random.sample(by_class[c], PER_CLASS)
print("chọn", len(picked), "ảnh", flush=True)

def fetch(info):
    out = os.path.join("cache", info.filename.split("/")[2], os.path.basename(info.filename))
    if os.path.exists(out): return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    start = info.header_offset
    span = 30 + len(info.filename.encode()) + 300 + info.compress_size
    for attempt in range(4):
        try:
            r = requests.get(rf.url, headers={"Range": f"bytes={start}-{start+span-1}"}, timeout=120); r.raise_for_status(); b = r.content
            n, e = struct.unpack("<HH", b[26:30]); data = b[30+n+e:30+n+e+info.compress_size]
            raw = data if info.compress_type == 0 else zlib.decompressobj(-15).decompress(data)
            open(out, "wb").write(raw); return out
        except Exception as ex:
            err = ex
    raise err

with ThreadPoolExecutor(12) as ex:
    done = 0
    for _ in ex.map(fetch, picked):
        done += 1
        if done % 300 == 0: print(done, flush=True)
print("xong", done, flush=True)
