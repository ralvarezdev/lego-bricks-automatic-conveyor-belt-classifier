from typing import Optional
from core.domain.models import ProjectConfigModel, GateConfigModel
from core.domain.state_machine import ConveyorFSM
from core.domain.types import LabelId
from core.ports.interfaces import IConveyorController


class SortingEngine:
    """Orchestrates the sorting logic, mapping predictions to gate triggers."""

    def __init__(self, conveyor_controller: IConveyorController, fsm: ConveyorFSM):
        self.serial = conveyor_controller
        self.fsm = fsm

    def evaluate_piece(
        self, label: LabelId, project: ProjectConfigModel
    ) -> Optional[int]:
        """
        Evaluates a predicted label, determines the gate, and triggers hardware.
        Returns the required lock time (ms) if successful, None otherwise.
        """
        # 1. Look up gate assignment
        gate_idx = project.gate_assignments.get(label)
        if gate_idx is None:
            return None  # No assigned gate, let it pass

        # 2. Retrieve gate configuration
        gate_config = project.get_gate_by_id(gate_idx)
        if not gate_config:
            return None

        # 3. Atomically lock the state machine
        if not self.fsm.lock_for_processing():
            return None

        # 4. Fire hardware
        success = self.serial.trigger_gate(gate_config)

        if success:
            # Return the total duration the belt should remain locked
            return int((gate_config.lead_time + gate_config.active_time) * 1000)
        else:
            self.fsm.set_error()
            return None
