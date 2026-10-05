from ai.temporal.drowsiness import AlertState, DurationFSM


def test_full_flow():
    """Kiểm tra luồng đầy đủ: IDLE -> CANDIDATE -> ACTIVE -> COOLDOWN -> IDLE."""
    fsm = DurationFSM(duration_s=1.8, cooldown_s=3.0)
    assert fsm.state == AlertState.IDLE

    # IDLE với signal=False vẫn ở IDLE
    assert fsm.update(0.0, False) == AlertState.IDLE

    # IDLE --signal=True--> CANDIDATE (ghi mốc bắt đầu 1.0)
    assert fsm.update(1.0, True) == AlertState.CANDIDATE
    assert fsm.state == AlertState.CANDIDATE

    # CANDIDATE duy trì tín hiệu nhưng chưa đủ duration_s (< 1.8s)
    assert fsm.update(2.0, True) == AlertState.CANDIDATE

    # CANDIDATE đủ duration_s (2.8 - 1.0 = 1.8s) -> ACTIVE
    assert fsm.update(2.8, True) == AlertState.ACTIVE
    assert fsm.state == AlertState.ACTIVE

    # ACTIVE tiếp tục duy trì tín hiệu -> vẫn ACTIVE
    assert fsm.update(3.5, True) == AlertState.ACTIVE

    # ACTIVE: signal mất (False) -> COOLDOWN (ghi mốc 4.0)
    assert fsm.update(4.0, False) == AlertState.COOLDOWN
    assert fsm.state == AlertState.COOLDOWN

    # COOLDOWN chưa đủ cooldown_s (< 3.0s) -> vẫn COOLDOWN
    assert fsm.update(5.5, False) == AlertState.COOLDOWN

    # COOLDOWN đủ cooldown_s (7.0 - 4.0 = 3.0s) -> về IDLE
    assert fsm.update(7.0, False) == AlertState.IDLE
    assert fsm.state == AlertState.IDLE


def test_transient_signal_no_activation():
    """Kiểm tra tín hiệu thoáng qua (< duration_s) không kích hoạt ACTIVE và trở về IDLE."""
    fsm = DurationFSM(duration_s=1.8, cooldown_s=3.0)

    # Xuất hiện tín hiệu -> CANDIDATE (mốc 0.0)
    assert fsm.update(0.0, True) == AlertState.CANDIDATE

    # Duy trì tín hiệu 1.0s (< 1.8s)
    assert fsm.update(1.0, True) == AlertState.CANDIDATE

    # Tín hiệu mất tại 1.5s (< 1.8s) -> quay về IDLE
    assert fsm.update(1.5, False) == AlertState.IDLE
    assert fsm.state == AlertState.IDLE

    # Tiếp tục không có tín hiệu -> duy trì IDLE
    assert fsm.update(2.0, False) == AlertState.IDLE
    assert fsm.state == AlertState.IDLE


def test_anti_spam_during_cooldown():
    """Kiểm tra chống spam trong cooldown: tín hiệu quay lại trong cooldown không báo lại."""
    fsm = DurationFSM(duration_s=1.8, cooldown_s=3.0)

    # Kích hoạt lên ACTIVE
    assert fsm.update(0.0, True) == AlertState.CANDIDATE
    assert fsm.update(1.8, True) == AlertState.ACTIVE

    # Tín hiệu mất -> chuyển sang COOLDOWN (mốc 2.0)
    assert fsm.update(2.0, False) == AlertState.COOLDOWN

    # Tín hiệu quay lại liên tục trong thời gian cooldown (< 3.0s) -> vẫn giữ COOLDOWN, không báo lại
    assert fsm.update(2.5, True) == AlertState.COOLDOWN
    assert fsm.update(3.5, True) == AlertState.COOLDOWN
    assert fsm.update(4.5, True) == AlertState.COOLDOWN
    assert fsm.update(4.9, True) == AlertState.COOLDOWN
    assert fsm.state == AlertState.COOLDOWN

    # Sau khi hết cooldown (5.0 - 2.0 = 3.0s) và tín hiệu tắt -> về IDLE
    assert fsm.update(5.0, False) == AlertState.IDLE
    assert fsm.state == AlertState.IDLE


def test_reset():
    """Kiểm tra hàm reset() đưa máy trạng thái về IDLE từ bất kỳ trạng thái nào."""
    fsm = DurationFSM(duration_s=1.8, cooldown_s=3.0)

    # Reset từ CANDIDATE
    fsm.update(0.0, True)
    assert fsm.state == AlertState.CANDIDATE
    fsm.reset()
    assert fsm.state == AlertState.IDLE

    # Reset từ ACTIVE
    fsm.update(0.0, True)
    fsm.update(1.8, True)
    assert fsm.state == AlertState.ACTIVE
    fsm.reset()
    assert fsm.state == AlertState.IDLE

    # Reset từ COOLDOWN
    fsm.update(0.0, True)
    fsm.update(1.8, True)
    fsm.update(2.0, False)
    assert fsm.state == AlertState.COOLDOWN
    fsm.reset()
    assert fsm.state == AlertState.IDLE
