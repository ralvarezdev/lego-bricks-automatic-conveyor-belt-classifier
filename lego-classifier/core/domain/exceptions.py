class LegoSystemError(Exception):
    """Base exception for all system errors."""

    pass


class HardwareConnectionError(LegoSystemError):
    """Raised when Serial/Camera fails."""

    pass


class ConfigurationParseError(LegoSystemError):
    """Raised when JSON/Project is invalid."""

    pass


class VisionEngineError(LegoSystemError):
    """Raised during ONNX runtime failures."""

    pass
