import queue
import threading
import cv2
import numpy as np
from core.ports.interfaces import IVisionEngine


class VisionWorker:
    def __init__(self, ai_engine: IVisionEngine):
        self.ai = ai_engine
        # maxsize=1: We only care about the absolute most recent frame. Drop the rest.
        self.frame_queue = queue.Queue(maxsize=1)
        self.result_queue = queue.Queue(maxsize=1)
        self._is_running = False

    def start(self, camera_idx: int):
        self._is_running = True
        threading.Thread(
            target=self._capture_loop,
            args=(camera_idx,),
            daemon=True,
            name="VisionCapture",
        ).start()
        threading.Thread(
            target=self._inference_loop, daemon=True, name="VisionInference"
        ).start()

    def stop(self):
        self._is_running = False

    def _capture_loop(self, camera_idx: int):
        # Use cv2.CAP_DSHOW on Windows for faster initialization if needed, but default is fine
        cap = cv2.VideoCapture(camera_idx)
        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                continue
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass  # Frame dropped to maintain real-time sync
        cap.release()

    def _inference_loop(self):
        while self._is_running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                label, conf = self.ai.predict(frame)
                # Replace the old result with the newest one
                if self.result_queue.full():
                    try:
                        self.result_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.result_queue.put_nowait((frame, label, conf))
            except queue.Empty:
                pass
