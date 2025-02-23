import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import logging
import shutil
import requests
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from difflib import get_close_matches
import queue
import threading
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup
import openai
import cohere
from anthropic import Anthropic
from googlesearch import search
from config import *
import enum

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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

class PluginCategorizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WordPress Plugin Categorizer")
        self.root.geometry("1200x800")
        
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
        
        # Add tabs to notebook
        self.notebook.add(self.setup_tab, text="Setup & API Status")
        self.notebook.add(self.process_tab, text="Process Plugins")
        self.notebook.add(self.status_tab, text="File Move Status")
        self.notebook.add(self.stats_tab, text="Statistics")
        self.notebook.add(self.logs_tab, text="Logs")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Initialize tab contents
        self._initialize_setup_tab()
        self._initialize_process_tab()
        self._initialize_status_tab()
        self._initialize_stats_tab()
        self._initialize_logs_tab()
        self._initialize_settings_tab()
        
        # Initialize statistics
        self.stats = {
            'total_processed': 0,
            'successful_categorizations': 0,
            'failed_categorizations': 0,
            'categories_used': {},
            'api_usage': {name: 0 for name in self.api_services}
        }
        
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
                    self.status_label.config(text=message['text'], fg=message['color'])
                elif action == 'update_progress':
                    self.progress_label.config(text=message['text'])
                
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

    def _initialize_status_tab(self):
        """Initialize the File Move Status tab."""
        # Create main frame
        main_frame = ttk.Frame(self.status_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create status text widget
        self.status_text = scrolledtext.ScrolledText(main_frame, height=20, width=80)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text widget
        self.status_text.config(state='disabled')
        
        # Add tags for coloring
        self.status_text.tag_configure("success", foreground="green")
        self.status_text.tag_configure("error", foreground="red")

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
        # Directory variables
        self.source_dir = tk.StringVar(value='')
        self.target_dir = tk.StringVar(value='')
        
        # Progress variables
        self.total_progress = tk.DoubleVar(value=0)
        self.current_progress = tk.DoubleVar(value=0)
        self.current_file = tk.StringVar(value="")
        self.start_time = None
        self.time_label = None
        
        # Processing state
        self.is_processing = False
        self.log_queue = queue.Queue()
        
        # Settings variables
        self.theme_var = tk.StringVar(value="light")
        self.batch_size = tk.IntVar(value=10)
        self.rate_limit = tk.IntVar(value=60)
        
        # Constants
        self.MAX_CATEGORIES = 25
        self.MAX_TOTAL_CATEGORIES = 50
        
        # Time tracking
        self.start_time = None
        self.elapsed_time = tk.StringVar(value="00:00:00")
        self.estimated_time = tk.StringVar(value="--:--:--")
        self.completion_time = tk.StringVar(value="--:--:--")

    def _async_test_api_keys(self):
        """Run API tests asynchronously to prevent GUI freezing."""
        self.queue_message(action='update_test_status', text="Testing APIs... Please wait...")
        self.test_button.config(state='disabled')
        threading.Thread(target=self.test_api_keys, daemon=True).start()

    def test_api_keys(self):
        """Test all API keys."""
        try:
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
                    # Test the API key
                    if service.name == 'Gemini API':
                        response = requests.post(
                            GEMINI_API_URL,
                            headers={'Content-Type': 'application/json', 'x-goog-api-key': GEMINI_API_KEYS[0]},
                            json={
                                "contents": [{"parts": [{"text": "Test"}]}],
                                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1}
                            }
                        )
                        if response.status_code == 200:
                            self.queue_message(
                                action='update_label',
                                label=service.status_label,
                                text="Working",
                                style='Working.TLabel'
                            )
                            service.status = ServiceStatus.WORKING
                        else:
                            self.queue_message(
                                action='update_label',
                                label=service.status_label,
                                text=f"Failed (Status: {response.status_code})",
                                style='Failed.TLabel'
                            )
                            service.status = ServiceStatus.FAILED
                    
                    elif service.name == 'OpenAI API':
                        client = openai.OpenAI(api_key=OPENAI_API_KEY)
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": "Test"}],
                            max_tokens=1
                        )
                        self.queue_message(
                            action='update_label',
                            label=service.status_label,
                            text="Working",
                            style='Working.TLabel'
                        )
                        service.status = ServiceStatus.WORKING
                    
                    elif service.name == 'Cohere API':
                        if not COHERE_API_KEY:
                            raise ValueError("Cohere API key not configured")
                        co = cohere.Client(api_key=COHERE_API_KEY)
                        response = co.generate(
                            prompt="Test",
                            max_tokens=1,
                            model=COHERE_MODEL
                        )
                        if response and response.generations:
                            self.queue_message(
                                action='update_label',
                                label=service.status_label,
                                text="Working",
                                style='Working.TLabel'
                            )
                            service.status = ServiceStatus.WORKING
                        else:
                            raise ValueError("No response from Cohere API")
                    
                    elif service.name == 'Anthropic API':
                        client = Anthropic(api_key=ANTHROPIC_API_KEY)
                        completion = client.messages.create(
                            model="claude-3-haiku-20240307",
                            max_tokens=1,
                            messages=[{
                                "role": "user",
                                "content": "Test"
                            }]
                        )
                        self.queue_message(
                            action='update_label',
                            label=service.status_label,
                            text="Working",
                            style='Working.TLabel'
                        )
                        service.status = ServiceStatus.WORKING
                    
                    elif service.name == 'Google Search':
                        results = list(search("wordpress plugin", num_results=1))
                        self.queue_message(
                            action='update_label',
                            label=service.status_label,
                            text="Working",
                            style='Working.TLabel'
                        )
                        service.status = ServiceStatus.WORKING
                
                except Exception as e:
                    error_msg = str(e)
                    # Truncate long error messages
                    if len(error_msg) > 50:
                        error_msg = error_msg[:47] + "..."
                    self.queue_message(
                        action='update_label',
                        label=service.status_label,
                        text=f"Failed ({error_msg})",
                        style='Failed.TLabel'
                    )
                    service.status = ServiceStatus.FAILED
                    logging.error(f"API test failed for {service.name}: {str(e)}")
                
                if service.status == ServiceStatus.NOT_CONFIGURED:
                    self.queue_message(
                        action='update_label',
                        label=service.status_label,
                        text="Not Configured",
                        style='NotConfigured.TLabel'
                    )
            
            # Clear testing status
            self.queue_message(action='update_test_status', text="")
            self.queue_message(action='enable_button', button=self.test_button, state='normal')
            
        except Exception as e:
            self.queue_message(
                action='update_test_status',
                text=f"Error testing APIs: {str(e)}"
            )
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
        """Process all plugins in the source directory."""
        try:
            # Get list of all plugin folders
            source_dir = self.source_dir.get()
            if not os.path.exists(source_dir):
                error_msg = "Source directory does not exist"
                logging.error(error_msg)
                self.queue_message(action='update_status', text=f"Error: {error_msg}", color='red')
                return
                
            plugin_folders = [f for f in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, f))]
            total_plugins = len(plugin_folders)
            
            if total_plugins == 0:
                msg = "No plugin folders found in source directory"
                logging.warning(msg)
                self.queue_message(action='update_status', text=msg, color='blue')
                return
                
            logging.info(f"Found {total_plugins} plugin folders to process")
            self.queue_message(action='update_status', text=f"Processing {total_plugins} plugins...", color='blue')
            
            processed_count = 0
            move_success_count = 0
            
            for plugin_name in plugin_folders:
                if not self.is_processing:
                    break
                    
                try:
                    plugin_path = os.path.join(source_dir, plugin_name)
                    
                    # Update progress
                    processed_count += 1
                    progress = (processed_count / total_plugins) * 100
                    self.progress_var.set(progress)
                    
                    # Update current file being processed
                    self.queue_message(action='update_current_file', text=f"Processing: {plugin_name}")
                    
                    # Analyze and categorize the plugin
                    result = self._analyze_plugin(plugin_name)
                    if not result:
                        continue
                        
                    plugin_name, category, confidence = result
                    
                    # Skip if categorization failed
                    if category == "Unknown":
                        self.queue_message(
                            action='update_status',
                            text=f"Skipped '{plugin_name}': Unable to determine category",
                            color='blue'
                        )
                        continue
                    
                    # Add to status display
                    self._add_to_status(plugin_name, category, confidence)
                    
                    # Move the plugin to its category folder
                    move_status, error_msg = self.move_plugin(plugin_path, category)
                    if move_status:
                        move_success_count += 1
                    
                    # Update status display with move status
                    self._add_to_status(plugin_name, category, confidence, move_status, error_msg)
                    
                    # Update progress display
                    self.queue_message(
                        action='update_progress',
                        text=f"Processed: {processed_count}/{total_plugins} ({move_success_count} moved successfully)"
                    )
                    
                    # Calculate and update time estimation
                    if self.start_time and processed_count > 0:
                        elapsed_time = time.time() - self.start_time
                        plugins_per_second = processed_count / elapsed_time
                        remaining_plugins = total_plugins - processed_count
                        
                        if plugins_per_second > 0:
                            estimated_remaining = remaining_plugins / plugins_per_second
                            total_estimated = elapsed_time + estimated_remaining
                            
                            # Format time strings
                            remaining_str = time.strftime("%M:%S", time.gmtime(estimated_remaining))
                            total_str = time.strftime("%M:%S", time.gmtime(total_estimated))
                            eta_str = time.strftime("%H:%M:%S", time.localtime(time.time() + estimated_remaining))
                            
                            self.time_label.config(
                                text=f"Remaining: {remaining_str} | Total: {total_str} | ETA: {eta_str}"
                            )
                    
                    # Add small delay to prevent overwhelming the system
                    time.sleep(0.1)
                    
                except Exception as e:
                    error_msg = f"Error processing '{plugin_name}': {str(e)}"
                    logging.error(error_msg)
                    self.queue_message(action='update_status', text=f"Error: {error_msg}", color='red')
                    continue
            
            # Final status update
            if self.is_processing:
                final_msg = f"Completed processing {processed_count} plugins. {move_success_count} moved successfully."
                logging.info(final_msg)
                self.queue_message(action='update_status', text=final_msg, color='green')
            else:
                stop_msg = "Processing stopped by user"
                logging.info(stop_msg)
                self.queue_message(action='update_status', text=stop_msg, color='blue')
                
        except Exception as e:
            error_msg = f"Error during plugin processing: {str(e)}"
            logging.error(error_msg)
            self.queue_message(action='update_status', text=f"Error: {error_msg}", color='red')
        finally:
            # Reset processing state
            self.is_processing = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.queue_message(action='update_current_file', text="")

    def _analyze_plugin(self, plugin_name):
        """Analyze a plugin folder and return categorization results."""
        if not self.is_processing:
            return None

        try:
            # Get the plugin name
            plugin_name = os.path.basename(plugin_name)
            
            # Get category and confidence for the plugin
            category = None
            confidence = 0.0
            used_service = None
            
            for service_name, service in self.api_services.items():
                if not service.enabled:
                    continue
                    
                try:
                    if service_name == 'gemini':
                        category = self._try_gemini_categorization(plugin_name)
                        confidence = 0.9 if category else 0.0
                    elif service_name == 'openai':
                        category = self._try_openai_categorization(plugin_name)
                        confidence = 0.85 if category else 0.0
                    elif service_name == 'cohere':
                        category = self._try_cohere_categorization(plugin_name)
                        confidence = 0.8 if category else 0.0
                    elif service_name == 'anthropic':
                        category = self._try_anthropic_categorization(plugin_name)
                        confidence = 0.85 if category else 0.0
                    elif service_name == 'google_search':
                        category = self._try_google_search_categorization(plugin_name)
                        confidence = 0.7 if category else 0.0
                    
                    if category:
                        used_service = service_name
                        self.stats['api_usage'][service_name] += 1
                        break
                        
                except Exception as e:
                    logging.warning(f"Error with {service_name} for {plugin_name}: {str(e)}")
                    continue
            
            if category:
                # Update statistics
                self._update_statistics(plugin_name, category, True)
                self.log_text.insert(tk.END, f"Successfully categorized '{plugin_name}' as '{category}' using {used_service}\n")
                return plugin_name, category, confidence
            else:
                # Update statistics for failed categorization
                self._update_statistics(plugin_name, "Unknown", False)
                self.log_text.insert(tk.END, f"Failed to categorize '{plugin_name}'\n")
                return plugin_name, "Unknown", 0.0
                
        except Exception as e:
            self.log_text.insert(tk.END, f"Error analyzing plugin '{plugin_name}': {str(e)}\n")
            return None

    def _add_to_status(self, plugin_name, category, confidence, move_status=None, error_msg=None):
        """Add a plugin to the status text with move status."""
        confidence_str = f"{confidence*100:.1f}%" if confidence > 0 else "N/A"
        
        # Format the status message
        status_msg = f"{plugin_name}: {category} ({confidence_str})"
        
        # Add move status if provided
        if move_status is not None:
            if move_status:
                status_msg += " \u2713 Moved successfully"
            else:
                status_msg += " \u2717 Move failed"
                if error_msg:
                    status_msg += f"\n    Error: {error_msg}"
        
        # Add to status text with appropriate color
        self.status_text.config(state='normal')
        if move_status is None:
            # No move attempted yet - default color
            self.status_text.insert(tk.END, status_msg + "\n")
        else:
            # Use tag to color the line
            tag = "success" if move_status else "error"
            self.status_text.insert(tk.END, status_msg + "\n", tag)
        
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    def get_plugin_category_from_gemini(self, plugin_name):
        """Try to categorize plugin using multiple AI services in sequence."""
        for service in self.api_services.values():
            try:
                if service.enabled:
                    if service.name == 'Gemini API':
                        category = self._try_gemini_categorization(plugin_name)
                    
                    elif service.name == 'OpenAI API':
                        category = self._try_openai_categorization(plugin_name)
                    
                    elif service.name == 'Cohere API':
                        category = self._try_cohere_categorization(plugin_name)
                    
                    elif service.name == 'Anthropic API':
                        category = self._try_anthropic_categorization(plugin_name)
                    
                    elif service.name == 'Google Search':
                        category = self._try_google_search_categorization(plugin_name)
                    
                    if category:
                        self.log_text.insert(tk.END, f"Successfully categorized '{plugin_name}' using {service.name}\n")
                        return category
                    else:
                        self.log_text.insert(tk.END, f"Failed to categorize '{plugin_name}' using {service.name}, trying next service...\n")
            
            except Exception as e:
                self.log_text.insert(tk.END, f"Error with {service.name} for '{plugin_name}': {str(e)}\n")
                continue
        
        # If all services fail, use the default category
        self.log_text.insert(tk.END, f"All services failed to categorize '{plugin_name}', using default category\n")
        return 'Content Management'

    def _try_gemini_categorization(self, plugin_name):
        """Try to categorize using Google's Gemini API."""
        try:
            prompt = self._get_categorization_prompt(plugin_name)
            
            response = requests.post(
                GEMINI_API_URL,
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': GEMINI_API_KEYS[0]
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 50
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    category = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    return self._normalize_category(category)
            return None
        except Exception as e:
            logging.warning(f"Gemini categorization failed: {str(e)}")
            return None

    def _try_openai_categorization(self, plugin_name):
        """Try to categorize using OpenAI's API."""
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a WordPress plugin categorization expert."},
                    {"role": "user", "content": self._get_categorization_prompt(plugin_name)}
                ],
                max_tokens=50,
                temperature=0.3
            )
            category = response.choices[0].message.content.strip()
            return self._validate_and_normalize_category(category)
        except Exception as e:
            logging.warning(f"OpenAI categorization failed: {str(e)}")
            return None

    def _try_cohere_categorization(self, plugin_name):
        """Try to categorize using Cohere's API."""
        try:
            co = cohere.Client(api_key=COHERE_API_KEY)
            response = co.generate(
                model=COHERE_MODEL,
                prompt=self._get_categorization_prompt(plugin_name),
                max_tokens=50,  
                temperature=0.3,  
                k=0,  
                stop_sequences=["\n", "."],  
                num_generations=1  
            )
            
            if response and response.generations:
                category = response.generations[0].text.strip()
                return self._validate_and_normalize_category(category)
            return None
            
        except Exception as e:
            logging.warning(f"Cohere categorization failed: {str(e)}")
            return None

    def _try_anthropic_categorization(self, plugin_name):
        """Try to categorize using Anthropic's Claude API."""
        try:
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            completion = client.messages.create(
                model="claude-3-haiku-20240307",  # Using the haiku model which is more widely available
                max_tokens=50,
                messages=[{
                    "role": "user",
                    "content": self._get_categorization_prompt(plugin_name)
                }]
            )
            category = completion.content[0].text.strip()
            return self._validate_and_normalize_category(category)
        except Exception as e:
            logging.warning(f"Anthropic categorization failed: {str(e)}")
            return None

    def _try_google_search_categorization(self, plugin_name):
        """Try to categorize using Google Search results."""
        try:
            # Try each search method
            results = None
            for method in [
                self._try_google_search_method1,
                self._try_google_search_method2,
                self._try_google_search_method3
            ]:
                try:
                    time.sleep(2)  # Delay between attempts
                    results = method()
                    if results:
                        break
                except Exception:
                    continue

            if not results:
                return None

            # Extract category hints from search results
            text = ' '.join(results).lower()
            category = self._extract_category_from_text(text)
            return self._normalize_category(category)

        except Exception as e:
            logging.warning(f"Google Search categorization failed: {str(e)}")
            return None

    def _try_google_search_method1(self):
        """Method 1: Using googlesearch-python with custom headers."""
        try:
            from googlesearch import search
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            results = list(search("wordpress plugin", num_results=1, sleep_interval=5, user_agent=headers['User-Agent']))
            return results
        except Exception as e:
            logging.warning(f"Google Search Method 1 failed: {str(e)}")
            return None

    def _try_google_search_method2(self):
        """Method 2: Direct HTTP request with custom parameters."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(
                'https://www.google.com/search',
                params={'q': 'wordpress plugin', 'num': 10},
                headers=headers
            )
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                for div in soup.find_all('div', class_='g'):
                    if div.find('h3'):
                        results.append(div.find('h3').text)
                return results
            return None
        except Exception as e:
            logging.warning(f"Google Search Method 2 failed: {str(e)}")
            return None

    def _try_google_search_method3(self):
        """Method 3: Using DuckDuckGo as alternative."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(
                'https://api.duckduckgo.com/',
                params={'q': 'wordpress plugin', 'format': 'json'},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                results = []
                if 'Abstract' in data and data['Abstract']:
                    results.append(data['Abstract'])
                if 'RelatedTopics' in data:
                    for topic in data['RelatedTopics'][:5]:
                        if 'Text' in topic:
                            results.append(topic['Text'])
                return results
            return None
        except Exception as e:
            logging.warning(f"Google Search Method 3 (DuckDuckGo) failed: {str(e)}")
            return None

    def _get_categorization_prompt(self, plugin_name):
        """Get the prompt for categorization."""
        return f"What category would you put the WordPress plugin '{plugin_name}' in?"

    def _normalize_category(self, category):
        """Normalize the category name."""
        if not category:
            return None
            
        # Convert to lowercase and strip whitespace
        category = category.lower().strip()
        
        # Map of common variations to standard categories
        category_mapping = {
            'seo': 'SEO',
            'ecommerce': 'E-commerce',
            'e-commerce': 'E-commerce',
            'social media': 'Social Media',
            'socialmedia': 'Social Media',
            'security': 'Security',
            'backup': 'Backup',
            'analytics': 'Analytics',
            'form': 'Forms',
            'forms': 'Forms',
            'marketing': 'Marketing',
            'performance': 'Performance',
            'optimization': 'Performance',
            'cache': 'Performance',
            'media': 'Media',
            'gallery': 'Media',
            'payment': 'Payment',
            'payments': 'Payment',
            'membership': 'Membership',
            'memberships': 'Membership',
            'content management': 'Content Management',
            'content': 'Content Management',
            'cms': 'Content Management',
            'blog': 'Content Management',
            'custom post': 'Content Management',
            'customization': 'Customization',
            'theme': 'Customization',
            'widget': 'Widgets',
            'widgets': 'Widgets',
            'woocommerce': 'E-commerce'
        }
        
        # Try to match with standard categories
        for key, value in category_mapping.items():
            if key in category:
                return value
                
        # If no match found, return original category with first letter capitalized
        return category.title()

    def _validate_and_normalize_category(self, category):
        """Validate and normalize the category name."""
        if not category:
            return None
            
        # Convert to lowercase and strip whitespace
        category = category.lower().strip()
        
        # Map of common variations to standard categories
        category_mapping = {
            'seo': 'SEO',
            'ecommerce': 'E-commerce',
            'e-commerce': 'E-commerce',
            'social media': 'Social Media',
            'socialmedia': 'Social Media',
            'security': 'Security',
            'backup': 'Backup',
            'analytics': 'Analytics',
            'form': 'Forms',
            'forms': 'Forms',
            'marketing': 'Marketing',
            'performance': 'Performance',
            'optimization': 'Performance',
            'cache': 'Performance',
            'media': 'Media',
            'gallery': 'Media',
            'payment': 'Payment',
            'payments': 'Payment',
            'membership': 'Membership',
            'memberships': 'Membership',
            'content management': 'Content Management',
            'content': 'Content Management',
            'cms': 'Content Management',
            'blog': 'Content Management',
            'custom post': 'Content Management',
            'customization': 'Customization',
            'theme': 'Customization',
            'widget': 'Widgets',
            'widgets': 'Widgets',
            'woocommerce': 'E-commerce'
        }
        
        # Try to match with standard categories
        for key, value in category_mapping.items():
            if key in category:
                return value
                
        # If no match found, return original category with first letter capitalized
        return category.title()

    def _extract_category_from_text(self, text):
        """Extract category hints from text."""
        # Common category keywords to look for
        category_keywords = {
            'seo': 'SEO',
            'ecommerce': 'E-commerce',
            'security': 'Security',
            'backup': 'Backup',
            'analytics': 'Analytics',
            'form': 'Forms',
            'marketing': 'Marketing',
            'performance': 'Performance',
            'media': 'Media',
            'payment': 'Payment',
            'membership': 'Membership',
            'content': 'Content Management',
            'customization': 'Customization',
            'widget': 'Widgets'
        }
        
        for keyword, category in category_keywords.items():
            if keyword in text:
                return category
                
        return "Content Management"  # Default category

    def move_plugin(self, plugin_path, category):
        """
        Move a plugin to its categorized folder.
        Creates the category folder if it doesn't exist.
        """
        try:
            # Ensure we have full paths
            source_path = os.path.abspath(plugin_path)
            plugin_name = os.path.basename(source_path)
            
            # Create category directory path
            category_dir = os.path.join(self.target_dir.get(), category)
            dest_path = os.path.join(category_dir, plugin_name)
            
            logging.info(f"Moving plugin from {source_path} to {dest_path}")
            
            # Create category folder if it doesn't exist
            os.makedirs(category_dir, exist_ok=True)
            
            # If destination exists, add a number to the filename
            base_name = plugin_name
            counter = 1
            while os.path.exists(dest_path):
                plugin_name = f"{base_name}_{counter}"
                dest_path = os.path.join(category_dir, plugin_name)
                counter += 1
            
            # Move the entire directory
            try:
                shutil.move(source_path, dest_path)
                logging.info(f"Successfully moved '{plugin_name}' to '{category}' folder")
                return True, None
            except Exception as e:
                # If move fails, try copy then delete
                shutil.copytree(source_path, dest_path)
                if os.path.exists(dest_path):
                    shutil.rmtree(source_path)
                    logging.info(f"Successfully moved '{plugin_name}' to '{category}' folder using copy+delete")
                    return True, None
                else:
                    raise Exception("Failed to copy directory")
            
        except Exception as e:
            error_msg = f"Error moving plugin '{plugin_name}': {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("Error", error_msg)
            return False, error_msg
            
        return False, None

    def categorize_plugin(self, plugin_path):
        """Categorize a plugin based on its content."""
        try:
            # Ensure we have full paths
            plugin_path = os.path.abspath(plugin_path)
            plugin_name = os.path.basename(plugin_path)
            
            # Log the paths for debugging
            logging.info(f"Processing plugin: {plugin_path}")
            self.current_file.set(f"Processing: {plugin_name}")
            
            # Read plugin content
            with open(plugin_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Get category using OpenAI
            category = self.get_category_openai(content)
            if not category:
                logging.error(f"Failed to categorize plugin: {plugin_name}")
                return
            
            # Add to results and update UI
            self.results[plugin_name] = category
            self.update_treeview(plugin_name, category)
            
            # Move the plugin file to its category folder
            if self.move_plugin(plugin_path, category):
                logging.info(f"Successfully categorized '{plugin_name}' as '{category}'")
            else:
                logging.error(f"Failed to move '{plugin_name}' to '{category}' folder")
            
            # Update progress
            self.processed_files += 1
            progress = (self.processed_files / self.total_files) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{int(progress)}%")
            
            # Update statistics
            self.update_statistics()
            
        except Exception as e:
            error_msg = f"Error processing '{plugin_name}': {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("Error", error_msg)
        finally:
            self.current_file.set("")

    def process_files(self):
        """Process all selected files."""
        try:
            source_dir = self.source_dir.get()
            if not os.path.exists(source_dir):
                messagebox.showerror("Error", f"Source directory does not exist: {source_dir}")
                return
                
            # Get list of files with full paths
            files = [os.path.join(source_dir, f) for f in os.listdir(source_dir) 
                    if os.path.isfile(os.path.join(source_dir, f))]
            
            if not files:
                messagebox.showwarning("Warning", "No files found in source directory!")
                return
            
            # Initialize progress tracking
            self.total_files = len(files)
            self.processed_files = 0
            self.progress_var.set(0)
            self.results.clear()
            self.tree.delete(*self.tree.get_children())
            
            # Log the start of processing
            logging.info(f"Starting to process {len(files)} files from {source_dir}")
            
            # Process each file
            for file_path in files:
                logging.info(f"Starting to process file: {file_path}")
                self.categorize_plugin(file_path)
            
            messagebox.showinfo("Complete", "All plugins have been categorized and moved!")
            
        except Exception as e:
            error_msg = f"Error processing files: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("Error", error_msg)

    def _export_stats(self):
        """Export statistics to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"plugin_stats_{timestamp}.json"
        )
        
        if file_path:
            try:
                # Prepare statistics data
                stats_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_processed': self.stats['total_processed'],
                    'successful_categorizations': self.stats['successful_categorizations'],
                    'failed_categorizations': self.stats['failed_categorizations'],
                    'categories_used': dict(self.stats['categories_used']),
                    'api_usage': dict(self.stats['api_usage'])
                }
                
                # Write to file
                with open(file_path, 'w') as f:
                    json.dump(stats_data, f, indent=4)
                
                messagebox.showinfo("Success", "Statistics exported successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export statistics: {str(e)}")

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
        self.stats['total_processed'] += 1
        if success:
            self.stats['successful_categorizations'] += 1
            self.stats['categories_used'][category] = self.stats['categories_used'].get(category, 0) + 1
        else:
            self.stats['failed_categorizations'] += 1
        
        # Update summary labels
        total = self.stats['total_processed']
        successful = self.stats['successful_categorizations']
        
        self.stats_labels['total'].config(text=f"Total Processed: {total}")
        self.stats_labels['success'].config(text=f"Successfully Categorized: {successful}")
        self.stats_labels['failed'].config(text=f"Failed to Categorize: {total - successful}")
        self.stats_labels['categories'].config(text=f"Categories Used: {len(self.stats['categories_used'])}")
        self.stats_labels['api_usage'].config(text=f"API Calls Made: {sum(self.stats['api_usage'].values())}")

    def _browse_directory(self, dir_type):
        """Browse and select a directory.
        
        Args:
            dir_type (str): Either 'source' or 'target' to indicate which directory to set
        """
        try:
            # Get initial directory from current value if set
            initial_dir = self.source_dir.get() if dir_type == 'source' else self.target_dir.get()
            if not initial_dir or not os.path.exists(initial_dir):
                initial_dir = os.path.expanduser("~")  # Default to user's home directory
            
            directory = filedialog.askdirectory(
                title=f"Select {dir_type.title()} Directory",
                initialdir=initial_dir
            )
            
            if directory:
                # Validate directory exists and is accessible
                if not os.path.exists(directory):
                    messagebox.showerror("Error", f"Selected directory does not exist: {directory}")
                    return
                    
                if not os.access(directory, os.R_OK):
                    messagebox.showerror("Error", f"Cannot read from selected directory: {directory}")
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
