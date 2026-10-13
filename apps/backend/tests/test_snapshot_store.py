import os

from app.services.snapshot_store import SnapshotStore, snapshots_enabled

JPEG = b"\xff\xd8\xff" + b"x" * 200


def test_luu_va_tra_duong_dan(tmp_path):
    store = SnapshotStore(tmp_path)
    path = store.save("abc", JPEG, "2026-10-05T08:00:00+00:00")
    assert path and os.path.isfile(path)
    assert open(path, "rb").read() == JPEG
    # tên tệp không chứa ký tự cấm trên Windows và sắp được theo thời gian
    name = os.path.basename(path)
    assert ":" not in name and "abc" in name and name.startswith("2026-10-05T08-00-00")


def test_khong_luu_khi_khong_co_khung_hinh(tmp_path):
    store = SnapshotStore(tmp_path)
    assert store.save("abc", None) is None
    assert store.save("abc", b"") is None
    assert list(tmp_path.iterdir()) == []


def test_fifo_theo_so_luong(tmp_path):
    store = SnapshotStore(tmp_path, max_files=3)
    for i in range(6):
        store.save(f"e{i}", JPEG, f"2026-10-05T08:00:0{i}+00:00")
    remaining = sorted(p.name for p in tmp_path.iterdir())
    assert len(remaining) == 3
    # giữ 3 ảnh mới nhất, xóa ảnh cũ nhất
    assert all(f"e{i}" not in " ".join(remaining) for i in (0, 1, 2))
    assert all(any(f"e{i}" in name for name in remaining) for i in (3, 4, 5))


def test_fifo_theo_dung_luong(tmp_path):
    big = b"\xff\xd8\xff" + b"y" * 1000
    store = SnapshotStore(tmp_path, max_files=500, max_bytes=2500)
    for i in range(5):
        store.save(f"e{i}", big, f"2026-10-05T08:00:0{i}+00:00")
    files = list(tmp_path.iterdir())
    assert sum(p.stat().st_size for p in files) <= 2500
    assert len(files) == 2


def test_thu_muc_khong_ghi_duoc_thi_tra_none(tmp_path):
    store = SnapshotStore(tmp_path / "ten_file_chan_duong")
    (tmp_path / "ten_file_chan_duong").write_text("đây là tệp, không phải thư mục")
    assert store.save("abc", JPEG, "2026-10-05T08:00:00+00:00") is None


def test_co_the_tat_bang_bien_moi_truong(monkeypatch):
    monkeypatch.delenv("DRIVERGUARD_SNAPSHOTS", raising=False)
    assert snapshots_enabled() is True
    monkeypatch.setenv("DRIVERGUARD_SNAPSHOTS", "0")
    assert snapshots_enabled() is False
