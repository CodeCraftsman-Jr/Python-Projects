import os
import shutil
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
from datetime import datetime
from tkinter.font import Font
import json
from typing import Dict, List
import re

class ModernButton(tk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            relief="flat",
            background="#2196F3",
            foreground="white",
            activebackground="#1976D2",
            activeforeground="white",
            borderwidth=0,
            padx=20,
            pady=10,
            cursor="hand2",
            font=("Segoe UI", 10)
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self.configure(background="#1976D2")

    def on_leave(self, e):
        self.configure(background="#2196F3")

class FolderOperation:
    def __init__(self, source: str, target: str, operation_type: str):
        self.source = source
        self.target = target
        self.operation_type = operation_type  # 'rename' or 'merge'
        self.timestamp = datetime.now()

class FolderRenamerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Folder Renamer")
        self.root.geometry("1100x800")
        self.root.configure(bg="#F5F5F5")
        
        # Initialize variables
        self.selected_folder = None
        self.operations_history: List[FolderOperation] = []
        self.preview_changes: Dict[str, str] = {}
        
        # Configure fonts
        self.title_font = Font(family="Segoe UI", size=16, weight="bold")
        self.normal_font = Font(family="Segoe UI", size=10)
        self.log_font = Font(family="Consolas", size=9)
        
        # Create main frame
        self.main_frame = tk.Frame(root, bg="#F5F5F5")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create and pack widgets
        self.create_widgets()
        
        # Set up logging
        self.setup_logging()
        
        # Load settings
        self.load_settings()

    def create_widgets(self):
        # Title and description
        self.create_header()
        
        # Create left and right panels
        left_panel = tk.Frame(self.main_frame, bg="#F5F5F5")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_panel = tk.Frame(self.main_frame, bg="#F5F5F5")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Left panel contents
        self.create_folder_selection(left_panel)
        self.create_operation_modes(left_panel)
        self.create_advanced_options(left_panel)
        
        # Right panel contents
        self.create_preview_section(right_panel)
        self.create_log_section(right_panel)

    def create_header(self):
        title_label = tk.Label(
            self.main_frame,
            text="Advanced Folder Renamer",
            font=self.title_font,
            bg="#F5F5F5",
            fg="#1565C0"
        )
        title_label.pack(pady=(0, 5))

        desc_label = tk.Label(
            self.main_frame,
            text="Rename and organize folders with advanced options",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#666666"
        )
        desc_label.pack(pady=(0, 20))

    def create_folder_selection(self, parent):
        folder_frame = tk.LabelFrame(
            parent,
            text="Folder Selection",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#333333",
            padx=10,
            pady=10
        )
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.folder_label = tk.Label(
            folder_frame,
            text="Selected Folder: None",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#333333",
            anchor="w"
        )
        self.folder_label.pack(fill=tk.X)
        
        button_frame = tk.Frame(folder_frame, bg="#F5F5F5")
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.select_button = ModernButton(
            button_frame,
            text="Select Folder",
            command=self.select_folder
        )
        self.select_button.pack(side=tk.LEFT, padx=5)
        
        self.refresh_button = ModernButton(
            button_frame,
            text="Refresh",
            command=self.refresh_preview
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)

    def create_operation_modes(self, parent):
        modes_frame = tk.LabelFrame(
            parent,
            text="Operation Mode",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#333333",
            padx=10,
            pady=10
        )
        modes_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Text to remove
        tk.Label(
            modes_frame,
            text="Text to Remove:",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#333333"
        ).pack(anchor=tk.W)
        
        self.remove_text = tk.Entry(
            modes_frame,
            font=self.normal_font
        )
        self.remove_text.pack(fill=tk.X, pady=(0, 10))
        
        # Operation modes
        self.operation_mode = tk.StringVar(value="smart")
        modes = [
            ("Smart Remove (Auto-detect patterns)", "smart"),
            ("Exact Text Match", "exact"),
            ("Regular Expression", "regex")
        ]
        
        for text, mode in modes:
            tk.Radiobutton(
                modes_frame,
                text=text,
                variable=self.operation_mode,
                value=mode,
                font=self.normal_font,
                bg="#F5F5F5",
                command=self.refresh_preview
            ).pack(anchor=tk.W)

    def create_advanced_options(self, parent):
        options_frame = tk.LabelFrame(
            parent,
            text="Advanced Options",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#333333",
            padx=10,
            pady=10
        )
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Checkboxes for various options
        self.recursive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            options_frame,
            text="Process Subfolders",
            variable=self.recursive_var,
            font=self.normal_font,
            bg="#F5F5F5",
            command=self.refresh_preview
        ).pack(anchor=tk.W)
        
        self.merge_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Merge Existing Folders",
            variable=self.merge_var,
            font=self.normal_font,
            bg="#F5F5F5",
            command=self.refresh_preview
        ).pack(anchor=tk.W)
        
        self.backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Create Backup",
            variable=self.backup_var,
            font=self.normal_font,
            bg="#F5F5F5"
        ).pack(anchor=tk.W)
        
        # Action buttons
        button_frame = tk.Frame(options_frame, bg="#F5F5F5")
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.process_button = ModernButton(
            button_frame,
            text="Apply Changes",
            command=self.start_processing
        )
        self.process_button.pack(side=tk.LEFT, padx=5)
        
        self.undo_button = ModernButton(
            button_frame,
            text="Undo Last",
            command=self.undo_last_operation
        )
        self.undo_button.pack(side=tk.LEFT, padx=5)
        self.undo_button.configure(state='disabled')

    def create_preview_section(self, parent):
        preview_frame = tk.LabelFrame(
            parent,
            text="Preview Changes",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#333333",
            padx=10,
            pady=10
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Preview tree
        self.preview_tree = ttk.Treeview(
            preview_frame,
            columns=("Current Name", "New Name"),
            show="headings",
            selectmode="browse"
        )
        
        self.preview_tree.heading("Current Name", text="Current Name")
        self.preview_tree.heading("New Name", text="New Name")
        
        # Scrollbar for preview
        preview_scroll = ttk.Scrollbar(
            preview_frame,
            orient="vertical",
            command=self.preview_tree.yview
        )
        self.preview_tree.configure(yscrollcommand=preview_scroll.set)
        
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def create_log_section(self, parent):
        log_frame = tk.LabelFrame(
            parent,
            text="Activity Log",
            font=self.normal_font,
            bg="#F5F5F5",
            fg="#333333",
            padx=10,
            pady=10
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_display = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            wrap=tk.WORD,
            font=self.log_font,
            background='white',
            borderwidth=0,
            relief="flat"
        )
        self.log_display.pack(fill=tk.BOTH, expand=True)
        self.log_display.configure(state='disabled')
        
        # Configure log display tags
        self.log_display.tag_configure('error', foreground='#D32F2F')
        self.log_display.tag_configure('info', foreground='#1565C0')
        self.log_display.tag_configure('success', foreground='#2E7D32')

    def select_folder(self):
        selected = filedialog.askdirectory()
        if selected:
            self.selected_folder = selected
            self.folder_label.config(text=f"Selected Folder: {selected}")
            logging.info(f"Selected folder: {selected}")
            self.refresh_preview()

    def refresh_preview(self):
        if not self.selected_folder:
            return
            
        # Clear preview
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
            
        try:
            # Get list of folders
            base_path = Path(self.selected_folder)
            folders = [base_path] if not self.recursive_var.get() else list(base_path.rglob("*"))
            folders = [f for f in folders if f.is_dir()]
            
            self.preview_changes.clear()
            
            for folder in folders:
                current_name = folder.name
                new_name = self.get_new_name(current_name)
                
                if new_name != current_name:
                    self.preview_changes[str(folder)] = new_name
                    self.preview_tree.insert(
                        "",
                        "end",
                        values=(current_name, new_name)
                    )
            
            logging.info(f"Found {len(self.preview_changes)} folders to rename")
            
        except Exception as e:
            logging.error(f"Error generating preview: {e}")

    def get_new_name(self, current_name: str) -> str:
        remove_text = self.remove_text.get().strip()
        if not remove_text:
            return current_name
            
        mode = self.operation_mode.get()
        
        if mode == "exact":
            return current_name.replace(remove_text, "").strip()
        elif mode == "regex":
            try:
                return re.sub(remove_text, "", current_name).strip()
            except re.error:
                return current_name
        else:  # smart mode
            # Remove text with surrounding spaces and hyphens
            pattern = f"[-\\s]*{re.escape(remove_text)}[-\\s]*"
            return re.sub(pattern, " ", current_name).strip()

    def start_processing(self):
        if not self.preview_changes:
            logging.error("No changes to apply!")
            return
            
        # Disable buttons
        self.process_button.configure(state='disabled')
        self.select_button.configure(state='disabled')
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self.process_folders_thread)
        thread.daemon = True
        thread.start()

    def process_folders_thread(self):
        try:
            # Create backup if requested
            if self.backup_var.get():
                self.create_backup()
            
            # Process each folder
            for source_path_str, new_name in self.preview_changes.items():
                source_path = Path(source_path_str)
                target_path = source_path.parent / new_name
                
                if target_path.exists() and self.merge_var.get():
                    # Merge folders
                    self.merge_folders(source_path, target_path)
                    operation = FolderOperation(str(source_path), str(target_path), 'merge')
                else:
                    # Rename folder
                    source_path.rename(target_path)
                    operation = FolderOperation(str(source_path), str(target_path), 'rename')
                
                self.operations_history.append(operation)
                logging.info(f"Processed folder: {source_path.name} → {new_name}")
            
            logging.info("Processing completed successfully!")
            self.root.after(0, self.enable_undo)
            
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            self.root.after(0, self.enable_buttons)
            self.refresh_preview()

    def create_backup(self):
        try:
            backup_dir = Path(self.selected_folder).parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(self.selected_folder, backup_dir)
            logging.info(f"Created backup at: {backup_dir}")
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")

    def merge_folders(self, source: Path, target: Path):
        target.mkdir(parents=True, exist_ok=True)
        
        for item in source.glob('*'):
            destination = target / item.name
            if item.is_file():
                if not destination.exists():
                    shutil.copy2(item, destination)
            elif item.is_dir():
                self.merge_folders(item, destination)
        
        shutil.rmtree(source)

    def undo_last_operation(self):
        if not self.operations_history:
            return
            
        operation = self.operations_history.pop()
        try:
            if operation.operation_type == 'rename':
                # Simple rename back
                Path(operation.target).rename(operation.source)
            elif operation.operation_type == 'merge':
                # For merge operations, we can't undo (would need backup)
                logging.error("Cannot undo merge operation - please restore from backup")
                
            logging.info(f"Undid last operation: {operation.target} → {operation.source}")
            
            if not self.operations_history:
                self.undo_button.configure(state='disabled')
                
            self.refresh_preview()
            
        except Exception as e:
            logging.error(f"Failed to undo operation: {e}")

    def enable_undo(self):
        self.undo_button.configure(state='normal')

    def enable_buttons(self):
        self.process_button.configure(state='normal')
        self.select_button.configure(state='normal')

    def load_settings(self):
        try:
            if Path("folder_renamer_settings.json").exists():
                with open("folder_renamer_settings.json", "r") as f:
                    settings = json.load(f)
                    self.remove_text.insert(0, settings.get("last_remove_text", ""))
                    self.operation_mode.set(settings.get("operation_mode", "smart"))
                    self.recursive_var.set(settings.get("recursive", False))
                    self.merge_var.set(settings.get("merge", True))
                    self.backup_var.set(settings.get("backup", True))
        except Exception:
            pass

    def save_settings(self):
        try:
            settings = {
                "last_remove_text": self.remove_text.get(),
                "operation_mode": self.operation_mode.get(),
                "recursive": self.recursive_var.get(),
                "merge": self.merge_var.get(),
                "backup": self.backup_var.get()
            }
            with open("folder_renamer_settings.json", "w") as f:
                json.dump(settings, f)
        except Exception:
            pass

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add GUI handler
        text_handler = TextHandler(self.log_display)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logger.addHandler(text_handler)
        
        # Add file handler
        log_file = f"folder_renamer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logger.addHandler(file_handler)

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            if "error" in record.levelname.lower():
                self.text_widget.insert(tk.END, msg + '\n', 'error')
            elif "info" in record.levelname.lower():
                self.text_widget.insert(tk.END, msg + '\n', 'info')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderRenamerGUI(root)
    root.mainloop()
    app.save_settings()
