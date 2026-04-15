from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto


class SystemState(Enum):
    IDLE = auto()
    COOLDOWN = auto()
    ERROR = auto()


@dataclass
class GateConfig:
    idx: int
    name: str
    lead_time: float
    active_time: float


@dataclass
class ProjectConfig:
    project_name: str = "lego_classifier"
    selected_ids: List[int] = field(default_factory=list)
    classes: Dict[str, str] = field(default_factory=dict)
    gates: List[GateConfig] = field(default_factory=list)
    gate_assignments: Dict[str, int] = field(
        default_factory=dict
    )  # label_id (string) -> gate_idx
