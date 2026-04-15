import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import json
from pathlib import Path

class LegoCatalogViewer:
    def __init__(self, window):
        self.window = window
        self.window.title("LEGO Studio - URU Robotics Project")
        self.window.geometry("1150x850") # Widened to fit the sidebar comfortably
        self.window.configure(bg="#f5f5f5")

        # Path Configuration (pointing to parent folder data)
        self.base_dir = Path(__file__).resolve().parent.parent if Path(__file__).parent.name == "tools" else Path(__file__).resolve().parent
        self.data_dir = self.base_dir.parent / "data" 
        self.metadata_path = self.data_dir / "catalog.json"
        self.previews_dir = self.data_dir / "previews"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.data = {}
        self.ids = []
        self.selected_ids = set() 
        self.current_index = 0
        self.sidebar_images = [] # Prevents Python from garbage-collecting sidebar thumbnails
        
        self.load_data()
        self.setup_ui()
        self.update_display()

        # Keyboard shortcuts
        self.window.bind("<Left>", lambda e: self.prev_img())
        self.window.bind("<Right>", lambda e: self.next_img())
        self.window.bind("<space>", lambda e: self.toggle_selection())
        self.window.bind("<Return>", lambda e: self.search_item())

    def load_data(self):
        if not self.metadata_path.exists():
            messagebox.showerror("Error", f"Could not find {self.metadata_path.name}\nPlease run the extractor first.")
            self.window.destroy()
            return
        
        try:
            with open(self.metadata_path, "r") as f:
                self.data = json.load(f)
            self.ids = sorted([int(k) for k in self.data.keys()])
        except Exception as e:
            messagebox.showerror("File Error", f"Failed to parse catalog: {e}")
            self.window.destroy()

    def setup_ui(self):
        # Master layout: split left and right
        self.left_panel = ttk.Frame(self.window, padding="20")
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_panel = tk.Frame(self.window, bg="#ecf0f1", width=350)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_panel.pack_propagate(False) # Force width

        self.setup_left_panel()
        self.setup_right_panel()

    def setup_left_panel(self):
        # Header
        header_frame = ttk.Frame(self.left_panel)
        header_frame.pack(fill=tk.X)
        self.counter_label = ttk.Label(header_frame, text="", font=("Helvetica", 10))
        self.counter_label.pack(side=tk.LEFT)

        # Image Display
        self.canvas_frame = tk.Frame(self.left_panel, bg="white", highlightbackground="#cccccc", highlightthickness=1)
        self.canvas_frame.pack(pady=10)
        self.img_label = tk.Label(self.canvas_frame, bg="white")
        self.img_label.pack(padx=10, pady=10)

        # Info & Selection Controls
        self.id_label = ttk.Label(self.left_panel, font=("Helvetica", 18, "bold"), foreground="#2c3e50")
        self.id_label.pack()
        self.name_label = ttk.Label(self.left_panel, font=("Helvetica", 12), foreground="#7f8c8d")
        self.name_label.pack(pady=5)

        self.btn_select = tk.Button(
            self.left_panel, text="SELECT (Space)", font=("Helvetica", 12, "bold"),
            command=self.toggle_selection, height=2, width=25, relief=tk.FLAT, cursor="hand2"
        )
        self.btn_select.pack(pady=10)

        # Navigation & Unified Search
        nav_frame = ttk.Frame(self.left_panel)
        nav_frame.pack(pady=10)
        ttk.Button(nav_frame, text="❮ Previous", command=self.prev_img).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(nav_frame, text="Search:", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(15, 2))
        self.entry_search = ttk.Entry(nav_frame, width=15, font=("Helvetica", 12), justify="center")
        self.entry_search.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(nav_frame, text="Jump", command=self.search_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="Next ❯", command=self.next_img).pack(side=tk.LEFT, padx=15)

        # --- File Management Section ---
        ttk.Separator(self.left_panel, orient='horizontal').pack(fill='x', pady=20)
        
        file_frame = tk.Frame(self.left_panel, bg="#f5f5f5")
        file_frame.pack(fill=tk.X, pady=5)

        self.btn_load = tk.Button(
            file_frame, text="📁 LOAD JSON", command=self.load_project,
            bg="#9b59b6", fg="white", font=("Helvetica", 10, "bold"), pady=8, padx=15, relief=tk.FLAT, cursor="hand2"
        )
        self.btn_load.pack(side=tk.LEFT, padx=5)

        name_frame = tk.Frame(file_frame, bg="#f5f5f5")
        name_frame.pack(side=tk.LEFT, expand=True)
        ttk.Label(name_frame, text="Project Name:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.project_name_entry = ttk.Entry(name_frame, width=20, font=("Helvetica", 11), justify="center")
        self.project_name_entry.insert(0, "lego_classifier") 
        self.project_name_entry.pack(side=tk.LEFT, padx=5)

        self.btn_export = tk.Button(
            file_frame, text="💾 SAVE JSON", command=self.export_selected,
            bg="#3498db", fg="white", font=("Helvetica", 10, "bold"), pady=8, padx=15, relief=tk.FLAT, cursor="hand2"
        )
        self.btn_export.pack(side=tk.RIGHT, padx=5)

    def setup_right_panel(self):
        # Sidebar Header
        self.sidebar_title = tk.Label(self.right_panel, text="Selected Pieces (0)", font=("Helvetica", 14, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.sidebar_title.pack(pady=15)

        # Scrollable area for selected items
        self.sidebar_canvas = tk.Canvas(self.right_panel, bg="#ecf0f1", highlightthickness=0)
        self.sidebar_scrollbar = ttk.Scrollbar(self.right_panel, orient="vertical", command=self.sidebar_canvas.yview)
        
        self.sidebar_inner = tk.Frame(self.sidebar_canvas, bg="#ecf0f1")
        self.sidebar_inner.bind("<Configure>", lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))

        self.sidebar_canvas.create_window((0, 0), window=self.sidebar_inner, anchor="nw", width=330)
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scrollbar.set)

        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        self.sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # Enable mouse scroll for the sidebar
        self.sidebar_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def load_project(self):
        filepath = filedialog.askopenfilename(
            initialdir=self.data_dir,
            title="Select Configuration JSON",
            filetypes=[("JSON files", "*.json")]
        )

        if not filepath:
            return

        try:
            with open(filepath, "r") as f:
                config = json.load(f)

            raw_ids = config.get("selected_ids", [])
            self.selected_ids = set([int(x) for x in raw_ids])
            
            project_name = config.get("project_name", Path(filepath).stem)
            self.project_name_entry.delete(0, tk.END)
            self.project_name_entry.insert(0, project_name)

            self.update_display()
            self.refresh_sidebar()
            messagebox.showinfo("Project Loaded", f"Successfully loaded '{project_name}'\nRestored {len(self.selected_ids)} selected classes.")

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load configuration:\n{e}")

    def search_item(self):
        query = self.entry_search.get().strip().lower()
        if not query:
            return

        try:
            target_id = int(query)
            if target_id in self.ids:
                self.current_index = self.ids.index(target_id)
                self.update_display()
                self.entry_search.delete(0, tk.END)
                return
        except ValueError:
            pass 

        for i, label_id in enumerate(self.ids):
            item_name = self.data[str(label_id)]["name"].lower()
            if query in item_name:
                self.current_index = i
                self.update_display()
                self.entry_search.delete(0, tk.END)
                return

        messagebox.showinfo("Not Found", f"Could not find any ID or piece matching:\n'{query}'")

    def toggle_selection(self):
        current_id = self.ids[self.current_index]
        if current_id in self.selected_ids:
            self.selected_ids.remove(current_id)
        else:
            self.selected_ids.add(current_id)
            
        self.update_display()
        self.refresh_sidebar() # Update the right panel instantly

    def remove_from_sidebar(self, target_id):
        # Function to handle clicking the 'X' in the sidebar
        if target_id in self.selected_ids:
            self.selected_ids.remove(target_id)
            self.refresh_sidebar()
            self.update_display() # Updates main viewer if we removed the piece currently on screen

    def refresh_sidebar(self):
        # 1. Clear current sidebar contents
        for widget in self.sidebar_inner.winfo_children():
            widget.destroy()
        self.sidebar_images.clear()

        # 2. Update Header
        self.sidebar_title.config(text=f"Selected Pieces ({len(self.selected_ids)})")

        # 3. Populate selected items
        for sid in sorted(list(self.selected_ids)):
            item = self.data.get(str(sid))
            if not item: continue
            
            img_path = self.previews_dir / item["image_path"]

            row = tk.Frame(self.sidebar_inner, bg="white", highlightbackground="#bdc3c7", highlightthickness=1)
            row.pack(fill=tk.X, pady=4)

            # Thumbnail
            if img_path.exists():
                try:
                    img = Image.open(img_path).resize((50, 50), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img)
                    self.sidebar_images.append(img_tk)
                    tk.Label(row, image=img_tk, bg="white").pack(side=tk.LEFT, padx=5, pady=5)
                except Exception:
                    pass

            # Text Info
            text_frame = tk.Frame(row, bg="white")
            text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            tk.Label(text_frame, text=f"ID: {sid}", font=("Helvetica", 9, "bold"), bg="white", anchor="w").pack(fill=tk.X)
            tk.Label(text_frame, text=item["name"], font=("Helvetica", 8), fg="#7f8c8d", bg="white", anchor="w", wraplength=180).pack(fill=tk.X)

            # Quick Remove Button
            btn_remove = tk.Button(row, text="✖", fg="#c0392b", bg="white", font=("Helvetica", 10, "bold"), 
                                   relief=tk.FLAT, cursor="hand2", command=lambda id=sid: self.remove_from_sidebar(id))
            btn_remove.pack(side=tk.RIGHT, padx=10)

    def update_display(self):
        if not self.ids: return
        label_id = self.ids[self.current_index]
        item = self.data[str(label_id)]
        img_path = self.previews_dir / item["image_path"]
        
        if img_path.exists():
            img = Image.open(img_path).resize((400, 400), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)
            self.img_label.configure(image=img_tk)
            self.img_label.image = img_tk
        
        self.id_label.configure(text=f"LABEL ID: {label_id}")
        self.name_label.configure(text=item["name"])
        self.counter_label.config(text=f"Item {self.current_index + 1} of {len(self.ids)}")

        if label_id in self.selected_ids:
            self.btn_select.config(text="✓ SELECTED", bg="#2ecc71", fg="white")
            self.canvas_frame.config(highlightbackground="#2ecc71", highlightthickness=3)
        else:
            self.btn_select.config(text="SELECT (Space)", bg="#ecf0f1", fg="black")
            self.canvas_frame.config(highlightbackground="#cccccc", highlightthickness=1)

    def next_img(self):
        self.current_index = (self.current_index + 1) % len(self.ids)
        self.update_display()

    def prev_img(self):
        self.current_index = (self.current_index - 1) % len(self.ids)
        self.update_display()

    def export_selected(self):
        if not self.selected_ids:
            messagebox.showwarning("Warning", "No pieces have been selected.")
            return

        project_name = self.project_name_entry.get().strip().replace(" ", "_")
        if not project_name:
            messagebox.showwarning("Warning", "Please enter a project name.")
            return

        export_path = self.data_dir / f"{project_name}.json"

        selected_list = sorted(list(self.selected_ids))
        export_data = {
            "project_name": project_name,
            "selected_ids": selected_list,
            "classes": {str(sid): self.data[str(sid)]["name"] for sid in selected_list}
        }
        
        try:
            with open(export_path, "w") as f:
                json.dump(export_data, f, indent=4)
            messagebox.showinfo("Success", f"Saved configuration to:\n{export_path.name}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LegoCatalogViewer(root)
    root.mainloop()