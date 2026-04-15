import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CATALOG_FILE = DATA_DIR / "catalog.json"
PREVIEWS_DIR = DATA_DIR / "previews"
MODELS_DIR = BASE_DIR / "models"
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)


# Application Configurations
class AppConfig:
    BAUD_RATE = 115200
    CONFIDENCE_THRESHOLD = 0.75
    COOLDOWN_TIME = 4.0  # seconds


# UI Colors (Industrial Minimalist)
class Colors:
    BG = "#f8f9fa"
    SIDEBAR = "#ffffff"
    PRIMARY = "#228be6"
    DANGER = "#e74c3c"
    TEXT = "#333333"
    SUCCESS = "#2ecc71"
    MUTED = "#7f8c8d"
    WARNING = "#f39c12"
