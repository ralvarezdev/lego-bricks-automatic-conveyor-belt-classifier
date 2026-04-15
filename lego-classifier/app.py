import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageTk
import json
from pathlib import Path

class LegoClassifierApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.window.geometry("950x900")
        self.window.configure(bg="#f0f0f0")

        # Path Configuration
        self.base_dir = Path(__file__).resolve().parent
        self.models_dir = self.base_dir / "models"
        
        # Inference State
        self.session = None
        self.class_names = {}
        self.input_name = None
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        # Video State
        self.running = True
        self.vid = None
        self.current_camera_index = 0

        self.setup_ui()
        
        # Initialize camera
        self.camera_list = self.detect_cameras()
        if self.camera_list:
            self.camera_selector['values'] = self.camera_list
            self.camera_selector.current(0)
            self.init_camera(0)
        
        self.update_frame()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Builds the English UI with Model and Camera selectors."""
        # Top Control Panel
        self.ctrl_frame = ttk.LabelFrame(self.window, text=" System Controls ", padding=10)
        self.ctrl_frame.pack(fill=tk.X, padx=20, pady=10)

        # 1. Model Selector
        ttk.Label(self.ctrl_frame, text="Select Model:").grid(row=0, column=0, padx=5, sticky="w")
        self.model_list = [f.name for f in self.models_dir.glob("*.onnx")]
        self.model_selector = ttk.Combobox(self.ctrl_frame, values=self.model_list, state="readonly", width=40)
        self.model_selector.grid(row=0, column=1, padx=5, pady=5)
        self.model_selector.bind("<<ComboboxSelected>>", self.load_selected_model)

        # 2. Camera Selector
        ttk.Label(self.ctrl_frame, text="Select Camera:").grid(row=1, column=0, padx=5, sticky="w")
        self.camera_selector = ttk.Combobox(self.ctrl_frame, state="readonly", width=40)
        self.camera_selector.grid(row=1, column=1, padx=5, pady=5)
        self.camera_selector.bind("<<ComboboxSelected>>", self.on_camera_change)

        # Video Display
        self.video_label = tk.Label(self.window, background="black", borderwidth=2, relief="groove")
        self.video_label.pack(pady=10)

        # Results Panel
        self.info_frame = ttk.Frame(self.window, padding=20)
        self.info_frame.pack(fill=tk.X)

        self.result_var = tk.StringVar(value="Please select a model to begin...")
        self.lbl_result = ttk.Label(self.info_frame, textvariable=self.result_var, font=("Helvetica", 18, "bold"))
        self.lbl_result.pack()

        self.confidence_bar = ttk.Progressbar(self.info_frame, orient=tk.HORIZONTAL, length=500, mode='determinate')
        self.confidence_bar.pack(pady=10)

    def load_selected_model(self, event=None):
        """Loads the ONNX session and the matching JSON mapping."""
        model_name = self.model_selector.get()
        model_path = self.models_dir / model_name
        
        # Determine mapping filename (e.g., project_mapping.json)
        # Assuming the standard we set: {project_name}_{n}classes.onnx
        mapping_name = model_name.replace(".onnx", "_mapping.json")
        mapping_path = self.models_dir / mapping_name

        if not mapping_path.exists():
            messagebox.showerror("Error", f"Mapping file not found: {mapping_name}")
            return

        try:
            # Load Names
            with open(mapping_path, "r") as f:
                self.class_names = json.load(f)
            
            # Initialize ONNX
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(str(model_path), providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            
            self.result_var.set(f"Model Loaded: {model_name}")
            print(f"Successfully loaded {model_name} with {len(self.class_names)} classes.")
        except Exception as e:
            messagebox.showerror("Inference Error", f"Failed to load model: {e}")

    def detect_cameras(self):
        available = []
        for i in range(3):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(f"Camera {i}")
                cap.release()
        return available

    def init_camera(self, index):
        if self.vid: self.vid.release()
        self.vid = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    def on_camera_change(self, event):
        new_index = int(self.camera_selector.get().split(" ")[1])
        self.init_camera(new_index)

    def preprocess(self, frame):
        """Prepares the frame for EfficientNet-B0 without distorting the aspect ratio."""
        
        # 1. Center-Crop the frame to a perfect square (e.g., 480x480)
        h, w, _ = frame.shape
        min_dim = min(h, w)
        start_x = (w // 2) - (min_dim // 2)
        start_y = (h // 2) - (min_dim // 2)
        cropped_frame = frame[start_y:start_y+min_dim, start_x:start_x+min_dim]

        # 2. Convert and Resize (Now it squishes a square into a smaller square -> No distortion!)
        image = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image).resize((224, 224), Image.Resampling.BILINEAR)
        
        # 3. Standardize
        img_data = np.array(image).astype(np.float32) / 255.0
        img_data = (img_data - self.mean) / self.std
        img_data = np.transpose(img_data, (2, 0, 1))
        
        return np.expand_dims(img_data, axis=0)

    def update_frame(self):
        if self.vid and self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                # If a model is loaded, run inference
                if self.session:
                    input_tensor = self.preprocess(frame)
                    outputs = self.session.run(None, {self.input_name: input_tensor})
                    
                    logits = outputs[0]
                    idx = np.argmax(logits)
                    
                    # Calculate Softmax Confidence
                    exp_logits = np.exp(logits[0] - np.max(logits[0]))
                    conf = exp_logits[idx] / exp_logits.sum()

                    piece_name = self.class_names.get(str(idx), "Unknown")
                    
                    # Update UI based on confidence threshold
                    if conf > 0.75:
                        self.result_var.set(f"{piece_name} ({conf:.1%})")
                        self.lbl_result.config(foreground="#2ecc71")
                    else:
                        self.result_var.set("Scanning conveyor belt...")
                        self.lbl_result.config(foreground="#7f8c8d")
                    
                    self.confidence_bar['value'] = conf * 100
                    
                # Render Video with a Targeting Box
                display_frame = cv2.resize(frame, (640, 480))
                
                # Draw a square in the center to show the user the crop area
                h, w, _ = display_frame.shape
                min_dim = min(h, w)
                start_x = (w // 2) - (min_dim // 2)
                start_y = (h // 2) - (min_dim // 2)
                cv2.rectangle(display_frame, (start_x, start_y), (start_x + min_dim, start_y + min_dim), (0, 255, 0), 2)

                img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

        if self.running:
            self.window.after(15, self.update_frame)

    def on_closing(self):
        self.running = False
        if self.vid: self.vid.release()
        self.window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LegoClassifierApp(root, "LEGO Classifier - Conveyor Belt System")
    root.mainloop()