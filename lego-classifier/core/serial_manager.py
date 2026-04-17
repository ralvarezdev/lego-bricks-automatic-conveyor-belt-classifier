import threading
import json

try:
    import serial
    import serial.tools.list_ports

    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class SerialManager:
    def __init__(self, log_callback=None):
        self.ser = None
        self.connected = False
        self.log_callback = log_callback
        self.lock = threading.Lock()

    def get_ports(self):
        if not HAS_SERIAL:
            return ["Mock COM1 (pyserial missing)"]
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports]

    def connect(self, port, baud_rate=115200):
        if not HAS_SERIAL:
            self._log("[SYS] pyserial is not installed. Mock connected.")
            self.connected = True
            return True
        try:
            self.ser = serial.Serial(port, baudrate=baud_rate, timeout=1)
            self.connected = True
            self._log(f"[SYS] Connected to {port} at {baud_rate} baud.")

            # Start background thread to read from ESP32
            threading.Thread(target=self._read_loop, daemon=True).start()

            return True
        except Exception as e:
            self._log(f"[ERR] Serial connection failed: {e}")
            return False

    def _read_loop(self):
        while self.connected and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode("utf-8").strip()
                    if line:
                        self._log(f"[RX] {line}")
            except Exception as e:
                self._log(f"[ERR] Error reading from serial: {e}")
                self.disconnect()
                break

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connected = False
        self._log("[SYS] Serial disconnected.")

    def send_payload(self, payload_dict):
        if not self.connected:
            self._log("[ERR] Cannot send, serial not connected.")
            return False

        def _send():
            try:
                msg = json.dumps(payload_dict) + "\n"
                if self.ser:
                    with self.lock:
                        self.ser.write(msg.encode("utf-8"))
                        self.ser.flush()
                self._log(f"[TX] {msg.strip()}")
            except Exception as e:
                self._log(f"[ERR] Failed to send payload: {e}")
                self.disconnect()

        threading.Thread(target=_send, daemon=True).start()
        return True

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)
