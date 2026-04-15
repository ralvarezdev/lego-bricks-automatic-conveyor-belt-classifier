from enum import Enum, auto


class BeltState(Enum):
    IDLE = auto()
    PROCESSING = auto()
    ERROR = auto()


class ConveyorFSM:
    def __init__(self):
        self._state = BeltState.IDLE

    def can_accept_new_piece(self) -> bool:
        return self._state == BeltState.IDLE

    def lock_for_processing(self) -> bool:
        if self._state == BeltState.IDLE:
            self._state = BeltState.PROCESSING
            return True
        return False

    def release_lock(self):
        self._state = BeltState.IDLE

    def set_error(self):
        self._state = BeltState.ERROR
