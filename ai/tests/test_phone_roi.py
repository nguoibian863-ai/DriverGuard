from ai.perception.phone_detector import is_usage_region

FACE = (300, 100, 400, 220)  # rộng 100, cao 120


def test_phone_near_chest_is_usage():
    assert is_usage_region((330, 300, 380, 380), FACE)


def test_phone_far_on_dashboard_not_usage():
    assert not is_usage_region((20, 400, 70, 470), FACE)


def test_no_face_not_usage():
    assert not is_usage_region((330, 300, 380, 380), None)


def test_face_box_hold_keeps_box_briefly():
    from ai.perception.phone_detector import FaceBoxHold

    hold = FaceBoxHold(hold_s=2.0)
    assert hold.update(0.0, FACE) == FACE
    assert hold.update(1.5, None) == FACE      # tay che mặt: vẫn dùng hộp cũ
    assert hold.update(2.5, None) is None      # quá 2 giây thì bỏ


def test_default_conf_theo_bien_moi_truong(monkeypatch):
    from ai.perception.phone_detector import DEFAULT_CONF, default_conf

    monkeypatch.delenv("DRIVERGUARD_YOLO_CONF", raising=False)
    assert default_conf() == DEFAULT_CONF
    monkeypatch.setenv("DRIVERGUARD_YOLO_CONF", "0.10")
    assert default_conf() == 0.10
    for bad in ("abc", "0", "1.5"):
        monkeypatch.setenv("DRIVERGUARD_YOLO_CONF", bad)
        assert default_conf() == DEFAULT_CONF
