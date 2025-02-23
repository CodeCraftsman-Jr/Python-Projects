import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import logging
import queue
import threading
import time
from datetime import datetime, timedelta
import shutil
import google.generativeai as genai
import config
import enum
import re  # Add this for regex operations
import requests  # Add this for API requests
from googlesearch import search  # Add this for Google search
import openai  # Add this for OpenAI
import cohere  # Add this for Cohere
from anthropic import Anthropic  # Add this for Anthropic

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add these constants that are referenced but not defined
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"
GEMINI_API_KEYS = config.GEMINI_API_KEYS  # Using the correct variable name from config.py

class ServiceStatus(enum.Enum):
    WORKING = "working"
    FAILED = "failed"
    NOT_CONFIGURED = "not_configured"

class APIService:
    def __init__(self, name, enabled=True):
        self.name = name
        self.enabled = enabled
        self.status = ServiceStatus.NOT_CONFIGURED
        self.error_message = ""
        self.status_label = None  # Will be set later by the GUI
        self._test_timeout = 10  # 10 seconds timeout for API tests

class PluginCategorizerGUI:
    """GUI for categorizing plugins using AI."""

    # Standard categories for plugins
    STANDARD_CATEGORIES = [
        "Admin Tools",
        "Analytics",
        "Authentication",
        "Backup",
        "Blogging",
        "Cache",
        "Contact Forms",
        "Content Management",
        "E-commerce",
        "Editor",
        "Email Marketing",
        "Forms",
        "Gallery",
        "Image Optimization",
        "Maintenance",
        "Media",
        "Membership",
        "Multilingual",
        "Page Builder",
        "Performance",
        "Security",
        "SEO",
        "Social Media",
        "Spam Protection",
        "Theme Tools",
        "WooCommerce",
        "Other"
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("WordPress Plugin Categorizer")
        self.root.geometry("1200x800")
        
        # Initialize processing state
        self.is_processing = False
        self.processed_files = 0
        self.total_files = 0
        
        # Initialize statistics
        self.stats = {
            'total_processed': 0,
            'successful_moves': 0,
            'failed_moves': 0,
            'categories_used': {},
            'api_usage': {'gemini': 0}
        }
        
        # Initialize variables first
        self._initialize_variables()
        
        # Initialize message queue for thread-safe UI updates
        self.message_queue = queue.Queue()
        
        # Initialize API services
        self.api_services = {
            'gemini': APIService('Gemini API'),
            'openai': APIService('OpenAI API'),
            'cohere': APIService('Cohere API'),
            'anthropic': APIService('Anthropic API'),
            'google_search': APIService('Google Search')
        }
        
        # Set initial API status
        for service in self.api_services.values():
            service.status = ServiceStatus.NOT_CONFIGURED
        
        # Configure style
        self._configure_style()
        
        # Create main notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.process_tab = ttk.Frame(self.notebook)
        self.status_tab = ttk.Frame(self.notebook)
        self.stats_tab = ttk.Frame(self.notebook)
        self.logs_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.cleanup_tab = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.setup_tab, text="Setup & API Status")
        self.notebook.add(self.process_tab, text="Process Plugins")
        self.notebook.add(self.status_tab, text="File Move Status2")
        self.notebook.add(self.stats_tab, text="Statistics")
        self.notebook.add(self.logs_tab, text="Logs")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.cleanup_tab, text="Cleanup")
        
        # Initialize tab contents
        self._initialize_setup_tab()
        self._initialize_process_tab()
        self._create_file_move_status_frame()
        self._initialize_stats_tab()
        self._initialize_logs_tab()
        self._initialize_settings_tab()
        self._initialize_cleanup_tab()
        
        # Apply initial theme
        self._apply_theme()
        
        # Start message processing
        self.process_messages()

    def process_messages(self):
        """Process messages from the queue and update UI."""
        try:
            while True:
                message = self.message_queue.get_nowait()
                action = message.get('action')
                
                if action == 'update_label':
                    label = message['label']
                    text = message['text']
                    style = message.get('style')
                    if style:
                        label.config(text=text, style=style)
                    else:
                        label.config(text=text)
                        
                elif action == 'update_test_status':
                    self.test_status_label.config(text=message['text'])
                    
                elif action == 'enable_button':
                    button = message['button']
                    button.config(state=message['state'])
                    
                elif action == 'update_current_file':
                    self.current_file_label.config(text=message['text'])
                    
                elif action == 'update_status':
                    self.status_label.config(text=message['text'])
                    
                elif action == 'update_progress':
                    value = message['value']
                    self.progress_var.set(value)
                    self.progress_label.config(text=f"{int(value)}%")
                    
                elif action == 'update_elapsed_time':
                    elapsed = message['elapsed']
                    hours = int(elapsed // 3600)
                    minutes = int((elapsed % 3600) // 60)
                    seconds = int(elapsed % 60)
                    self.elapsed_time.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                    
                elif action == 'update_estimated_time':
                    estimated = message['estimated']
                    hours = int(estimated // 3600)
                    minutes = int((estimated % 3600) // 60)
                    seconds = int(estimated % 60)
                    self.estimated_time.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                    
                elif action == 'update_completion_time':
                    self.completion_time.set(message['completion'])
                    
                elif action == 'add_log':
                    text = message['text']
                    error = message.get('error', False)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    formatted_message = f"[{timestamp}] {text}\n"
                    tag = "error" if error else "success"
                    color = "red" if error else "green"
                    
                    self.log_text.insert(tk.END, formatted_message, tag)
                    if tag not in self.log_text.tag_names():
                        self.log_text.tag_configure(tag, foreground=color)
                    self.log_text.see(tk.END)
                    self.log_text.update_idletasks()
                    
                elif action == 'update_stats':
                    stats = message['stats']
                    self.stats_labels['total'].config(text=f"Total Processed: {stats['total']}")
                    self.stats_labels['success'].config(text=f"Successfully Categorized: {stats['success']}")
                    self.stats_labels['failed'].config(text=f"Failed to Categorize: {stats['failed']}")
                
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.root.after(100, self.process_messages)
    
    def queue_message(self, **kwargs):
        """Add a message to the queue."""
        self.message_queue.put(kwargs)

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 10))
        style.configure('TButton', font=('Helvetica', 10))
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        
        # Configure service status styles
        style.configure('Working.TLabel', foreground='green')
        style.configure('Failed.TLabel', foreground='red')
        style.configure('NotConfigured.TLabel', foreground='gray')

    def _initialize_setup_tab(self):
        """Initialize the Setup & API Status tab."""
        # Create main container
        main_frame = ttk.Frame(self.setup_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(main_frame, text="API Services Configuration", style='Header.TLabel')
        header.pack(pady=(0, 20))
        
        # Create services frame
        services_frame = ttk.LabelFrame(main_frame, text="Available Services", padding=15)
        services_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Add service toggles and status indicators
        for service in self.api_services.values():
            service_frame = ttk.Frame(services_frame)
            service_frame.pack(fill=tk.X, pady=5)
            
            # Service toggle
            toggle_var = tk.BooleanVar(value=service.enabled)
            toggle = ttk.Checkbutton(service_frame, text=service.name, 
                                   variable=toggle_var,
                                   command=lambda s=service, v=toggle_var: self._toggle_service(s, v))
            toggle.pack(side=tk.LEFT)
            
            # Status indicator
            status_label = ttk.Label(service_frame, text="Not Configured", style='NotConfigured.TLabel')
            status_label.pack(side=tk.RIGHT)
            service.status_label = status_label
        
        # Add test button and instructions
        test_frame = ttk.Frame(main_frame)
        test_frame.pack(fill=tk.X, pady=20)
        
        # Add instructions
        instructions = ttk.Label(test_frame, 
                               text="Click 'Test APIs' to verify your API configurations.",
                               wraplength=400)
        instructions.pack(side=tk.LEFT, pady=(0, 10))
        
        self.test_status_label = ttk.Label(test_frame, text="")
        self.test_status_label.pack(side=tk.LEFT, padx=10)
        
        self.test_button = ttk.Button(test_frame, text="Test APIs", 
                  command=self._async_test_api_keys)
        self.test_button.pack(side=tk.RIGHT)

    def _initialize_process_tab(self):
        """Initialize the Process Plugins tab."""
        # Create main container
        main_frame = ttk.Frame(self.process_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Directory selection section
        dir_frame = ttk.LabelFrame(main_frame, text="Directory Selection", padding=15)
        dir_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(dir_frame, text="Source Directory:").pack(fill=tk.X)
        source_frame = ttk.Frame(dir_frame)
        source_frame.pack(fill=tk.X, pady=5)
        
        self.source_dir = tk.StringVar()
        ttk.Entry(source_frame, textvariable=self.source_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(source_frame, text="Browse", 
                  command=lambda: self._browse_directory('source')).pack(side=tk.RIGHT)
        
        ttk.Label(dir_frame, text="Target Directory:").pack(fill=tk.X)
        target_frame = ttk.Frame(dir_frame)
        target_frame.pack(fill=tk.X, pady=5)
        
        self.target_dir = tk.StringVar()
        ttk.Entry(target_frame, textvariable=self.target_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(target_frame, text="Browse", 
                  command=lambda: self._browse_directory('target')).pack(side=tk.RIGHT)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding=15)
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack()
        
        self.current_file_label = ttk.Label(progress_frame, text="")
        self.current_file_label.pack()
        
        self.time_label = ttk.Label(progress_frame, text="")
        self.time_label.pack()
        
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack()
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=20)
        
        self.start_button = ttk.Button(control_frame, text="Start Processing", 
                                     command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop", 
                                    command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def _create_file_move_status_frame(self):
        """Create the file move status frame."""
        frame = ttk.LabelFrame(self.notebook, text="File Move Status", padding=10)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create scrollbar first
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create text widget
        self.status_text = tk.Text(text_frame, wrap=tk.WORD, height=10, width=50)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure text widget
        self.status_text.configure(
            font=('Consolas', 10),
            background='white',
            foreground='black',
            padx=5,
            pady=5
        )

        # Configure tags for different message types
        self.status_text.tag_configure('error', foreground='red')
        self.status_text.tag_configure('success', foreground='green')

        # Link scrollbar to text widget
        scrollbar.config(command=self.status_text.yview)
        self.status_text.config(yscrollcommand=scrollbar.set)

        # Add initial message
        self.status_text.insert(tk.END, "Ready to process plugins...\n")
        self.status_text.see(tk.END)
        
        # Add button to show last move status
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Show Last Move Status", 
                  command=self._show_last_move_status).pack(side=tk.LEFT, padx=5)
        
        self.notebook.add(frame, text='File Move Status')

    def _initialize_logs_tab(self):
        """Initialize the Logs tab."""
        # Create main container
        main_frame = ttk.Frame(self.logs_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create log viewer
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Add log controls
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(control_frame, text="Clear Logs", 
                  command=self._clear_logs).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Save Logs", 
                  command=self._save_logs).pack(side=tk.LEFT, padx=5)

    def _initialize_settings_tab(self):
        """Initialize the Settings tab."""
        # Create main container
        main_frame = ttk.Frame(self.settings_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(main_frame, text="Application Settings", style='Header.TLabel')
        header.pack(pady=(0, 20))
        
        # Theme settings
        theme_frame = ttk.LabelFrame(main_frame, text="Theme", padding=15)
        theme_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Radiobutton(theme_frame, text="Light", value="light",
                       variable=self.theme_var,
                       command=self._apply_theme).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(theme_frame, text="Dark", value="dark",
                       variable=self.theme_var,
                       command=self._apply_theme).pack(side=tk.LEFT, padx=10)
        
        # Directory settings
        dir_frame = ttk.LabelFrame(main_frame, text="Default Directories", padding=15)
        dir_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Source directory
        source_frame = ttk.Frame(dir_frame)
        source_frame.pack(fill=tk.X, pady=5)
        ttk.Label(source_frame, text="Default Source:").pack(side=tk.LEFT)
        ttk.Entry(source_frame, textvariable=self.source_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(source_frame, text="Browse",
                  command=lambda: self._browse_directory('source')).pack(side=tk.RIGHT)
        
        # Target directory
        target_frame = ttk.Frame(dir_frame)
        target_frame.pack(fill=tk.X, pady=5)
        ttk.Label(target_frame, text="Default Target:").pack(side=tk.LEFT)
        ttk.Entry(target_frame, textvariable=self.target_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(target_frame, text="Browse",
                  command=lambda: self._browse_directory('target')).pack(side=tk.RIGHT)
        
        # Settings actions
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(actions_frame, text="Save Settings",
                  command=self._save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Export Settings",
                  command=self._export_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Import Settings",
                  command=self._import_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Reset to Default",
                  command=self._reset_settings).pack(side=tk.RIGHT)

    def _initialize_stats_tab(self):
        """Initialize the Statistics tab."""
        # Create main container
        main_frame = ttk.Frame(self.stats_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(main_frame, text="Processing Statistics", style='Header.TLabel')
        header.pack(pady=(0, 20))
        
        # Stats display
        stats_frame = ttk.LabelFrame(main_frame, text="Current Statistics", padding=15)
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Create labels for statistics
        self.stats_labels = {
            'total': ttk.Label(stats_frame, text="Total Processed: 0"),
            'success': ttk.Label(stats_frame, text="Successfully Categorized: 0"),
            'failed': ttk.Label(stats_frame, text="Failed to Categorize: 0"),
            'categories': ttk.Label(stats_frame, text="Categories Used: 0"),
            'api_usage': ttk.Label(stats_frame, text="API Calls Made: 0")
        }
        
        for label in self.stats_labels.values():
            label.pack(fill=tk.X, pady=2)
        
        # Add export button
        ttk.Button(main_frame, text="Export Statistics", 
                  command=self._export_stats).pack(pady=10)
    
    def _initialize_cleanup_tab(self):
        """Initialize the Cleanup tab."""
        # Create main container
        main_frame = ttk.Frame(self.cleanup_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(main_frame, text="Category Folder Cleanup", style='Header.TLabel')
        header.pack(pady=(0, 20))
        
        # Instructions
        instructions = ttk.Label(main_frame, text="This tool helps fix category folder names that are too long or incorrectly formatted.\n"
                               "It will normalize folder names to match standard categories.", wraplength=600)
        instructions.pack(pady=(0, 20))
        
        # Directory selection
        dir_frame = ttk.LabelFrame(main_frame, text="Target Directory", padding=15)
        dir_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Use the same target directory from main interface
        ttk.Label(dir_frame, text="Directory to clean:").pack(fill=tk.X)
        dir_entry = ttk.Entry(dir_frame, textvariable=self.target_dir)
        dir_entry.pack(fill=tk.X, pady=5)
        ttk.Button(dir_frame, text="Browse",
                  command=lambda: self._browse_directory('target')).pack(side=tk.RIGHT)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Changes Preview", padding=15)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Preview text widget
        self.cleanup_preview = scrolledtext.ScrolledText(preview_frame, height=10)
        self.cleanup_preview.pack(fill=tk.BOTH, expand=True)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.preview_button = ttk.Button(button_frame, text="Preview Changes",
                                       command=self._preview_cleanup)
        self.preview_button.pack(side=tk.LEFT, padx=5)
        
        self.apply_cleanup_button = ttk.Button(button_frame, text="Apply Changes",
                                             command=self._apply_cleanup)
        self.apply_cleanup_button.pack(side=tk.LEFT, padx=5)
        
        # Add status label
        self.cleanup_status_label = ttk.Label(main_frame, text="")
        self.cleanup_status_label.pack(pady=10)

    def _toggle_service(self, service, var):
        """Toggle a service on/off."""
        service.enabled = var.get()
        if service.enabled:
            self._async_test_api_keys()  # Retest APIs when enabling a service

    def _save_settings(self):
        """Save current settings."""
        settings = {
            'theme': self.theme_var.get(),
            'source_dir': self.source_dir.get(),
            'target_dir': self.target_dir.get(),
            'api_services': {name: service.enabled for name, service in self.api_services.items()}
        }
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def _export_settings(self):
        """Export settings to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="plugin_categorizer_settings.json"
        )
        
        if file_path:
            settings = {
                'theme': self.theme_var.get(),
                'source_dir': self.source_dir.get(),
                'target_dir': self.target_dir.get(),
                'api_services': {name: service.enabled for name, service in self.api_services.items()}
            }
            
            try:
                with open(file_path, 'w') as f:
                    json.dump(settings, f, indent=4)
                messagebox.showinfo("Success", "Settings exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export settings: {str(e)}")

    def _import_settings(self):
        """Import settings from a file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    settings = json.load(f)
                
                # Apply imported settings
                self.theme_var.set(settings.get('theme', 'light'))
                self.source_dir.set(settings.get('source_dir', ''))
                self.target_dir.set(settings.get('target_dir', ''))
                
                # Update API service states
                for name, enabled in settings.get('api_services', {}).items():
                    if name in self.api_services:
                        self.api_services[name].enabled = enabled
                
                self._apply_theme()
                messagebox.showinfo("Success", "Settings imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import settings: {str(e)}")

    def _reset_settings(self):
        """Reset settings to default values."""
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all settings to default?"):
            self.theme_var.set('light')
            self.source_dir.set('')
            self.target_dir.set('')
            for service in self.api_services.values():
                service.enabled = True
            self._apply_theme()
            messagebox.showinfo("Success", "Settings reset to default values!")

    def _clear_logs(self):
        """Clear the log viewer."""
        self.log_text.delete(1.0, tk.END)

    def _save_logs(self):
        """Save logs to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.log_text.get(1.0, tk.END))

    def _initialize_variables(self):
        """Initialize all variables used in the application."""
        # Theme variable
        self.theme_var = tk.StringVar(value="light")
        
        # Directory variables
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        
        # Progress tracking
        self.progress_var = tk.DoubleVar()
        self.current_file = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Time tracking
        self.elapsed_time = tk.StringVar(value="00:00:00")
        self.estimated_time = tk.StringVar(value="--:--:--")
        self.completion_time = tk.StringVar(value="--:--:--")
        
        # Processing state
        self.is_processing = False
        self.start_time = None
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful_moves': 0,
            'failed_moves': 0,
            'categories_used': {},
            'api_usage': {'gemini': 0}
        }
        
        # UI Labels dictionary
        self.stats_labels = {}
        
        # Initialize logging
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'plugin_categorizer.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        # API selection
        self.selected_api = tk.StringVar(value="Gemini")
        self.api_keys = {
            "Gemini": config.GEMINI_API_KEYS,
            "OpenAI": config.OPENAI_API_KEY,
            "Cohere": config.COHERE_API_KEY,
            "Anthropic": config.ANTHROPIC_API_KEY
        }

    def _async_test_api_keys(self):
        """Run API tests asynchronously to prevent GUI freezing."""
        self.queue_message(action='update_test_status', text="Testing APIs... Please wait...")
        self.test_button.config(state='disabled')
        threading.Thread(target=self.test_api_keys, daemon=True).start()

    def test_api_keys(self):
        """Test all API keys."""
        try:
            # Initialize API clients if not already done
            initialize_api_clients()
            
            # Update UI to show testing status
            self.queue_message(action='update_test_status', text="Testing API keys...")
            
            for service in self.api_services.values():
                if not service.enabled:
                    continue
                    
                # Update service status to testing
                self.queue_message(
                    action='update_label',
                    label=service.status_label,
                    text="Testing...",
                    style='Testing.TLabel'
                )
                
                try:
                    # Test the API key with timeout handling
                    if service.name == 'Gemini API':
                        if not config.GEMINI_API_KEYS or not config.GEMINI_API_KEYS[0]:
                            raise ValueError("Gemini API key not configured")
                        
                        # Use direct HTTP request with timeout for testing
                        response = requests.post(
                            GEMINI_API_URL,
                            headers={
                                'Content-Type': 'application/json',
                                'x-goog-api-key': config.GEMINI_API_KEYS[0]
                            },
                            json={
                                "contents": [{"parts": [{"text": "Test"}]}],
                                "generationConfig": {
                                    "temperature": 0.1,
                                    "maxOutputTokens": 1
                                }
                            },
                            timeout=self.api_services['gemini']._test_timeout
                        )
                        
                        if response.status_code != 200:
                            raise Exception(f"API returned status code: {response.status_code}")
                    
                    elif service.name == 'OpenAI API':
                        if not config.OPENAI_API_KEY:
                            raise ValueError("OpenAI API key not configured")
                        response = openai.Completion.create(
                            model="gpt-3.5-turbo-instruct",
                            prompt="Test",
                            max_tokens=1,
                            timeout=self.api_services['openai']._test_timeout
                        )
                        
                    elif service.name == 'Cohere API':
                        if not config.COHERE_API_KEY:
                            raise ValueError("Cohere API key not configured")
                        co = cohere.Client(config.COHERE_API_KEY)
                        response = co.generate(prompt='Test', max_tokens=1)
                        
                    elif service.name == 'Anthropic API':
                        if not config.ANTHROPIC_API_KEY:
                            raise ValueError("Anthropic API key not configured")
                        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                        response = client.messages.create(
                            model="claude-2",
                            max_tokens=1,
                            messages=[{"role": "user", "content": "Test"}]
                        )
                    
                    # If we get here, the test was successful
                    service.status = ServiceStatus.WORKING
                    service.error_message = ""
                    self.queue_message(
                        action='update_label',
                        label=service.status_label,
                        text="Working",
                        style='Working.TLabel'
                    )
                    
                except requests.Timeout:
                    service.status = ServiceStatus.FAILED
                    service.error_message = "API request timed out"
                    self.queue_message(
                        action='update_label',
                        label=service.status_label,
                        text="Failed (Timeout)",
                        style='Failed.TLabel'
                    )
                    logging.error(f"Timeout testing {service.name}")
                    
                except Exception as e:
                    service.status = ServiceStatus.FAILED
                    service.error_message = str(e)
                    self.queue_message(
                        action='update_label',
                        label=service.status_label,
                        text="Failed",
                        style='Failed.TLabel'
                    )
                    logging.error(f"Error testing {service.name}: {str(e)}")
            
            # Clear testing status
            self.queue_message(action='update_test_status', text="")
            self.queue_message(action='enable_button', button=self.test_button, state='normal')
            
        except Exception as e:
            logging.error(f"Error in test_api_keys: {str(e)}")
            self.queue_message(action='update_test_status', text=f"Error: {str(e)}")
            self.queue_message(action='enable_button', button=self.test_button, state='normal')

    def start_processing(self):
        if not GEMINI_API_KEYS:
            messagebox.showerror("Error", "Please configure API keys in config.py")
            return
            
        if not os.path.exists(self.source_dir.get()):
            messagebox.showerror("Error", "Source directory does not exist")
            return
            
        if not os.path.exists(self.target_dir.get()):
            messagebox.showerror("Error", "Target directory does not exist")
            return
            
        self.is_processing = True
        self.start_time = time.time()  # Start timing
        
        # Update button states
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Reset progress and time displays
        self.progress_var.set(0)
        self.status_label.config(text="Running")
        self.elapsed_time.set("00:00:00")
        self.estimated_time.set("--:--:--")
        self.completion_time.set("--:--:--")
        
        # Start processing in a separate thread
        threading.Thread(target=self.process_plugins, daemon=True).start()

    def stop_processing(self):
        self.is_processing = False
        self.start_time = None
        
        # Reset displays
        self.status_label.config(text="Ready")
        self.elapsed_time.set("00:00:00")
        self.estimated_time.set("--:--:--")
        self.completion_time.set("--:--:--")
        
        # Update button states
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def process_plugins(self):
        """Process plugins in batches of 30."""
        try:
            source_dir = self.source_dir.get()
            if not source_dir:
                raise ValueError("Source directory not selected")

            # Get all plugin directories
            plugin_paths = []
            for item in os.listdir(source_dir):
                item_path = os.path.join(source_dir, item)
                if os.path.isdir(item_path):  # Only process directories
                    plugin_paths.append(item_path)

            if not plugin_paths:
                self._add_to_status("No plugin directories found in the source directory.", True)
                return

            # Process in batches of 30
            batch_size = 30
            for i in range(0, len(plugin_paths), batch_size):
                batch = plugin_paths[i:i + batch_size]
                
                # Get plugin names for the batch
                plugin_names = [os.path.basename(path) for path in batch]
                
                # Create a combined prompt for the entire batch
                combined_prompt = "Please categorize the following WordPress plugins into appropriate categories. Return the results as a JSON object with plugin names as keys and categories as values. Categories should be single words or hyphenated words, suitable for directory names:\n\n"
                combined_prompt += "\n".join(plugin_names)

                try:
                    # Get categories for the entire batch
                    categories = self.categorize_plugins_batch(combined_prompt, plugin_names)
                    
                    # Move plugins based on returned categories
                    for plugin_path, category in zip(batch, categories):
                        if category:
                            self.move_plugin(plugin_path, category)
                            
                except Exception as e:
                    self._add_to_status(f"Error processing batch: {str(e)}", True)
                    logging.error(f"Batch processing error: {str(e)}")

                # Update progress
                self.queue_message(
                    action='update_progress',
                    value=min(100, int((i + batch_size) / len(plugin_paths) * 100))
                )

        except Exception as e:
            self._add_to_status(f"Error in plugin processing: {str(e)}", True)
            logging.error(f"Plugin processing error: {str(e)}")

    def categorize_plugins_batch(self, prompt, plugin_names):
        """Categorize multiple plugins at once using the selected API."""
        try:
            api_key = self.api_keys.get(self.selected_api.get())
            if not api_key:
                raise ValueError(f"API key not found for {self.selected_api.get()}")

            if self.selected_api.get() == "Gemini":
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                
                try:
                    # Parse the JSON response
                    categories_dict = json.loads(response.text)
                    # Map categories to plugin names, use "Uncategorized" as fallback
                    return [categories_dict.get(name, "Uncategorized") for name in plugin_names]
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse API response: {str(e)}")
                    logging.error(f"Raw response: {response.text}")
                    return ["Uncategorized"] * len(plugin_names)
                
            # Add support for other APIs here
            else:
                raise ValueError(f"Unsupported API: {self.selected_api.get()}")
                
        except Exception as e:
            self._add_to_status(f"Error in batch categorization: {str(e)}", True)
            logging.error(f"Batch categorization error: {str(e)}")
            return ["Uncategorized"] * len(plugin_names)

    def move_plugin(self, plugin_path, category):
        """Move a plugin to its categorized directory."""
        try:
            target_dir = self.target_dir.get()
            if not target_dir:
                raise ValueError("Target directory not selected")

            # Create category directory if it doesn't exist
            category_dir = os.path.join(target_dir, category)
            os.makedirs(category_dir, exist_ok=True)

            # Get plugin name and create target path
            plugin_name = os.path.basename(plugin_path)
            target_path = os.path.join(category_dir, plugin_name)

            # Move the plugin directory
            if os.path.exists(target_path):
                # If target exists, create a unique name
                base_name = plugin_name
                counter = 1
                while os.path.exists(target_path):
                    new_name = f"{base_name}_({counter})"
                    target_path = os.path.join(category_dir, new_name)
                    counter += 1

            shutil.move(plugin_path, target_path)
            self._add_to_status(f"Moved '{plugin_name}' to category '{category}'")
            self._update_statistics(plugin_name, category, True)

        except Exception as e:
            self._add_to_status(f"Failed to move '{os.path.basename(plugin_path)}': {str(e)}", True)
            self._update_statistics(os.path.basename(plugin_path), category, False)
            logging.error(f"Move plugin error: {str(e)}")

    def _apply_theme(self):
        """Apply the selected theme."""
        style = ttk.Style()
        
        if self.theme_var.get() == "dark":
            # Dark theme colors
            bg_color = '#2b2b2b'
            fg_color = '#ffffff'
            select_bg = '#404040'
            
            style.configure('TFrame', background=bg_color)
            style.configure('TLabel', background=bg_color, foreground=fg_color)
            style.configure('TButton', background=select_bg)
            style.configure('Treeview', background=bg_color, foreground=fg_color, fieldbackground=bg_color)
            style.configure('TNotebook', background=bg_color)
            style.configure('TNotebook.Tab', background=bg_color, foreground=fg_color)
            
            self.root.configure(bg=bg_color)
        else:
            # Light theme colors
            style.theme_use('clam')
            
            style.configure('TFrame', background='#f0f0f0')
            style.configure('TLabel', background='#f0f0f0', foreground='black')
            style.configure('TButton', background='#e0e0e0')
            style.configure('Treeview', background='white', foreground='black', fieldbackground='white')
            style.configure('TNotebook', background='#f0f0f0')
            style.configure('TNotebook.Tab', background='#e0e0e0', foreground='black')
            
            self.root.configure(bg='#f0f0f0')

    def _update_statistics(self, plugin_name, category, success):
        """Update statistics after processing a plugin."""
        if success:
            if category not in self.stats['categories_used']:
                self.stats['categories_used'][category] = 0
            self.stats['categories_used'][category] += 1
            self.stats['successful_moves'] += 1
        else:
            self.stats['failed_moves'] += 1
        
        self.stats['total_processed'] += 1
        
        # Update statistics display
        self.queue_message(
            action='update_stats',
            stats={
                'total': self.stats['total_processed'],
                'success': self.stats['successful_moves'],
                'failed': self.stats['failed_moves']
            }
        )

    def _browse_directory(self, dir_type):
        """Browse and select a directory.
        
        Args:
            dir_type (str): Either 'source' or 'target' to indicate which directory to set
        """
        try:
            # Get initial directory from current value if set
            current_dir = self.source_dir.get() if dir_type == 'source' else self.target_dir.get()
            initial_dir = current_dir if current_dir and os.path.exists(current_dir) else os.path.expanduser("~")
            
            directory = filedialog.askdirectory(
                title=f"Select {dir_type.title()} Directory",
                initialdir=initial_dir
            )
            
            if directory:
                # Validate directory exists and is accessible
                if not os.path.exists(directory):
                    messagebox.showerror("Error", f"Selected directory does not exist: {directory}")
                    return
                    
                if dir_type == 'target' and not os.access(directory, os.W_OK):
                    messagebox.showerror("Error", f"Cannot write to selected directory: {directory}")
                    return
                
                # Set the directory
                if dir_type == 'source':
                    self.source_dir.set(directory)
                    logging.info(f"Source directory set to: {directory}")
                else:
                    self.target_dir.set(directory)
                    logging.info(f"Target directory set to: {directory}")
                
                # Update status label
                self.status_label.config(text=f"{dir_type.title()} directory selected: {directory}")
                
        except Exception as e:
            logging.error(f"Error selecting {dir_type} directory: {str(e)}")
            messagebox.showerror("Error", f"Failed to select directory: {str(e)}")

    def _add_to_status(self, message, is_error=False):
        """Add a message to the status text widget."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Add message with appropriate tag
        tag = 'error' if is_error else 'success'
        self.status_text.insert(tk.END, formatted_message, tag)
        self.status_text.see(tk.END)  # Auto-scroll to bottom
        self.status_text.update_idletasks()

    def _show_last_move_status(self):
        """Show the last move status in a popup window."""
        try:
            # Get the last line from status_text
            last_line = self.status_text.get("end-2c linestart", "end-1c")
            if last_line.strip():
                messagebox.showinfo("Last Move Status", last_line)
            else:
                messagebox.showinfo("Last Move Status", "No moves have been performed yet.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not retrieve last move status: {str(e)}")

    def _preview_cleanup(self):
        """Preview the changes that will be made to category folders."""
        target_dir = self.target_dir.get()
        if not target_dir or not os.path.exists(target_dir):
            messagebox.showerror("Error", "Please select a valid target directory")
            return
            
        self.cleanup_preview.delete(1.0, tk.END)
        self.cleanup_changes = {}  # Store proposed changes
        
        try:
            # Collect all folder names longer than 20 characters
            long_folders = []
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isdir(item_path) and len(item) > 20:
                    long_folders.append(item)
                    self.cleanup_preview.insert(tk.END, f"Found long folder name: {item}\n")
            
            if not long_folders:
                self.cleanup_preview.insert(tk.END, "\nNo folder names longer than 20 characters found.")
                return
                
            self.cleanup_preview.insert(tk.END, f"\nFound {len(long_folders)} folders to process.\n\n")
            
            # Process folders in batches of 100
            for i in range(0, len(long_folders), 100):
                batch = long_folders[i:i+100]
                self.cleanup_preview.insert(tk.END, f"Processing batch {i//100 + 1}...\n")
                normalized_names = self._get_batch_normalized_names(batch)
                
                if not normalized_names:
                    self.cleanup_preview.insert(tk.END, "Error: No response from Gemini API for this batch.\n")
                    continue
                
                for old_name, new_name in normalized_names.items():
                    if new_name and new_name != old_name:
                        self.cleanup_changes[old_name] = new_name
                        self.cleanup_preview.insert(tk.END, f"Will rename:\n")
                        self.cleanup_preview.insert(tk.END, f"  From: {old_name}\n")
                        self.cleanup_preview.insert(tk.END, f"  To: {new_name}\n\n")
            
            if not self.cleanup_changes:
                self.cleanup_preview.insert(tk.END, "\nNo changes needed for the long folder names.")
                
        except Exception as e:
            self.cleanup_preview.insert(tk.END, f"\nError previewing changes: {str(e)}")
            logging.error(f"Error in preview_cleanup: {str(e)}")
            
    def _get_batch_normalized_names(self, folder_names):
        """Get normalized names for a batch of folders using Gemini API."""
        try:
            # Create a list of folders with their names
            folder_list = "\n".join([f"- {name}" for name in folder_names])
            
            # Prepare the prompt for Gemini
            prompt = (
                "Task: Rename these WordPress plugin folders to be shorter while keeping their main identifiers.\n\n"
                "For each folder name, extract just the essential identifier and remove unnecessary descriptions.\n"
                "Keep hyphens and version numbers if they are part of the main name.\n\n"
                "Format each response exactly as: \"original_name -> new_name\"\n\n"
                "Examples:\n"
                "- advanced-custom-fields-pro-for-wordpress -> advanced-custom-fields-pro\n"
                "- contact-form-7-style-customizer-plugin -> contact-form-7-style\n"
                "- design-feedback-is-a-plugin-that-helps -> design-feedback\n\n"
                "Folders to rename:\n"
                f"{folder_list}"
            )
            
            # Call Gemini API
            response = self.get_plugin_category_from_gemini(prompt)
            if not response:
                logging.error("No response from Gemini API")
                self.cleanup_preview.insert(tk.END, "Error: Gemini API returned no response. Check API key and connection.\n")
                return {}

            # Parse the response
            normalized_names = {}
            lines = [line.strip() for line in response.split('\n') if '->' in line]
            
            for line in lines:
                try:
                    old_name, new_name = [part.strip() for part in line.split('->')]
                    
                    # Clean up names and validate
                    if old_name in folder_names:
                        new_name = new_name.strip('"').strip("'").strip()
                        
                        # Additional validation
                        if (len(new_name) < len(old_name) and 
                            len(new_name) >= 3 and 
                            new_name.lower() != 'plugin' and 
                            new_name.lower() != 'wordpress'):
                            normalized_names[old_name] = new_name
                            logging.info(f"Successfully normalized: {old_name} -> {new_name}")
                        else:
                            logging.warning(f"Skipped invalid normalized name: {old_name} -> {new_name}")
                    
                except Exception as e:
                    logging.error(f"Error parsing line '{line}': {str(e)}")
                    continue

            if not normalized_names:
                self.cleanup_preview.insert(tk.END, "Warning: Could not generate valid names from API response.\n")
            
            logging.info(f"Processed {len(folder_names)} names, got {len(normalized_names)} valid responses")
            return normalized_names
            
        except Exception as e:
            logging.error(f"Error getting normalized names from Gemini: {str(e)}")
            self.cleanup_preview.insert(tk.END, f"Error: {str(e)}\n")
            return {}
            
    def _apply_cleanup(self):
        """Apply the cleanup changes to the category folders."""
        if not hasattr(self, 'cleanup_changes') or not self.cleanup_changes:
            messagebox.showinfo("Info", "No changes to apply")
            return
            
        target_dir = self.target_dir.get()
        if not target_dir or not os.path.exists(target_dir):
            messagebox.showerror("Error", "Invalid target directory")
            return
            
        if not messagebox.askyesno("Confirm", "Are you sure you want to rename these folders?"):
            return
            
        success_count = 0
        error_count = 0
        
        for old_name, new_name in self.cleanup_changes.items():
            try:
                old_path = os.path.join(target_dir, old_name)
                new_path = os.path.join(target_dir, new_name)
                
                # Handle case where target folder already exists
                if os.path.exists(new_path):
                    # Merge folders
                    for item in os.listdir(old_path):
                        old_item_path = os.path.join(old_path, item)
                        new_item_path = os.path.join(new_path, item)
                        shutil.move(old_item_path, new_item_path)
                    os.rmdir(old_path)
                else:
                    # Simple rename
                    os.rename(old_path, new_path)
                    
                success_count += 1
                self.log_text.insert(tk.END, f"Successfully renamed '{old_name}' to '{new_name}'\n")
                
            except Exception as e:
                error_count += 1
                self.log_text.insert(tk.END, f"Error renaming '{old_name}': {str(e)}\n")
                
        # Show results
        message = f"Completed category cleanup:\n{success_count} folders renamed successfully"
        if error_count > 0:
            message += f"\n{error_count} errors encountered"
        
        messagebox.showinfo("Complete", message)
        
        # Clear preview and changes
        self.cleanup_preview.delete(1.0, tk.END)
        self.cleanup_changes = {}
        
    def _normalize_category_name(self, folder_name):
        """Normalize a category folder name."""
        # Convert to title case and remove common prefixes/suffixes
        name = folder_name.strip()
        
        # First try to match with standard categories
        name_lower = name.lower()
        for category in self.STANDARD_CATEGORIES:
            if category.lower() in name_lower:
                return category
                
        # Special cases
        if "woo" in name_lower:
            return "WooCommerce"
        if "multi" in name_lower and "lang" in name_lower:
            return "Multilingual"
        if "analytics" in name_lower or "stat" in name_lower:
            return "Analytics"
        if "security" in name_lower or "protect" in name_lower:
            return "Security"
        if "seo" in name_lower or "search engine" in name_lower:
            return "SEO"
            
        # If no standard category found, extract the main plugin name
        # Remove common phrases and descriptions
        name = re.sub(r'(?i)(is a |plugin that |would be |categorized as |plugin for |plugin |for |tool |that helps |users |gather |website |on their |designs?)', '', name)
        
        # Get the first part before any separator
        separators = [' - ', '-', ' | ', '|', ':']
        for sep in separators:
            if sep in name:
                name = name.split(sep)[0]
                break
                
        # Clean up the name
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)  # Replace multiple spaces with single space
        
        # If name became too short or is just generic words, use the first part of original name
        if len(name) < 3 or name.lower() in ['plugin', 'tool', 'wordpress']:
            original_parts = folder_name.split(' ')[0:2]  # Take first two words
            name = '-'.join(original_parts)
            
        return name.strip()

    def _export_stats(self):
        """Export statistics to a file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"plugin_stats_{timestamp}.json"
            )
            
            if file_path:
                # Prepare statistics data
                stats_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_processed': self.stats['total_processed'],
                    'successful_categorizations': self.stats['successful_moves'],
                    'failed_categorizations': self.stats['failed_moves'],
                    'categories_used': dict(self.stats['categories_used']),
                    'api_usage': dict(self.stats['api_usage'])
                }
                
                # Write to file
                with open(file_path, 'w') as f:
                    json.dump(stats_data, f, indent=4)
                
                self._add_to_status("Statistics exported successfully!")
                messagebox.showinfo("Success", "Statistics exported successfully!")
                
        except Exception as e:
            error_msg = f"Failed to export statistics: {str(e)}"
            self._add_to_status(error_msg, True)
            messagebox.showerror("Error", error_msg)
            logging.error(error_msg)

    def get_plugin_category_from_gemini(self, prompt):
        """Get category suggestions from Gemini API."""
        try:
            if not GEMINI_API_KEYS:
                raise ValueError("Gemini API key not configured")

            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEYS[0]
            }

            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024
                }
            }

            response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=10)
            
            if response.status_code != 200:
                raise ValueError(f"API request failed with status {response.status_code}")

            response_data = response.json()
            if 'candidates' in response_data and response_data['candidates']:
                return response_data['candidates'][0]['content']['parts'][0]['text']
            
            return None

        except Exception as e:
            logging.error(f"Error getting category from Gemini: {str(e)}")
            return None

def initialize_api_clients():
    """Initialize API clients with proper configuration"""
    if not hasattr(initialize_api_clients, '_initialized'):
        try:
            # Configure Gemini with timeout
            if config.GEMINI_API_KEYS and len(config.GEMINI_API_KEYS) > 0:
                genai.configure(api_key=config.GEMINI_API_KEYS[0])
                # Set timeout for requests
                genai.configure(timeout=10)  # 10 seconds timeout
            
            # Configure OpenAI
            if config.OPENAI_API_KEY:
                openai.api_key = config.OPENAI_API_KEY
            
            # Configure Anthropic
            if config.ANTHROPIC_API_KEY:
                anthropic = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            
            initialize_api_clients._initialized = True
        except Exception as e:
            logging.error(f"Error initializing API clients: {str(e)}")
            raise

if __name__ == "__main__":
    def start_application():
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        # First check dependencies
        from dependency_checker import DependencyChecker
        checker = DependencyChecker(tk.Toplevel(root))
        
        def show_login():
            # After dependencies are checked/installed, show login window
            from login_window import LoginWindow
            
            def launch_main_app():
                root.destroy()  # Destroy the root window before creating new one
                app = PluginCategorizerGUI(tk.Tk())
                app.root.mainloop()
            
            login = LoginWindow(tk.Toplevel(root), launch_main_app)
        
        # Wait for dependency check to complete before showing login
        root.after(100, lambda: root.wait_window(checker.root) or show_login())
        root.mainloop()
    
    # Start the application
    start_application()
