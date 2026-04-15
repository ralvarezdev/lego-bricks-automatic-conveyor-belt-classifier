from typing import List, Dict, Optional
from pydantic import BaseModel, Field, model_validator
from core.domain.types import GateId, LabelId


class GateConfigModel(BaseModel):
    idx: GateId
    name: str = Field(..., min_length=1, max_length=50)
    lead_time: float = Field(ge=0.0, le=10.0, description="Delay before activation")
    active_time: float = Field(ge=0.1, le=10.0, description="Duration of activation")

    @model_validator(mode="after")
    def validate_timings(self):
        if self.lead_time + self.active_time > 15.0:
            raise ValueError(
                f"Gate '{self.name}' total cycle time exceeds maximum allowed (15s)."
            )
        return self


class ProjectConfigModel(BaseModel):
    project_name: str = "lego_classifier"
    selected_ids: List[int] = Field(default_factory=list)
    classes: Dict[str, str] = Field(default_factory=dict)
    gates: List[GateConfigModel] = Field(default_factory=list)
    gate_assignments: Dict[str, GateId] = Field(default_factory=dict)

    def get_gate_by_id(self, gate_id: GateId) -> Optional[GateConfigModel]:
        for g in self.gates:
            if g.idx == gate_id:
                return g
        return None
