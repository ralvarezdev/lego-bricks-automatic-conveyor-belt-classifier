import cv2
import numpy as np


def RenderTacticalHUD(
    frame: np.ndarray, label: str, conf: float, is_locked: bool
) -> np.ndarray:
    """Draws an industrial HUD directly on the frame array."""
    h, w = frame.shape[:2]
    center_x, center_y = w // 2, h // 2
    box_size = 224
    half_box = box_size // 2

    # Determine state color
    color = (
        (0, 165, 255) if is_locked else (0, 255, 0) if conf > 0.75 else (255, 255, 0)
    )  # BGR

    # Draw Corner Reticles
    thickness = 2
    length = 20
    # Top-Left
    cv2.line(
        frame,
        (center_x - half_box, center_y - half_box),
        (center_x - half_box + length, center_y - half_box),
        color,
        thickness,
    )
    cv2.line(
        frame,
        (center_x - half_box, center_y - half_box),
        (center_x - half_box, center_y - half_box + length),
        color,
        thickness,
    )
    # Top-Right
    cv2.line(
        frame,
        (center_x + half_box, center_y - half_box),
        (center_x + half_box - length, center_y - half_box),
        color,
        thickness,
    )
    cv2.line(
        frame,
        (center_x + half_box, center_y - half_box),
        (center_x + half_box, center_y - half_box + length),
        color,
        thickness,
    )
    # Bottom-Left
    cv2.line(
        frame,
        (center_x - half_box, center_y + half_box),
        (center_x - half_box + length, center_y + half_box),
        color,
        thickness,
    )
    cv2.line(
        frame,
        (center_x - half_box, center_y + half_box),
        (center_x - half_box, center_y + half_box - length),
        color,
        thickness,
    )
    # Bottom-Right
    cv2.line(
        frame,
        (center_x + half_box, center_y + half_box),
        (center_x + half_box - length, center_y + half_box),
        color,
        thickness,
    )
    cv2.line(
        frame,
        (center_x + half_box, center_y + half_box),
        (center_x + half_box, center_y + half_box - length),
        color,
        thickness,
    )

    # Overlay Text with Drop Shadow for legibility
    text = f"TGT: {label} [{conf:.1%}]" if conf > 0.75 else "SCANNING..."
    cv2.putText(
        frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3
    )  # Shadow
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 1)  # Text

    if is_locked:
        cv2.putText(
            frame,
            "SYS.LOCKED",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 165, 255),
            2,
        )

    return frame
