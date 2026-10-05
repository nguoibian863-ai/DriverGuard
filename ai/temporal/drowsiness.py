from enum import Enum

_EPS = 1e-9  # dung sai số thực khi so sánh mốc thời gian


class AlertState(Enum):
    """Các trạng thái cảnh báo của máy trạng thái."""

    IDLE = "IDLE"
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    COOLDOWN = "COOLDOWN"


class DurationFSM:
    """Máy trạng thái hữu hạn theo dõi thời lượng tín hiệu để kích hoạt cảnh báo."""

    def __init__(self, duration_s: float = 1.8, cooldown_s: float = 3.0) -> None:
        """Khởi tạo FSM với ngưỡng thời lượng và thời gian hồi chiêu."""
        self.duration_s: float = duration_s
        self.cooldown_s: float = cooldown_s
        self._state: AlertState = AlertState.IDLE
        self._candidate_start: float | None = None
        self._cooldown_start: float | None = None

    @property
    def state(self) -> AlertState:
        """Trạng thái hiện tại của FSM."""
        return self._state

    def reset(self) -> None:
        """Đặt lại máy trạng thái về IDLE và xóa các mốc thời gian."""
        self._state = AlertState.IDLE
        self._candidate_start = None
        self._cooldown_start = None

    def update(self, timestamp: float, signal: bool) -> AlertState:
        """Cập nhật trạng thái theo mốc thời gian và tín hiệu đầu vào."""
        if self._state == AlertState.IDLE:
            if signal:
                self._state = AlertState.CANDIDATE
                self._candidate_start = timestamp

        elif self._state == AlertState.CANDIDATE:
            if not signal:
                self._state = AlertState.IDLE
                self._candidate_start = None
            elif self._candidate_start is not None and (timestamp - self._candidate_start >= self.duration_s - _EPS):
                self._state = AlertState.ACTIVE
                self._candidate_start = None

        elif self._state == AlertState.ACTIVE:
            if not signal:
                self._state = AlertState.COOLDOWN
                self._cooldown_start = timestamp

        elif self._state == AlertState.COOLDOWN:
            if self._cooldown_start is not None and (timestamp - self._cooldown_start >= self.cooldown_s - _EPS):
                self._state = AlertState.IDLE
                self._cooldown_start = None
                if signal:
                    self._state = AlertState.CANDIDATE
                    self._candidate_start = timestamp

        return self._state
