from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Theme:
    # Backgrounds
    BG_BASE: Final[str] = "#0A0A0B"  # App background
    BG_PANEL: Final[str] = "#141416"  # Widget background
    BG_SURFACE: Final[str] = "#1E1E20"  # Input fields / Highlights

    # Typography
    TEXT_PRIMARY: Final[str] = "#E0E0E0"
    TEXT_SECONDARY: Final[str] = "#808084"
    FONT_DISPLAY: Final[tuple[str, int, str]] = ("JetBrains Mono", 18, "bold")
    FONT_MONO: Final[tuple[str, int]] = ("JetBrains Mono", 12)

    # State Accents (Neon/High Intensity)
    ACCENT_CYAN: Final[str] = "#00F0FF"  # Active scanning / System ON
    ACCENT_GREEN: Final[str] = "#39FF14"  # Confident match / Success
    ACCENT_AMBER: Final[str] = "#FFB000"  # Cooldown / System locked
    ACCENT_RED: Final[str] = "#FF003C"  # Error / Disconnected
