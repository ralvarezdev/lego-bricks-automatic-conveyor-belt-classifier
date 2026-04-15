import os
import sys
import threading
import json
import customtkinter as ctk
from PIL import Image
import cv2
import numpy as np
import onnxruntime as ort
from tkinter import filedialog, messagebox

# Adjust path so `core` can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.constants import *
from core.models import ProjectConfig, GateConfig, SystemState
from core.extractor import run_extractor
from gui.console import ThreadSafeConsole
from core.balance import run_check_balance
from core.trainer import run_training
from core.serial_manager import SerialManager

import queue
from gui.components.vision_canvas import RenderTacticalHUD
from infrastructure.vision_worker import VisionWorker
from infrastructure.vision_onnx import ONNXVisionEngine
from core.domain.state_machine import ConveyorFSM

ctk.set_appearance_mode("Light")


class LegoStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LEGO Studio - URU Sorting System")
        self.geometry("1200x850")
        self.configure(fg_color=Colors.BG)

        # Output Redirection
        self.console_queue = []
        self.original_stdout = sys.stdout
        self.ts_console = ThreadSafeConsole(self.write_to_console)
        sys.stdout = self.ts_console

        # Studio State
        self.catalog = {}
        self.catalog_keys = []
        self.current_preview_index = 0

        # Project Data Model
        self.project = ProjectConfig()
        self.project_name_var = ctk.StringVar(value=self.project.project_name)

        # Serial & System State
        self.serial_mgr = SerialManager(log_callback=self.write_debug_console)
        self.system_state = SystemState.IDLE
        self.conveyor_fsm = ConveyorFSM()
        self.vision_worker = None
        self._current_frame_img = None

        # Inference State
        self.session = None
        self.class_names = {}
        self.input_name = None
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        self.running_camera = False
        self.vid = None

        if not self.check_extracted_data():
            self.build_setup_ui()
        else:
            self.load_catalog()
            self.build_main_ui()

    def write_to_console(self, msg):
        self.after(0, self._append_sys_console, msg)

    def write_debug_console(self, msg):
        self.after(0, self._append_debug_console, msg)

    def _append_sys_console(self, msg):
        if hasattr(self, "sys_console") and self.sys_console.winfo_exists():
            self.sys_console.insert("end", msg)
            self.sys_console.see("end")
        elif hasattr(self, "setup_console") and self.setup_console.winfo_exists():
            self.setup_console.insert("end", msg)
            self.setup_console.see("end")

    def _append_debug_console(self, msg):
        if hasattr(self, "debug_console") and self.debug_console.winfo_exists():
            self.debug_console.insert("end", msg + "\n")
            self.debug_console.see("end")

    def check_extracted_data(self):
        return (
            CATALOG_FILE.exists()
            and PREVIEWS_DIR.exists()
            and any(PREVIEWS_DIR.iterdir())
        )

    def load_catalog(self):
        try:
            with open(CATALOG_FILE, "r") as f:
                self.catalog = json.load(f)
            self.catalog_keys = sorted([int(k) for k in self.catalog.keys()])
        except Exception as e:
            print(f"Failed to load catalog: {e}")

    # ==============================
    # 1. SETUP UI
    # ==============================
    def build_setup_ui(self):
        self.setup_frame = ctk.CTkFrame(self, fg_color=Colors.SIDEBAR, corner_radius=10)
        self.setup_frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self.setup_frame,
            text="System Uninitialized",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=Colors.TEXT,
        ).pack(pady=(30, 10), padx=50)
        ctk.CTkLabel(
            self.setup_frame,
            text="Missing catalog.json or previews.\nPlease run the Extractor pipeline to continue.",
            text_color=Colors.TEXT,
        ).pack(pady=(0, 20), padx=50)

        self.extract_btn = ctk.CTkButton(
            self.setup_frame,
            text="Run Extractor",
            fg_color=Colors.PRIMARY,
            command=self.run_extractor_thread,
        )
        self.extract_btn.pack(pady=(0, 30), padx=50)

        self.setup_console = ctk.CTkTextbox(
            self.setup_frame,
            width=600,
            height=200,
            fg_color="#1e1e1e",
            text_color="#00ff00",
        )
        self.setup_console.pack(pady=(0, 20), padx=20)

    def run_extractor_thread(self):
        self.extract_btn.configure(state="disabled", text="Extracting...")
        threading.Thread(target=self._extractor_task, daemon=True).start()

    def _extractor_task(self):
        try:
            print("Starting extraction...")
            run_extractor()
            self.after(0, self.on_extraction_complete)
        except Exception as e:
            print(f"Error: {e}")
            self.after(
                0,
                lambda: self.extract_btn.configure(
                    state="normal", text="Retry Extractor"
                ),
            )

    def on_extraction_complete(self):
        self.setup_frame.destroy()
        self.load_catalog()
        self.build_main_ui()

    # ==============================
    # 2. MAIN UI
    # ==============================
    def build_main_ui(self):
        self.tabview = ctk.CTkTabview(self, fg_color=Colors.BG)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_studio = self.tabview.add("Project Studio (Previewer)")
        self.tab_gates = self.tabview.add("Gates Setup")
        self.tab_live = self.tabview.add("Live Belt (Inference)")
        self.tab_console = self.tabview.add("System Logs")

        self.build_studio_tab()
        self.build_gates_tab()
        self.build_live_tab()
        self.build_console_tab()

    # --- GATES SETUP TAB ---
    def build_gates_tab(self):
        left_frame = ctk.CTkFrame(self.tab_gates, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            left_frame,
            text="Configured Gates",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=10)

        self.gates_scroll = ctk.CTkScrollableFrame(left_frame, fg_color=Colors.SIDEBAR)
        self.gates_scroll.pack(fill="both", expand=True, pady=10)

        right_frame = ctk.CTkFrame(self.tab_gates, fg_color=Colors.SIDEBAR)
        right_frame.pack(side="right", fill="y", padx=10, pady=10)
        right_frame.configure(width=300)

        ctk.CTkLabel(
            right_frame, text="Add New Gate", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=20, padx=20)

        ctk.CTkLabel(right_frame, text="Gate Index (ID):").pack(anchor="w", padx=20)
        self.gate_idx_var = ctk.StringVar()
        ctk.CTkEntry(right_frame, textvariable=self.gate_idx_var).pack(
            fill="x", padx=20, pady=(0, 10)
        )

        ctk.CTkLabel(right_frame, text="Gate Name:").pack(anchor="w", padx=20)
        self.gate_name_var = ctk.StringVar()
        ctk.CTkEntry(right_frame, textvariable=self.gate_name_var).pack(
            fill="x", padx=20, pady=(0, 10)
        )

        ctk.CTkLabel(right_frame, text="Lead Time (s):").pack(anchor="w", padx=20)
        self.gate_lead_var = ctk.StringVar()
        ctk.CTkEntry(right_frame, textvariable=self.gate_lead_var).pack(
            fill="x", padx=20, pady=(0, 10)
        )

        ctk.CTkLabel(right_frame, text="Active Time (s):").pack(anchor="w", padx=20)
        self.gate_active_var = ctk.StringVar()
        ctk.CTkEntry(right_frame, textvariable=self.gate_active_var).pack(
            fill="x", padx=20, pady=(0, 20)
        )

        ctk.CTkButton(
            right_frame, text="Add Gate", fg_color=Colors.PRIMARY, command=self.add_gate
        ).pack(fill="x", padx=20)

        self.refresh_gates_ui()

    def add_gate(self):
        try:
            idx = int(self.gate_idx_var.get())
            name = self.gate_name_var.get().strip()
            lead = float(self.gate_lead_var.get())
            active = float(self.gate_active_var.get())

            # Check if index already exists
            if any(g.idx == idx for g in self.project.gates):
                messagebox.showwarning("Warning", f"Gate index {idx} already exists!")
                return

            new_gate = GateConfig(
                idx=idx, name=name, lead_time=lead, active_time=active
            )
            self.project.gates.append(new_gate)
            self.refresh_gates_ui()
            self.refresh_sidebar()  # Update dropdowns in studio tab
            self.save_project()  # Auto-save
        except ValueError:
            messagebox.showerror(
                "Error", "Invalid number formats for Index, Lead Time, or Active Time."
            )

    def delete_gate(self, idx):
        self.project.gates = [g for g in self.project.gates if g.idx != idx]
        # Remove from assignments
        self.project.gate_assignments = {
            k: v for k, v in self.project.gate_assignments.items() if v != idx
        }
        self.refresh_gates_ui()
        self.refresh_sidebar()
        self.save_project()  # Auto-save

    def refresh_gates_ui(self):
        for widget in self.gates_scroll.winfo_children():
            widget.destroy()

        for gate in self.project.gates:
            row = ctk.CTkFrame(self.gates_scroll, fg_color="white", corner_radius=5)
            row.pack(fill="x", pady=5, padx=5)

            info_txt = f"[{gate.idx}] {gate.name} | Lead: {gate.lead_time}s | Active: {gate.active_time}s"
            ctk.CTkLabel(
                row,
                text=info_txt,
                text_color=Colors.TEXT,
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left", padx=10, pady=10)
            ctk.CTkButton(
                row,
                text="Delete",
                fg_color=Colors.DANGER,
                width=60,
                command=lambda i=gate.idx: self.delete_gate(i),
            ).pack(side="right", padx=10, pady=10)

    # --- STUDIO TAB ---
    def build_studio_tab(self):
        self.tab_studio.grid_columnconfigure(0, weight=2)
        self.tab_studio.grid_columnconfigure(1, weight=1)
        self.tab_studio.grid_rowconfigure(0, weight=1)

        # Left: Previewer
        left_panel = ctk.CTkFrame(self.tab_studio, fg_color="transparent")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.preview_lbl = ctk.CTkLabel(
            left_panel, text="No Image", width=400, height=400, fg_color="#e9ecef"
        )
        self.preview_lbl.pack(pady=10)

        self.info_id_lbl = ctk.CTkLabel(
            left_panel, text="ID:", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.info_id_lbl.pack()
        self.info_name_lbl = ctk.CTkLabel(
            left_panel, text="Name", text_color=Colors.MUTED
        )
        self.info_name_lbl.pack(pady=5)

        self.btn_toggle = ctk.CTkButton(
            left_panel,
            text="SELECT",
            font=("Helvetica", 14, "bold"),
            command=self.toggle_selection,
        )
        self.btn_toggle.pack(pady=10)

        nav_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        nav_frame.pack(pady=10)
        ctk.CTkButton(nav_frame, text="< Prev", width=80, command=self.prev_item).pack(
            side="left", padx=5
        )

        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            nav_frame,
            textvariable=self.search_var,
            placeholder_text="Search ID/Name...",
            width=150,
        )
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<Return>", lambda e: self.search_item())
        ctk.CTkButton(nav_frame, text="Jump", width=60, command=self.search_item).pack(
            side="left", padx=5
        )
        ctk.CTkButton(nav_frame, text="Next >", width=80, command=self.next_item).pack(
            side="left", padx=5
        )

        file_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        file_frame.pack(pady=20, fill="x")
        ctk.CTkButton(
            file_frame, text="LOAD JSON", fg_color="#9b59b6", command=self.load_project
        ).pack(side="left", padx=5)
        ctk.CTkEntry(file_frame, textvariable=self.project_name_var, width=150).pack(
            side="left", padx=5, expand=True
        )
        ctk.CTkButton(
            file_frame,
            text="SAVE JSON",
            fg_color=Colors.PRIMARY,
            command=self.save_project,
        ).pack(side="right", padx=5)

        # Right: Sidebar
        right_panel = ctk.CTkFrame(self.tab_studio, fg_color=Colors.SIDEBAR)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.sidebar_title = ctk.CTkLabel(
            right_panel,
            text="Selected Pieces (0)",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.sidebar_title.pack(pady=10)

        self.tray_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self.tray_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        tools_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        tools_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkButton(
            tools_frame,
            text="Check Balance",
            fg_color="transparent",
            border_width=1,
            text_color=Colors.TEXT,
            command=self.thread_check_balance,
        ).pack(fill="x", pady=5)

        epoch_frame = ctk.CTkFrame(tools_frame, fg_color="transparent")
        epoch_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(epoch_frame, text="Epochs:").pack(side="left", padx=5)
        self.epochs_var = ctk.StringVar(value="5")
        ctk.CTkEntry(epoch_frame, textvariable=self.epochs_var, width=60).pack(
            side="right", padx=5
        )

        ctk.CTkButton(
            tools_frame,
            text="Start Training",
            fg_color=Colors.PRIMARY,
            command=self.thread_train_model,
        ).pack(fill="x", pady=5)

        self.update_studio_display()

    def update_studio_display(self):
        if not self.catalog_keys:
            return
        current_id = self.catalog_keys[self.current_preview_index]
        item = self.catalog[str(current_id)]

        img_path = PREVIEWS_DIR / item["image_path"]
        if img_path.exists():
            img = Image.open(img_path)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(380, 380))
            self.preview_lbl.configure(image=ctk_img, text="")

        self.info_id_lbl.configure(text=f"LABEL ID: {current_id}")
        self.info_name_lbl.configure(text=item["name"])

        if current_id in self.project.selected_ids:
            self.btn_toggle.configure(text="✓ SELECTED", fg_color=Colors.SUCCESS)
        else:
            self.btn_toggle.configure(text="SELECT", fg_color=Colors.MUTED)

    def next_item(self):
        self.current_preview_index = (self.current_preview_index + 1) % len(
            self.catalog_keys
        )
        self.update_studio_display()

    def prev_item(self):
        self.current_preview_index = (self.current_preview_index - 1) % len(
            self.catalog_keys
        )
        self.update_studio_display()

    def search_item(self):
        query = self.search_var.get().strip().lower()
        if not query:
            return
        try:
            target_id = int(query)
            if target_id in self.catalog_keys:
                self.current_preview_index = self.catalog_keys.index(target_id)
                self.update_studio_display()
                return
        except ValueError:
            pass

        for i, label_id in enumerate(self.catalog_keys):
            if query in self.catalog[str(label_id)]["name"].lower():
                self.current_preview_index = i
                self.update_studio_display()
                return

    def toggle_selection(self):
        current_id = self.catalog_keys[self.current_preview_index]
        if current_id in self.project.selected_ids:
            self.project.selected_ids.remove(current_id)
            if str(current_id) in self.project.gate_assignments:
                del self.project.gate_assignments[str(current_id)]
        else:
            self.project.selected_ids.append(current_id)
        self.update_studio_display()
        self.refresh_sidebar()

    def remove_from_sidebar(self, target_id):
        if target_id in self.project.selected_ids:
            self.project.selected_ids.remove(target_id)
            if str(target_id) in self.project.gate_assignments:
                del self.project.gate_assignments[str(target_id)]
            self.refresh_sidebar()
            self.update_studio_display()

    def assign_gate(self, choice, sid):
        if choice == "None":
            if str(sid) in self.project.gate_assignments:
                del self.project.gate_assignments[str(sid)]
            return

        idx = int(choice.split(" ")[1])  # Parse "Gate X" -> X
        self.project.gate_assignments[str(sid)] = idx

    def refresh_sidebar(self):
        for widget in self.tray_scroll.winfo_children():
            widget.destroy()

        self.sidebar_images = []  # Prevent garbage collection of thumbnails
        self.sidebar_title.configure(
            text=f"Selected Pieces ({len(self.project.selected_ids)})"
        )
        gate_names = ["None"] + [f"Gate {g.idx}" for g in self.project.gates]

        for sid in sorted(list(self.project.selected_ids)):
            item = self.catalog.get(str(sid))
            if not item:
                continue

            row = ctk.CTkFrame(self.tray_scroll, fg_color="white", corner_radius=5)
            row.pack(fill="x", pady=2)

            # 1. Thumbnail Image
            img_path = PREVIEWS_DIR / item["image_path"]
            if img_path.exists():
                try:
                    img = Image.open(img_path)
                    ctk_img = ctk.CTkImage(
                        light_image=img, dark_image=img, size=(40, 40)
                    )
                    self.sidebar_images.append(ctk_img)
                    ctk.CTkLabel(row, image=ctk_img, text="").pack(
                        side="left", padx=5, pady=5
                    )
                except Exception:
                    pass

            # 2. Middle Frame for Text & Combobox
            mid_frame = ctk.CTkFrame(row, fg_color="transparent")
            mid_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            ctk.CTkLabel(
                mid_frame,
                text=f"ID {sid}: {item['name'][:15]}...",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=Colors.TEXT,
                anchor="w",
            ).pack(fill="x")

            assigned_idx = self.project.gate_assignments.get(str(sid))
            current_val = f"Gate {assigned_idx}" if assigned_idx is not None else "None"

            combo = ctk.CTkOptionMenu(
                mid_frame,
                values=gate_names,
                height=24,
                command=lambda c, s=sid: self.assign_gate(c, s),
            )
            combo.set(current_val)
            combo.pack(fill="x", pady=(2, 0))

            # 3. Right Frame for Action Buttons (Only Remove/Close remains)
            right_frame = ctk.CTkFrame(row, fg_color="transparent")
            right_frame.pack(side="right", fill="y", padx=5, pady=5)

            ctk.CTkButton(
                right_frame,
                text="✖",
                width=28,
                height=28,
                fg_color=Colors.DANGER,
                command=lambda i=sid: self.remove_from_sidebar(i),
            ).pack(side="right", padx=(2, 0))

    def save_project(self):
        if not self.project.selected_ids:
            print("Cannot save empty project.")
            return
        p_name = self.project_name_var.get().strip().replace(" ", "_")
        export_path = DATA_DIR / f"{p_name}.json"

        self.project.project_name = p_name
        self.project.classes = {
            str(sid): self.catalog[str(sid)]["name"]
            for sid in self.project.selected_ids
        }

        data = {
            "project_name": self.project.project_name,
            "selected_ids": self.project.selected_ids,
            "classes": self.project.classes,
            "gates": [g.__dict__ for g in self.project.gates],
            "gate_assignments": self.project.gate_assignments,
        }
        with open(export_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Project saved to {export_path.name}")

    def load_project(self):
        filepath = filedialog.askopenfilename(
            initialdir=DATA_DIR, filetypes=[("JSON files", "*.json")]
        )
        if filepath:
            with open(filepath, "r") as f:
                config = json.load(f)
            self.project.selected_ids = config.get("selected_ids", [])
            self.project.project_name = config.get("project_name", "lego_classifier")
            self.project.classes = config.get("classes", {})
            self.project.gate_assignments = config.get("gate_assignments", {})

            gates_raw = config.get("gates", [])
            self.project.gates = [GateConfig(**g) for g in gates_raw]

            self.project_name_var.set(self.project.project_name)
            self.update_studio_display()
            self.refresh_sidebar()
            self.refresh_gates_ui()
            print(f"Loaded project from {filepath}")

    # --- THREADED JOBS ---
    def thread_check_balance(self):
        p_name = self.project_name_var.get().strip()
        config_path = DATA_DIR / f"{p_name}.json"
        self.tabview.set("System Logs")
        threading.Thread(
            target=run_check_balance, args=(config_path,), daemon=True
        ).start()

    def thread_train_model(self):
        p_name = self.project_name_var.get().strip()
        config_path = DATA_DIR / f"{p_name}.json"

        try:
            epochs = int(self.epochs_var.get())
        except ValueError:
            epochs = 5

        self.tabview.set("System Logs")
        threading.Thread(
            target=run_training, args=(config_path, 32, epochs), daemon=True
        ).start()

    # --- LIVE BELT TAB ---
    def build_live_tab(self):
        self.tab_live.grid_columnconfigure(0, weight=2)
        self.tab_live.grid_columnconfigure(1, weight=1)
        self.tab_live.grid_rowconfigure(1, weight=1)

        # Top Bar (Serial & AI Connection)
        top_bar = ctk.CTkFrame(self.tab_live, fg_color=Colors.SIDEBAR)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(top_bar, text="COM Port:").pack(side="left", padx=5)
        self.com_selector = ctk.CTkOptionMenu(
            top_bar, values=self.serial_mgr.get_ports()
        )
        self.com_selector.pack(side="left", padx=5)

        self.btn_serial = ctk.CTkButton(
            top_bar, text="Connect USB", width=100, command=self.toggle_serial
        )
        self.btn_serial.pack(side="left", padx=10)

        ctk.CTkLabel(top_bar, text="Model:").pack(side="left", padx=(30, 5))
        self.model_selector = ctk.CTkOptionMenu(
            top_bar,
            values=["--- Select Model ---"]
            + [f.name for f in MODELS_DIR.glob("*.onnx")],
            command=self.load_onnx_model,
        )
        self.model_selector.pack(side="left", padx=5)

        ctk.CTkLabel(top_bar, text="Camera:").pack(side="left", padx=(30, 5))
        self.camera_selector = ctk.CTkOptionMenu(
            top_bar,
            values=["Camera 0", "Camera 1", "Camera 2"],
            command=self.change_camera,
        )
        self.camera_selector.pack(side="left", padx=5)

        self.btn_cam_toggle = ctk.CTkButton(
            top_bar, text="Start Vision", width=100, command=self.toggle_camera
        )
        self.btn_cam_toggle.pack(side="left", padx=20)

        # Left Column (Vision Node)
        vision_frame = ctk.CTkFrame(self.tab_live, fg_color="transparent")
        vision_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.video_canvas = ctk.CTkLabel(vision_frame, text="", fg_color="black")
        self.video_canvas.pack(fill="both", expand=True, pady=5)

        status_frame = ctk.CTkFrame(vision_frame, fg_color=Colors.SIDEBAR)
        status_frame.pack(fill="x", pady=5)

        self.live_result_lbl = ctk.CTkLabel(
            status_frame,
            text="Please select a model and start camera...",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.live_result_lbl.pack(pady=5)

        self.live_conf_bar = ctk.CTkProgressBar(
            status_frame, width=500, progress_color=Colors.SUCCESS
        )
        self.live_conf_bar.set(0)
        self.live_conf_bar.pack(pady=10)

        # Right Column (Debug Console & Status)
        debug_frame = ctk.CTkFrame(self.tab_live, fg_color=Colors.SIDEBAR)
        debug_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)

        ctk.CTkLabel(
            debug_frame, text="System Status", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        self.lbl_stat_ai = ctk.CTkLabel(
            debug_frame, text="AI: OFFLINE", text_color=Colors.DANGER
        )
        self.lbl_stat_ai.pack()
        self.lbl_stat_serial = ctk.CTkLabel(
            debug_frame, text="SERIAL: DISCONNECTED", text_color=Colors.DANGER
        )
        self.lbl_stat_serial.pack()
        self.lbl_stat_engine = ctk.CTkLabel(
            debug_frame, text="STATE: IDLE", text_color=Colors.PRIMARY
        )
        self.lbl_stat_engine.pack()

        ctk.CTkLabel(
            debug_frame,
            text="Debug Console (TX/RX)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 5))
        self.debug_console = ctk.CTkTextbox(
            debug_frame, fg_color="#1e1e1e", text_color="#00ff00", font=("Consolas", 12)
        )
        self.debug_console.pack(fill="both", expand=True, padx=10, pady=10)

    def toggle_serial(self):
        if self.serial_mgr.connected:
            self.serial_mgr.disconnect()
            self.btn_serial.configure(text="Connect USB", fg_color=Colors.PRIMARY)
            self.lbl_stat_serial.configure(
                text="SERIAL: DISCONNECTED", text_color=Colors.DANGER
            )
        else:
            port = self.com_selector.get()
            if self.serial_mgr.connect(port, AppConfig.BAUD_RATE):
                self.btn_serial.configure(text="Disconnect", fg_color=Colors.DANGER)
                self.lbl_stat_serial.configure(
                    text="SERIAL: CONNECTED", text_color=Colors.SUCCESS
                )

    def load_onnx_model(self, model_name):
        if model_name == "--- Select Model ---":
            return
        model_path = MODELS_DIR / model_name
        try:
            self.session = ONNXVisionEngine(model_path)
            self.live_result_lbl.configure(
                text=f"Model Loaded: {model_name}", text_color=Colors.TEXT
            )
            self.lbl_stat_ai.configure(text="AI: ONLINE", text_color=Colors.SUCCESS)
        except Exception as e:
            print(f"Failed to load ONNX: {e}")

    def toggle_camera(self):
        if self.running_camera:
            self.running_camera = False
            self.btn_cam_toggle.configure(text="Start Vision", fg_color=Colors.PRIMARY)
            if self.vision_worker:
                self.vision_worker.stop()
                self.vision_worker = None
            self.video_canvas.configure(image="")
        else:
            if not self.session:
                print("Cannot start camera without AI model.")
                return
            cam_idx = int(self.camera_selector.get().split(" ")[1])
            self.running_camera = True
            self.btn_cam_toggle.configure(text="Stop Vision", fg_color=Colors.DANGER)
            self.vision_worker = VisionWorker(self.session)
            self.vision_worker.start(cam_idx)
            self.ProcessLiveTick()

    def change_camera(self, choice):
        if self.running_camera:
            self.toggle_camera()
            self.toggle_camera()

    def set_system_idle(self):
        self.system_state = SystemState.IDLE
        self.conveyor_fsm = ConveyorFSM()
        self.vision_worker = None
        self._current_frame_img = None
        self.lbl_stat_engine.configure(text="STATE: IDLE", text_color=Colors.PRIMARY)
        self.write_debug_console("[SYS] Cooldown finished. Resuming inference.")

    def trigger_cooldown(self):
        self.system_state = SystemState.COOLDOWN
        self.lbl_stat_engine.configure(
            text="STATE: COOLDOWN LOCK", text_color=Colors.WARNING
        )
        self.write_debug_console(f"[SYS] System locked for {AppConfig.COOLDOWN_TIME}s")
        self.after(int(AppConfig.COOLDOWN_TIME * 1000), self.set_system_idle)

    def ProcessLiveTick(self):
        if not self.running_camera or not self.vision_worker:
            return

        try:
            frame, label, conf = self.vision_worker.result_queue.get_nowait()
        except queue.Empty:
            self.after(15, self.ProcessLiveTick)
            return

        is_locked = not self.conveyor_fsm.can_accept_new_piece()

        hud_frame = RenderTacticalHUD(frame, str(label), conf, is_locked)

        display_frame = cv2.resize(hud_frame, (640, 480))
        img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        from PIL import Image

        imgtk = ctk.CTkImage(light_image=Image.fromarray(img), size=(640, 480))
        self._current_frame_img = imgtk
        self.video_canvas.configure(image=imgtk)
        self.video_canvas.image = imgtk

        if is_locked:
            self.after(15, self.ProcessLiveTick)
            return

        if conf < AppConfig.CONFIDENCE_THRESHOLD:
            self.live_result_lbl.configure(
                text="Scanning conveyor belt...", text_color=Colors.MUTED
            )
            self.live_conf_bar.set(conf)
            self.after(15, self.ProcessLiveTick)
            return

        self.live_result_lbl.configure(
            text=f"{label} ({conf:.1%})", text_color=Colors.SUCCESS
        )
        self.live_conf_bar.set(conf)
        self._TriggerSortingRoutine(label)
        self.after(15, self.ProcessLiveTick)

    def _TriggerSortingRoutine(self, label: str):
        # find ID by class name or assume label is ID
        # Since onnx outputs ID directly as string right now, we use it directly:
        gate_idx = self.project.gate_assignments.get(str(label))
        if gate_idx is None:
            return

        gate_config = next((g for g in self.project.gates if g.idx == gate_idx), None)
        if not gate_config:
            return

        if not self.conveyor_fsm.lock_for_processing():
            return

        payload = {
            "gate_idx": gate_config.idx,
            "lead_time": gate_config.lead_time,
            "active_time": gate_config.active_time,
        }
        success = self.serial_mgr.send_payload(payload)

        if success:
            total_lock_time_ms = int(
                (gate_config.lead_time + gate_config.active_time) * 1000
            )
            self.after(total_lock_time_ms, self.conveyor_fsm.release_lock)
        else:
            self.conveyor_fsm.set_error()
            self.write_debug_console("Hardware Communication Failure")

    # --- CONSOLE TAB ---
    def build_console_tab(self):
        self.sys_console = ctk.CTkTextbox(
            self.tab_console,
            fg_color="#1e1e1e",
            text_color="#00ff00",
            font=("Consolas", 12),
        )
        self.sys_console.pack(fill="both", expand=True, padx=10, pady=10)
        print("System Logs initialized.")


if __name__ == "__main__":
    app = LegoStudioApp()
    app.mainloop()
