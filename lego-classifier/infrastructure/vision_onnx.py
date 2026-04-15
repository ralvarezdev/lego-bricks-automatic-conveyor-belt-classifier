import json
from pathlib import Path
import numpy as np
import onnxruntime as ort
import cv2
from PIL import Image
from core.ports.interfaces import IVisionEngine
from core.domain.types import LabelId


class ONNXVisionEngine(IVisionEngine):
    def __init__(self, model_path: Path):
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        mapping_path = model_path.with_name(
            model_path.name.replace(".onnx", "_mapping.json")
        )
        if mapping_path.exists():
            with open(mapping_path, "r") as f:
                self.class_names = json.load(f)
        else:
            self.class_names = {}

        self.session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, frame: np.ndarray) -> tuple[LabelId, float]:
        h, w, _ = frame.shape
        min_dim = min(h, w)
        start_x = (w // 2) - (min_dim // 2)
        start_y = (h // 2) - (min_dim // 2)

        cropped_frame = frame[start_y : start_y + min_dim, start_x : start_x + min_dim]
        image = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image).resize((224, 224), Image.Resampling.BILINEAR)

        img_data = np.array(image).astype(np.float32) / 255.0
        img_data = (img_data - self.mean) / self.std
        img_data = np.transpose(img_data, (2, 0, 1))
        input_tensor = np.expand_dims(img_data, axis=0)

        outputs = self.session.run(None, {self.input_name: input_tensor})
        logits = outputs[0]
        idx = np.argmax(logits)
        exp_logits = np.exp(logits[0] - np.max(logits[0]))
        conf = exp_logits[idx] / exp_logits.sum()

        piece_name = self.class_names.get(str(idx), f"{idx}")
        return LabelId(piece_name), float(conf)
