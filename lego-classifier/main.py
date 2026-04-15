import sys
import os
from pathlib import Path

# Ensure the root directory is in the sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.app_window import LegoStudioApp
from infrastructure.serial_arduino import ArduinoController
from config.settings import settings


def main():
    # 1. Dependency Injection Composition Root
    # Here we instantiate infrastructure implementations.
    # Note: VisionEngine is instantiated dynamically when a model is selected in the UI.

    serial_controller = ArduinoController(baud_rate=settings.BAUD_RATE)

    # 2. Inject into the main GUI Window
    # For now, LegoStudioApp handles its own state, but we provide the hardware controller
    app = LegoStudioApp()

    # Optional: If LegoStudioApp was fully refactored to accept DI:
    # app = LegoStudioApp(serial_controller=serial_controller)

    # 3. Start Main Loop
    app.mainloop()


if __name__ == "__main__":
    main()
