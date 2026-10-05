from ai.perception.phone_detector import is_usage_region

FACE = (300, 100, 400, 220)  # rộng 100, cao 120


def test_phone_near_chest_is_usage():
    assert is_usage_region((330, 300, 380, 380), FACE)


def test_phone_far_on_dashboard_not_usage():
    assert not is_usage_region((20, 400, 70, 470), FACE)


def test_no_face_not_usage():
    assert not is_usage_region((330, 300, 380, 380), None)
