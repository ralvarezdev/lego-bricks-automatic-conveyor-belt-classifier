from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class AppSettings(BaseSettings):
    CONFIDENCE_THRESHOLD: float = 0.75
    BAUD_RATE: int = 115200
    CAMERA_IDX: int = 0
    MODEL_PATH: Path = Path("models/classifier.onnx")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = AppSettings()
