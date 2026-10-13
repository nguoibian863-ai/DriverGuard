"""Lưu ảnh chụp sự kiện kèm chính sách giới hạn dung lượng.

Theo `docs/design/07_API_AND_DATA_MODEL.md` mục 4: giữ tối đa 500 ảnh gần nhất
hoặc 1 GB, vượt thì xóa ảnh cũ nhất theo FIFO; metadata sự kiện trong SQLite giữ nguyên.
"""

import os
from pathlib import Path

MAX_FILES = 500
MAX_BYTES = 1024 * 1024 * 1024  # 1 GB
SUFFIX = ".jpg"


def snapshots_enabled() -> bool:
    return os.getenv("DRIVERGUARD_SNAPSHOTS", "1") != "0"


def snapshot_dir() -> Path:
    return Path(os.getenv("DRIVERGUARD_SNAPSHOT_DIR", "data/snapshots"))


class SnapshotStore:
    """Thư mục ảnh JPEG phẳng, tên theo thời điểm sự kiện nên sắp xếp được theo thời gian."""

    def __init__(self, directory: Path | str | None = None, max_files: int = MAX_FILES, max_bytes: int = MAX_BYTES) -> None:
        self.directory = Path(directory) if directory is not None else snapshot_dir()
        self.max_files = max_files
        self.max_bytes = max_bytes

    def save(self, event_id: str, jpeg: bytes | None, started_at: str | None = None) -> str | None:
        """Ghi ảnh cho sự kiện; trả về đường dẫn tương đối, hoặc None nếu không ghi được."""
        if not jpeg:
            return None
        # Tiền tố thời gian để sắp theo thứ tự; ký tự không hợp lệ trên Windows được thay bằng '-'
        prefix = "".join("-" if ch in ':+ ' else ch for ch in (started_at or ""))[:32]
        name = f"{prefix}_{event_id}{SUFFIX}" if prefix else f"{event_id}{SUFFIX}"
        path = self.directory / name
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path.write_bytes(jpeg)
        except OSError:
            return None
        self.prune()
        return str(path)

    def _files(self) -> list[Path]:
        """Ảnh đã lưu, cũ nhất trước (theo thời điểm sửa đổi, hòa thì theo tên)."""
        try:
            entries = [p for p in self.directory.iterdir() if p.is_file() and p.suffix == SUFFIX]
        except OSError:
            return []
        return sorted(entries, key=lambda p: (p.stat().st_mtime, p.name))

    def prune(self) -> int:
        """Xóa ảnh cũ nhất cho đến khi dưới cả hai ngưỡng. Trả về số ảnh đã xóa."""
        files = self._files()
        try:
            sizes = {p: p.stat().st_size for p in files}
        except OSError:
            return 0
        total = sum(sizes.values())
        removed = 0
        for path in files:
            if len(files) - removed <= self.max_files and total <= self.max_bytes:
                break
            try:
                path.unlink()
            except OSError:
                continue
            total -= sizes[path]
            removed += 1
        return removed
