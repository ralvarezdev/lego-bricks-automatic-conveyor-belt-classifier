import serial
import time
import threading
from core.domain.models import GateConfigModel


class ArduinoController:
    def __init__(self, baud_rate: int = 115200):
        self.baud_rate = baud_rate
        self.port = None
        self._serial: serial.Serial | None = None
        self._lock = threading.Lock()

    def connect(self, port: str) -> None:
        self.port = port
        self._attempt_connection()

    def is_connected(self) -> bool:
        with self._lock:
            return self._serial is not None and self._serial.is_open

    def _attempt_connection(self):
        try:
            with self._lock:
                self._serial = serial.Serial(self.port, self.baud_rate, timeout=1)
        except serial.SerialException:
            self._serial = None

    def trigger_gate(self, gate_config: GateConfigModel) -> bool:
        with self._lock:
            if not self._serial or not self._serial.is_open:
                # Try auto-reconnect once before failing
                self._attempt_connection()
                if not self._serial:
                    return False

            try:
                payload = f"{gate_config.idx},{gate_config.lead_time},{gate_config.active_time}\n"
                self._serial.write(payload.encode("utf-8"))
                return True
            except serial.SerialException:
                if self._serial:
                    self._serial.close()
                self._serial = None
                return False
