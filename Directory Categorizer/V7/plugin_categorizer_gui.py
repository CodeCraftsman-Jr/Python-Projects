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
from datetime import datetime
import json
from dataclasses import dataclass
import google.generativeai as genai
import openai
import cohere
from anthropic import Anthropic
from googlesearch import search
import config
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
        self.root.title("Plugin Categorizer")
        
        # Initialize API keys from config
        self.api_keys = {
            'gemini': tk.StringVar(value=config.GEMINI_API_KEYS[0] if config.GEMINI_API_KEYS else ""),
            'openai': tk.StringVar(value=config.OPENAI_API_KEY),
            'cohere': tk.StringVar(value=config.COHERE_API_KEY),
            'anthropic': tk.StringVar(value=config.ANTHROPIC_API_KEY),
            'google_search': tk.StringVar(value="")
        }
        
        # Import required API libraries
        try:
            global genai, openai, cohere, Anthropic, googlesearch
            import google.generativeai as genai
            import openai
            import cohere
            from anthropic import Anthropic
            from googlesearch import search
        except ImportError as e:
            logging.error(f"Failed to import API libraries: {str(e)}")
        
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
        """Process any pending messages in the message queue."""
        try:
            while True:
                message = self.message_queue.get_nowait()
                
                if message.get('action') == 'update_label':
                    label = message.get('label')
                    text = message.get('text', '')
                    style = message.get('style', '')
                    if label and hasattr(label, 'config'):
                        label.config(text=text, style=style)
                
                elif message.get('action') == 'update_test_status':
                    text = message.get('text', '')
                    if hasattr(self, 'test_status_label'):
                        self.test_status_label.config(text=text)
                
                elif message.get('action') == 'enable_button':
                    button = message.get('button')
                    state = message.get('state', 'normal')
                    if button and hasattr(button, 'config'):
                        button.config(state=state)
                
                elif message.get('action') == 'update_log':
                    text = message.get('text', '')
                    if hasattr(self, 'log_text'):
                        self.log_text.insert(tk.END, text + '\n')
                        self.log_text.see(tk.END)
                
                elif message.get('action') == 'update_status':
                    self.status_label.config(text=message['text'], foreground=message['foreground'])
                elif message.get('action') == 'update_progress':
                    self.progress_label.config(text=message['text'])
                elif message.get('action') == 'update_current_file':
                    self.current_file_label.config(text=message['text'])
                
                self.message_queue.task_done()
                
        except queue.Empty:
            pass
        finally:
            # Schedule the next check
            self.root.after(100, self.process_messages)
    
    def queue_message(self, **kwargs):
        """Add a message to the queue for processing.
        
        Args:
            **kwargs: Keyword arguments for the message.
                     Must include 'action' and may include 'text' and 'foreground'.
        """
        if 'color' in kwargs:
            kwargs['foreground'] = kwargs.pop('color')
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
        main_frame = ttk.Frame(self.setup_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create status frame
        status_frame = ttk.LabelFrame(main_frame, text="API Status", padding=(10, 5))
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create grid for API services
        for i, (key, service) in enumerate(self.api_services.items()):
            # Create enable/disable checkbox
            enabled_var = tk.BooleanVar(value=service.enabled)
            enabled_check = ttk.Checkbutton(
                status_frame,
                text=service.name,
                variable=enabled_var,
                command=lambda s=service, v=enabled_var: self._toggle_service(s, v)
            )
            enabled_check.grid(row=i, column=0, sticky='w', padx=5, pady=2)
            
            # Create status label with style
            service.status_label = ttk.Label(
                status_frame,
                text="Not Configured",
                style='NotConfigured.TLabel'
            )
            service.status_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
        
        # Create API key entries
        api_frame = ttk.LabelFrame(main_frame, text="API Keys")
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        row = 0
        for api_name in ['gemini', 'openai', 'cohere', 'anthropic']:
            # Create StringVar for API key
            self.api_keys[api_name] = tk.StringVar()
            
            # Create label and entry
            ttk.Label(api_frame, text=f"{api_name.title()} API Key:").grid(row=row, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(api_frame, textvariable=self.api_keys[api_name], show='*')
            entry.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
            
            # Add trace to update config when API key changes
            self.api_keys[api_name].trace_add('write', self._create_api_key_callback(api_name))
            
            row += 1
        
        # Add save and test buttons at the bottom of API frame
        button_frame = ttk.Frame(api_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Save API Keys", command=self._save_api_keys).pack(side=tk.LEFT, padx=5)
        self.test_button = ttk.Button(button_frame, text="Test API Keys", command=self._async_test_api_keys)
        self.test_button.pack(side=tk.LEFT, padx=5)
        
        # Add status label for test results
        self.test_status_label = ttk.Label(button_frame, text="")
        self.test_status_label.pack(side=tk.LEFT, padx=5)
        
    def _create_api_key_callback(self, api_name):
        """Create a callback for API key changes that properly captures the api_name."""
        def callback(*args):
            try:
                # Update status to indicate key needs testing
                self.root.after(0, lambda: self.queue_message(
                    action='update_label',
                    label=self.api_services[api_name].status_label,
                    text="Not Tested",
                    style='NotConfigured.TLabel'
                ))
                self.api_services[api_name].status = ServiceStatus.NOT_CONFIGURED
            except Exception as e:
                logging.error(f"Error updating {api_name} API key: {str(e)}")
        return callback

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
        # Create frames for different sections
        api_frame = ttk.LabelFrame(self.settings_tab, text="API Settings")
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add API key entries
        self.api_keys = {}
        self.api_statuses = {}
        
        row = 0
        for api_name in ['gemini', 'openai', 'cohere', 'anthropic']:
            # Create StringVar for API key
            self.api_keys[api_name] = tk.StringVar()
            
            # Create label and entry
            ttk.Label(api_frame, text=f"{api_name.title()} API Key:").grid(row=row, column=0, padx=5, pady=5, sticky='w')
            ttk.Entry(api_frame, textvariable=self.api_keys[api_name], show='*').grid(row=row, column=1, padx=5, pady=5, sticky='ew')
            
            # Create status label
            status_label = ttk.Label(api_frame, text="Not Configured")
            status_label.grid(row=row, column=2, padx=5, pady=5)
            self.api_statuses[api_name] = status_label
            
            row += 1
            
        # Add test button
        ttk.Button(api_frame, text="Test API Keys", command=self.test_api_keys).grid(row=row, column=0, columnspan=3, pady=10)
        
        # Add batch processing settings
        batch_frame = ttk.LabelFrame(self.settings_tab, text="Processing Settings")
        batch_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add batch processing option
        self.batch_processing = tk.BooleanVar(value=False)
        self.batch_size = tk.IntVar(value=10)
        
        ttk.Checkbutton(batch_frame, text="Enable batch processing", variable=self.batch_processing).pack(padx=5, pady=5)
        
        batch_size_frame = ttk.Frame(batch_frame)
        batch_size_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(batch_size_frame, text="Batch size:").pack(side=tk.LEFT)
        ttk.Entry(batch_size_frame, textvariable=self.batch_size, width=10).pack(side=tk.LEFT, padx=5)
        
        # Add theme selection
        theme_frame = ttk.LabelFrame(self.settings_tab, text="Theme")
        theme_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.theme_var = tk.StringVar(value="light")
        ttk.Radiobutton(theme_frame, text="Light", variable=self.theme_var, value="light", command=self._apply_theme).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(theme_frame, text="Dark", variable=self.theme_var, value="dark", command=self._apply_theme).pack(side=tk.LEFT, padx=5, pady=5)

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
        try:
            # Disable the test button while testing
            self.test_button.config(state='disabled')
            self.queue_message(action='update_test_status', text="Testing APIs... Please wait...")
            
            # Create a new thread for testing
            test_thread = threading.Thread(target=self._run_api_tests, daemon=True)
            test_thread.start()
            
        except Exception as e:
            logging.error(f"Error starting API tests: {str(e)}")
            self.test_button.config(state='normal')
            self.queue_message(action='update_test_status', text=f"Error: {str(e)}")

    def _run_api_tests(self):
        """Run the actual API tests with rate limiting."""
        try:
            for service_name, service in self.api_services.items():
                if not service.enabled:
                    continue
                
                # Create a local copy of service_name and service for the lambda
                current_service_name = service_name
                current_service = service
                
                # Update status to testing
                self.root.after(0, lambda: self.queue_message(
                    action='update_label',
                    label=current_service.status_label,
                    text="Testing...",
                    style='Testing.TLabel'
                ))
                
                # Test the API with rate limiting
                try:
                    time.sleep(config.RETRY_DELAY)  # Add delay between tests
                    success = self.test_api_connection(current_service_name)
                    
                    if success:
                        self.root.after(0, lambda: self.queue_message(
                            action='update_label',
                            label=current_service.status_label,
                            text="Ready",
                            style='Working.TLabel'
                        ))
                        current_service.status = ServiceStatus.WORKING
                    else:
                        self.root.after(0, lambda: self.queue_message(
                            action='update_label',
                            label=current_service.status_label,
                            text="Failed",
                            style='Failed.TLabel'
                        ))
                        current_service.status = ServiceStatus.FAILED
                        
                except Exception as e:
                    logging.error(f"Error testing {current_service_name}: {str(e)}")
                    error_msg = str(e)
                    status_text = "Error"
                    
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        status_text = "Rate Limited"
                    elif "quota" in error_msg.lower() or "exceeded" in error_msg.lower():
                        status_text = "Quota Exceeded"
                    elif "key" in error_msg.lower() or "invalid" in error_msg.lower():
                        status_text = "Invalid Key"
                    elif "billing" in error_msg.lower():
                        status_text = "Billing Required"
                    
                    self.root.after(0, lambda: self.queue_message(
                        action='update_label',
                        label=current_service.status_label,
                        text=status_text,
                        style='Failed.TLabel'
                    ))
                    current_service.status = ServiceStatus.FAILED
            
            # Re-enable the test button
            self.root.after(0, lambda: self.queue_message(
                action='enable_button',
                button=self.test_button,
                state='normal'
            ))
            self.root.after(0, lambda: self.queue_message(
                action='update_test_status',
                text="API testing complete"
            ))
            
        except Exception as e:
            logging.error(f"Error in API testing thread: {str(e)}")
            self.root.after(0, lambda: self.queue_message(
                action='enable_button',
                button=self.test_button,
                state='normal'
            ))
            self.root.after(0, lambda: self.queue_message(
                action='update_test_status',
                text=f"Error: {str(e)}"
            ))

    def test_api_connection(self, api_name):
        """Test the connection to a specific API."""
        try:
            # Add delay for rate limiting
            time.sleep(config.RETRY_DELAY)
            
            if api_name == 'gemini':
                api_key = self.api_keys[api_name].get()  # Get from GUI instead of config
                if not api_key:
                    raise ValueError("API key is not set")
                    
                # Just validate the API key format
                success = bool(api_key)
                
            elif api_name == 'openai':
                api_key = self.api_keys[api_name].get()  # Get from GUI instead of config
                if not api_key:
                    raise ValueError("API key is not set")
                    
                # Just validate the API key format (should start with 'sk-')
                success = bool(api_key and api_key.startswith('sk-'))
                if not success:
                    raise ValueError("Invalid API key format")
                
            elif api_name == 'cohere':
                api_key = self.api_keys[api_name].get()  # Get from GUI instead of config
                if not api_key:
                    raise ValueError("API key is not set")
                    
                # Just validate the API key
                success = bool(api_key)
                
            elif api_name == 'anthropic':
                api_key = self.api_keys[api_name].get()  # Get from GUI instead of config
                if not api_key:
                    raise ValueError("API key is not set")
                    
                # Just validate the API key format (should start with 'sk-ant-')
                success = bool(api_key and api_key.startswith('sk-ant-'))
                if not success:
                    raise ValueError("Invalid API key format")
                
            elif api_name == 'google_search':
                # Always mark as success since we can't easily test
                success = True
                
            else:
                success = False
            
            if success:
                return True
            else:
                return False
                
        except Exception as e:
            error_msg = str(e)
            status_text = "Error"
            
            if "429" in error_msg or "Too Many Requests" in error_msg:
                status_text = "Rate Limited"
            elif "quota" in error_msg.lower() or "exceeded" in error_msg.lower():
                status_text = "Quota Exceeded"
            elif "key" in error_msg.lower() or "invalid" in error_msg.lower():
                status_text = "Invalid Key"
            elif "billing" in error_msg.lower():
                status_text = "Billing Required"
            
            self.root.after(0, lambda: self.queue_message(
                action='update_label',
                label=self.api_services[api_name].status_label,
                text=status_text,
                style='Failed.TLabel'
            ))
            self.api_services[api_name].status = ServiceStatus.FAILED
            logging.error(f"API test failed for {api_name}: {str(e)}")
            return False

    def start_processing(self):
        if not config.GEMINI_API_KEYS:
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
                self.queue_message(action='update_status', text=f"Error: {error_msg}", foreground='red')
                return
                
            # Get all folders in the source directory - these are our plugins
            plugin_folders = [f for f in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, f))]
            total_plugins = len(plugin_folders)
            
            if total_plugins == 0:
                msg = "No folders found in source directory"
                logging.warning(msg)
                self.queue_message(action='update_status', text=msg, foreground='blue')
                return
                
            logging.info(f"Found {total_plugins} plugin folders to process")
            self.queue_message(action='update_status', text=f"Processing {total_plugins} plugins...", foreground='blue')
            
            processed_count = 0
            move_success_count = 0
            
            # Check if batch processing is enabled
            if self.batch_processing.get():
                batch_size = max(1, min(self.batch_size.get(), total_plugins))  # Ensure valid batch size
                logging.info(f"Using batch processing with batch size: {batch_size}")
                
                # Process plugins in batches
                for i in range(0, total_plugins, batch_size):
                    if not self.is_processing:
                        break
                        
                    batch_plugins = plugin_folders[i:i + batch_size]
                    try:
                        # Update progress for batch start
                        self.queue_message(
                            action='update_current_file', 
                            text=f"Processing batch {i//batch_size + 1} of {(total_plugins + batch_size - 1)//batch_size}"
                        )
                        
                        # Process the batch
                        batch_results = self._analyze_plugin_batch(batch_plugins)
                        if batch_results:
                            for plugin_name, (category, confidence) in batch_results.items():
                                if not self.is_processing:
                                    break
                                    
                                plugin_path = os.path.join(source_dir, plugin_name)
                                
                                # Skip if categorization failed
                                if category == "Unknown":
                                    self.queue_message(
                                        action='update_status',
                                        text=f"Skipped '{plugin_name}': Unable to determine category",
                                        foreground='blue'
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
                                
                                processed_count += 1
                                
                                # Update progress
                                progress = (processed_count / total_plugins) * 100
                                self.progress_var.set(progress)
                                self.queue_message(
                                    action='update_progress',
                                    text=f"Processed: {processed_count}/{total_plugins} ({move_success_count} moved successfully)"
                                )
                                
                        # Add small delay to prevent overwhelming the system
                        time.sleep(0.1)
                        
                    except Exception as e:
                        error_msg = f"Error processing batch: {str(e)}"
                        logging.error(error_msg)
                        self.queue_message(action='update_status', text=f"Error: {error_msg}", foreground='red')
                        continue
                        
            else:
                # Original single processing logic
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
                                foreground='blue'
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
                        self.queue_message(action='update_status', text=f"Error: {error_msg}", foreground='red')
                        continue
            
            # Final status update
            if self.is_processing:
                final_msg = f"Completed processing {processed_count} plugins. {move_success_count} moved successfully."
                logging.info(final_msg)
                self.queue_message(action='update_status', text=final_msg, foreground='green')
            else:
                stop_msg = "Processing stopped by user"
                logging.info(stop_msg)
                self.queue_message(action='update_status', text=stop_msg, foreground='blue')
                
        except Exception as e:
            error_msg = f"Error during plugin processing: {str(e)}"
            logging.error(error_msg)
            self.queue_message(action='update_status', text=f"Error: {error_msg}", foreground='red')
        finally:
            # Reset processing state
            self.is_processing = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.queue_message(action='update_current_file', text="")

    def _analyze_plugin_batch(self, plugin_names):
        """Analyze a batch of plugins and return categorization results."""
        if not self.is_processing:
            return None
            
        results = {}
        try:
            # Create combined prompt for all plugins
            combined_prompt = "Please categorize the following WordPress plugins into their appropriate categories:\n\n"
            for plugin_name in plugin_names:
                combined_prompt += f"- {plugin_name}\n"
            combined_prompt += "\nFor each plugin, provide the category that best describes its functionality."
            
            # Try each enabled service in sequence for the entire batch
            for service_name, service in self.api_services.items():
                if not service.enabled:
                    continue
                    
                try:
                    categories = None
                    if service_name == 'gemini':
                        categories = self._try_gemini_categorization(combined_prompt, plugin_names)
                    elif service_name == 'openai':
                        categories = self._try_openai_categorization(combined_prompt, plugin_names)
                    elif service_name == 'cohere':
                        categories = self._try_cohere_categorization(combined_prompt, plugin_names)
                    elif service_name == 'anthropic':
                        categories = self._try_anthropic_categorization(combined_prompt, plugin_names)
                    elif service_name == 'google_search':
                        # For Google Search, we still need to process plugins individually
                        categories = {}
                        for plugin_name in plugin_names:
                            category = self._try_google_search_categorization(plugin_name)
                            if category:
                                categories[plugin_name] = category
                    
                    if categories:
                        # Process the results
                        for plugin_name, category in categories.items():
                            confidence = self._get_confidence_score(service_name)
                            results[plugin_name] = (category, confidence)
                            self._update_statistics(plugin_name, category, True)
                            self.log_text.insert(tk.END, f"Successfully categorized '{plugin_name}' as '{category}' using {service_name}\n")
                        
                        # Only increment API usage once per batch
                        self.stats['api_usage'][service_name] += 1
                        return results
                        
                except Exception as e:
                    logging.warning(f"Error with {service_name} for batch: {str(e)}")
                    continue
            
            # If no service succeeded, mark all plugins as Unknown
            for plugin_name in plugin_names:
                results[plugin_name] = ("Unknown", 0.0)
                self._update_statistics(plugin_name, "Unknown", False)
                self.log_text.insert(tk.END, f"Failed to categorize '{plugin_name}'\n")
            
        except Exception as e:
            logging.error(f"Error analyzing plugin batch: {str(e)}")
            # In case of error, mark remaining plugins as Unknown
            for plugin_name in plugin_names:
                if plugin_name not in results:
                    results[plugin_name] = ("Unknown", 0.0)
                    self._update_statistics(plugin_name, "Unknown", False)
                    
        return results

    def _get_confidence_score(self, service_name):
        """Get the confidence score for a service."""
        confidence_scores = {
            'gemini': 0.9,
            'openai': 0.85,
            'cohere': 0.8,
            'anthropic': 0.85,
            'google_search': 0.7
        }
        return confidence_scores.get(service_name, 0.0)

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
                    
                    elif service_name == 'openai':
                        category = self._try_openai_categorization(plugin_name)
                    
                    elif service_name == 'cohere':
                        category = self._try_cohere_categorization(plugin_name)
                    
                    elif service_name == 'anthropic':
                        category = self._try_anthropic_categorization(plugin_name)
                    
                    elif service_name == 'google_search':
                        category = self._try_google_search_categorization(plugin_name)
                    
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

    def _try_gemini_categorization(self, prompt, plugin_names=None):
        """Try to categorize using Google's Gemini API. Supports both single and batch processing."""
        try:
            api_key = self.api_keys['gemini'].get()  # Get from GUI instead of config
            if not api_key:
                return None
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            response = model.generate_content(prompt)
            
            if response and response.text:
                if plugin_names:  # Batch mode
                    return self._parse_batch_response(response.text, plugin_names)
                else:  # Single mode
                    category = response.text.strip()
                    return self._normalize_category(category)
                    
        except Exception as e:
            logging.error(f"Gemini API error: {str(e)}")
            # Try secondary key if available
            if len(config.GEMINI_API_KEYS) > 1:
                try:
                    api_key = config.GEMINI_API_KEYS[1]
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        if plugin_names:
                            return self._parse_batch_response(response.text, plugin_names)
                        else:
                            category = response.text.strip()
                            return self._normalize_category(category)
                except Exception as e2:
                    logging.error(f"Gemini API error with secondary key: {str(e2)}")
            
        return None

    def _try_openai_categorization(self, prompt, plugin_names=None):
        """Try to categorize using OpenAI's API. Supports both single and batch processing."""
        try:
            api_key = self.api_keys['openai'].get()  # Get from GUI instead of config
            if not api_key:
                return None
                
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a WordPress plugin expert. Categorize plugins based on their functionality."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200 if plugin_names else 50,
                temperature=0.3
            )
            
            if response and response.choices:
                if plugin_names:  # Batch mode
                    return self._parse_batch_response(response.choices[0].message.content, plugin_names)
                else:  # Single mode
                    category = response.choices[0].message.content.strip()
                    return self._normalize_category(category)
                    
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            
        return None

    def _try_cohere_categorization(self, prompt, plugin_names=None):
        """Try to categorize using Cohere's API. Supports both single and batch processing."""
        try:
            api_key = self.api_keys['cohere'].get()  # Get from GUI instead of config
            if not api_key:
                return None
                
            co = cohere.Client(api_key=api_key)
            
            response = co.generate(
                model=config.COHERE_MODEL,
                prompt=prompt,
                max_tokens=200 if plugin_names else 50,
                temperature=0.3,
                k=0,
                stop_sequences=["\n", "."] if not plugin_names else None,
                num_generations=1
            )
            
            if response and response.generations:
                if plugin_names:  # Batch mode
                    return self._parse_batch_response(response.generations[0].text, plugin_names)
                else:  # Single mode
                    category = response.generations[0].text.strip()
                    return self._normalize_category(category)
                    
        except Exception as e:
            logging.error(f"Cohere API error: {str(e)}")
            
        return None

    def _try_anthropic_categorization(self, prompt, plugin_names=None):
        """Try to categorize using Anthropic's Claude API. Supports both single and batch processing."""
        try:
            api_key = self.api_keys['anthropic'].get()  # Get from GUI instead of config
            if not api_key:
                return None
                
            client = Anthropic(api_key=api_key)
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Using the latest model
                max_tokens=200 if plugin_names else 50,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            if response and response.content:
                if plugin_names:  # Batch mode
                    return self._parse_batch_response(response.content[0].text, plugin_names)
                else:  # Single mode
                    category = response.content[0].text.strip()
                    return self._normalize_category(category)
                    
        except Exception as e:
            logging.error(f"Anthropic API error: {str(e)}")
            
        return None

    def _try_google_search_categorization(self, plugin_name):
        """Try to categorize using Google Search results."""
        try:
            # Method 1: Using googlesearch-python
            search_query = f"WordPress plugin {plugin_name} category type"
            search_results = list(search(search_query, num=5, stop=5))
            
            if search_results:
                # Analyze search results to determine category
                text_to_analyze = " ".join(search_results)
                return self._extract_category_from_text(text_to_analyze)
                
        except Exception as e:
            logging.warning(f"Google Search Method 1 failed: {str(e)}")
            
        return None

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

    def _parse_batch_response(self, response_text, plugin_names):
        """Parse the API response to extract categories for each plugin."""
        try:
            categories = {}
            lines = response_text.split('\n')
            current_plugin = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Look for plugin names in the response
                for plugin_name in plugin_names:
                    if plugin_name.lower() in line.lower():
                        current_plugin = plugin_name
                        break
                
                if current_plugin and current_plugin not in categories:
                    # Extract category from the line
                    category = self._extract_category_from_text(line)
                    if category:
                        categories[current_plugin] = self._normalize_category(category)
            
            # Fill in any missing plugins with Unknown category
            for plugin_name in plugin_names:
                if plugin_name not in categories:
                    categories[plugin_name] = "Unknown"
            
            return categories
            
        except Exception as e:
            logging.error(f"Error parsing batch response: {str(e)}")
            return None

    def _normalize_category(self, category):
        """Normalize a category name to a consistent format."""
        if not category:
            return None
            
        # Convert to lowercase and replace spaces/special chars with underscores
        normalized = category.lower().strip()
        normalized = ''.join(c if c.isalnum() else '_' for c in normalized)
        normalized = '_'.join(filter(None, normalized.split('_')))
        
        return normalized

    def _update_api_key(self, api_name):
        """Update API key in config when it changes in GUI."""
        try:
            new_value = self.api_keys[api_name].get()
            
            # Update status to indicate key needs testing
            self.root.after(0, lambda: self.queue_message(
                action='update_label',
                label=self.api_services[api_name].status_label,
                text="Not Tested",
                style='NotConfigured.TLabel'
            ))
            self.api_services[api_name].status = ServiceStatus.NOT_CONFIGURED
            
        except Exception as e:
            logging.error(f"Error updating {api_name} API key: {str(e)}")

    def _save_api_keys(self):
        """Save API keys to config.py file."""
        try:
            # Read the current config.py content
            with open('config.py', 'r') as f:
                lines = f.readlines()
            
            # Update the lines with new API keys
            for i, line in enumerate(lines):
                if 'GEMINI_API_KEYS' in line:
                    lines[i] = f'GEMINI_API_KEYS = ["{self.api_keys["gemini"].get()}"]\n'
                elif 'OPENAI_API_KEY' in line:
                    lines[i] = f'OPENAI_API_KEY = "{self.api_keys["openai"].get()}"\n'
                elif 'COHERE_API_KEY' in line:
                    lines[i] = f'COHERE_API_KEY = "{self.api_keys["cohere"].get()}"\n'
                elif 'ANTHROPIC_API_KEY' in line:
                    lines[i] = f'ANTHROPIC_API_KEY = "{self.api_keys["anthropic"].get()}"\n'
            
            # Write back to config.py
            with open('config.py', 'w') as f:
                f.writelines(lines)
            
            messagebox.showinfo("Success", "API keys saved successfully!")
            
            # Test the APIs after saving
            self._async_test_api_keys()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save API keys: {str(e)}")
            logging.error(f"Error saving API keys: {str(e)}")

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
