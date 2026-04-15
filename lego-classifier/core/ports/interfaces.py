from typing import Protocol, Tuple
import numpy as np
from core.domain.models import GateConfigModel
from core.domain.types import LabelId


class IConveyorController(Protocol):
    def connect(self, port: str) -> None: ...
    def is_connected(self) -> bool: ...
    def trigger_gate(self, gate: GateConfigModel) -> bool: ...


class IVisionEngine(Protocol):
    def predict(self, frame: np.ndarray) -> Tuple[LabelId, float]: ...
