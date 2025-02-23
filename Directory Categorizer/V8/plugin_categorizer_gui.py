import os
os.environ['ABSL_LOGGING_MODULE_LEVEL'] = '0'  # Suppress absl logging
import google.generativeai as genai
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import json
from enum import Enum, auto
import config
import queue
import requests
from googlesearch import search
from tqdm import tqdm
from logging.handlers import RotatingFileHandler

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ServiceStatus(Enum):
    """Enum for service status."""
    NOT_CONFIGURED = auto()
    TESTING = auto()
    WORKING = auto()
    FAILED = auto()

class APIService:
    """Class to manage API service state."""
    def __init__(self, name, enabled=True):
        self.name = name
        self.enabled = enabled
        self.status = ServiceStatus.NOT_CONFIGURED
        self.status_label = None
        self.last_request = 0
        self.request_count = 0
        self.error_count = 0
        self.cache = {}

class PluginCategorizerGUI:
    """Advanced GUI for plugin categorization using multiple AI models."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Directory Categorizer V8")
        
        # Initialize Gemini configuration
        try:
            genai.configure(api_key=config.GEMINI_API_KEYS[0])
        except Exception as e:
            logging.warning(f"Failed to initialize Gemini: {e}")
        
        # Initialize services
        self.api_services = {
            'gemini': APIService('Google Gemini'),
            'openai': APIService('OpenAI GPT'),
            'cohere': APIService('Cohere Command'),
            'anthropic': APIService('Anthropic Claude')
        }
        
        # Initialize variables
        self.api_keys = {}
        self.selected_dir = tk.StringVar()
        self.destination_dir = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_text = tk.StringVar(value="Ready")
        self.dark_mode = tk.BooleanVar(value=False)
        self.message_queue = queue.Queue()
        self.processing = False
        self.cache = {}
        
        # Create styles
        self._create_styles()
        
        # Create main container
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.process_tab = ttk.Frame(self.notebook)
        self.results_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.setup_tab, text="Setup & API Status")
        self.notebook.add(self.process_tab, text="Process Files")
        self.notebook.add(self.results_tab, text="Results")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Initialize tabs
        self._initialize_setup_tab()
        self._initialize_process_tab()
        self._initialize_results_tab()
        self._initialize_settings_tab()
        
        # Set up logging
        self._setup_logging()
        
        # Start message processing
        self._start_message_processing()
        
        # Load saved settings
        self._load_settings()
        
        # Apply initial theme
        self._apply_theme()
    
    def _create_styles(self):
        """Create ttk styles for the GUI."""
        self.style = ttk.Style()
        
        # Create label styles
        self.style.configure('Working.TLabel', foreground='green')
        self.style.configure('Failed.TLabel', foreground='red')
        self.style.configure('Testing.TLabel', foreground='orange')
        self.style.configure('NotConfigured.TLabel', foreground='gray')
        
        # Create button styles
        self.style.configure('Primary.TButton', font=('Helvetica', 10, 'bold'))
        self.style.configure('Secondary.TButton', font=('Helvetica', 10))
        
        # Create frame styles
        self.style.configure('Card.TFrame', relief='raised', padding=10)
    
    def _setup_logging(self):
        """Set up logging configuration."""
        log_file = config.LOG_SETTINGS['filename']
        max_size = config.LOG_SETTINGS['max_size']
        backup_count = config.LOG_SETTINGS['backup_count']
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        
        formatter = logging.Formatter(config.LOG_SETTINGS['format'])
        handler.setFormatter(formatter)
        
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(config.LOG_SETTINGS['level'])
    
    def _start_message_processing(self):
        """Start the message processing thread."""
        def process_messages():
            while True:
                try:
                    message = self.message_queue.get()
                    if message['action'] == 'update_label':
                        message['label'].config(
                            text=message['text'],
                            style=message.get('style', '')
                        )
                    elif message['action'] == 'enable_button':
                        message['button'].config(state=message['state'])
                    elif message['action'] == 'update_progress':
                        self.progress_var.set(message['value'])
                    elif message['action'] == 'update_status':
                        self.status_text.set(message['text'])
                    elif message['action'] == 'show_error':
                        messagebox.showerror("Error", message['text'])
                    elif message['action'] == 'show_info':
                        messagebox.showinfo("Info", message['text'])
                    elif message['action'] == 'update_test_status':
                        self.test_status_label.config(text=message['text'])
                    
                    self.message_queue.task_done()
                except Exception as e:
                    logging.error(f"Error processing message: {str(e)}")
                    continue
        
        self.message_thread = threading.Thread(
            target=process_messages,
            daemon=True
        )
        self.message_thread.start()
    
    def queue_message(self, **kwargs):
        """Add a message to the queue."""
        self.message_queue.put(kwargs)
    
    def _load_settings(self):
        """Load saved settings."""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                    
                    # Load theme
                    self.dark_mode.set(settings.get('dark_mode', False))
                    
                    # Load API keys
                    for api_name, key in settings.get('api_keys', {}).items():
                        if api_name in self.api_keys:
                            self.api_keys[api_name].set(key)
        except Exception as e:
            logging.error(f"Error loading settings: {str(e)}")
    
    def _save_settings(self):
        """Save current settings."""
        try:
            settings = {
                'dark_mode': self.dark_mode.get(),
                'api_keys': {
                    name: var.get()
                    for name, var in self.api_keys.items()
                }
            }
            
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving settings: {str(e)}")
            self.queue_message(
                action='show_error',
                text=f"Error saving settings: {str(e)}"
            )
    
    def _apply_theme(self):
        """Apply the current theme."""
        theme = 'dark' if self.dark_mode.get() else 'light'
        settings = config.THEME_SETTINGS[theme]
        
        # Update ttk styles
        self.style.configure('TFrame', background=settings['bg'])
        self.style.configure('TLabel', background=settings['bg'], foreground=settings['fg'])
        self.style.configure('TButton', background=settings['button_bg'], foreground=settings['button_fg'])
        self.style.configure('TEntry', fieldbackground=settings['bg'], foreground=settings['fg'])
        
        # Update root window
        self.root.configure(bg=settings['bg'])
        
        # Save settings
        self._save_settings()

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
            
            # Create status label
            service.status_label = ttk.Label(
                status_frame,
                text="Not Configured",
                style='NotConfigured.TLabel'
            )
            service.status_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
            
            # Create request count label
            ttk.Label(
                status_frame,
                text="Requests: 0"
            ).grid(row=i, column=2, sticky='w', padx=5, pady=2)
        
        # Create API key entries
        api_frame = ttk.LabelFrame(main_frame, text="API Keys", padding=(10, 5))
        api_frame.pack(fill=tk.X, pady=10)
        
        row = 0
        for api_name in ['gemini', 'openai', 'cohere', 'anthropic']:
            # Create StringVar for API key
            self.api_keys[api_name] = tk.StringVar()
            
            # Create label and entry
            ttk.Label(api_frame, text=f"{api_name.title()} API Key:").grid(
                row=row, column=0, padx=5, pady=5, sticky='w'
            )
            entry = ttk.Entry(api_frame, textvariable=self.api_keys[api_name], show='*', width=50)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
            
            # Add show/hide button
            show_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                api_frame,
                text="Show",
                variable=show_var,
                command=lambda e=entry, v=show_var: self._toggle_key_visibility(e, v)
            ).grid(row=row, column=2, padx=5, pady=5)
            
            # Add trace to update config when API key changes
            self.api_keys[api_name].trace_add('write', self._create_api_key_callback(api_name))
            
            row += 1
        
        # Add button frame
        button_frame = ttk.Frame(api_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        # Add save and test buttons
        ttk.Button(
            button_frame,
            text="Save API Keys",
            command=self._save_api_keys,
            style='Primary.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        self.test_button = ttk.Button(
            button_frame,
            text="Test API Keys",
            command=self._async_test_api_keys,
            style='Primary.TButton'
        )
        self.test_button.pack(side=tk.LEFT, padx=5)
        
        # Add status label
        self.test_status_label = ttk.Label(button_frame, text="")
        self.test_status_label.pack(side=tk.LEFT, padx=5)
        
        # Add help text
        help_frame = ttk.LabelFrame(main_frame, text="Help", padding=(10, 5))
        help_frame.pack(fill=tk.X, pady=10)
        
        help_text = """
        1. Enter your API keys for the services you want to use
        2. Click 'Save API Keys' to save them
        3. Click 'Test API Keys' to verify they work
        4. Enable/disable services using the checkboxes
        
        Note: You don't need all API keys. The app will use available services.
        """
        ttk.Label(help_frame, text=help_text, wraplength=500).pack(pady=5)

    def _initialize_process_tab(self):
        """Initialize the Process Files tab."""
        main_frame = ttk.Frame(self.process_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Source directory selection
        source_frame = ttk.LabelFrame(main_frame, text="Source Directory", padding=(10, 5))
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(source_frame, text="Source Directory:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(source_frame, textvariable=self.selected_dir, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(source_frame, text="Browse", command=self._browse_source_directory).pack(side=tk.LEFT, padx=5)
        
        # Destination directory selection
        dest_frame = ttk.LabelFrame(main_frame, text="Destination Directory", padding=(10, 5))
        dest_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(dest_frame, text="Destination Directory:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(dest_frame, textvariable=self.destination_dir, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(dest_frame, text="Browse", command=self._browse_destination_directory).pack(side=tk.LEFT, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Processing Options", padding=(10, 5))
        options_frame.pack(fill=tk.X, pady=10)
        
        # Confidence threshold
        ttk.Label(options_frame, text="Minimum Confidence:").grid(
            row=0, column=0, padx=5, pady=5, sticky='w'
        )
        self.confidence_var = tk.DoubleVar(value=config.CATEGORIZATION_SETTINGS['min_confidence'])
        ttk.Entry(
            options_frame,
            textvariable=self.confidence_var,
            width=10
        ).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Batch size
        ttk.Label(options_frame, text="Batch Size:").grid(
            row=1, column=0, padx=5, pady=5, sticky='w'
        )
        self.batch_size_var = tk.IntVar(value=config.RATE_LIMIT_SETTINGS['gemini']['batch_size'])
        ttk.Entry(
            options_frame,
            textvariable=self.batch_size_var,
            width=10
        ).grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # Use web search checkbox
        self.use_search_var = tk.BooleanVar(value=config.CATEGORIZATION_SETTINGS['fallback_to_search'])
        ttk.Checkbutton(
            options_frame,
            text="Use Web Search for Better Accuracy",
            variable=self.use_search_var
        ).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        
        # Use cache checkbox
        self.use_cache_var = tk.BooleanVar(value=config.CACHE_SETTINGS['enabled'])
        ttk.Checkbutton(
            options_frame,
            text="Use Cache (Faster Processing)",
            variable=self.use_cache_var
        ).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding=(10, 5))
        progress_frame.pack(fill=tk.X, pady=10)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Status label
        ttk.Label(
            progress_frame,
            textvariable=self.status_text
        ).pack(pady=5)
        
        # Statistics labels
        self.stats_frame = ttk.Frame(progress_frame)
        self.stats_frame.pack(fill=tk.X, pady=5)
        
        self.processed_label = ttk.Label(self.stats_frame, text="Processed: 0")
        self.processed_label.pack(side=tk.LEFT, padx=10)
        
        self.remaining_label = ttk.Label(self.stats_frame, text="Remaining: 0")
        self.remaining_label.pack(side=tk.LEFT, padx=10)
        
        self.errors_label = ttk.Label(self.stats_frame, text="Errors: 0")
        self.errors_label.pack(side=tk.LEFT, padx=10)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        self.start_button = ttk.Button(
            button_frame,
            text="Start Processing",
            command=self._start_processing,
            style='Primary.TButton'
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="Stop",
            command=self._stop_processing,
            state='disabled'
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def _initialize_results_tab(self):
        """Initialize the Results tab."""
        main_frame = ttk.Frame(self.results_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Results tree
        tree_frame = ttk.LabelFrame(main_frame, text="Categorized Files", padding=(10, 5))
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create tree with scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_tree = ttk.Treeview(
            tree_frame,
            columns=('Category', 'Confidence', 'Service'),
            show='headings'
        )
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        tree_scroll.config(command=self.results_tree.yview)
        self.results_tree.config(yscrollcommand=tree_scroll.set)
        
        # Configure columns
        self.results_tree.heading('Category', text='Category')
        self.results_tree.heading('Confidence', text='Confidence')
        self.results_tree.heading('Service', text='Service Used')
        
        # Add export button
        export_frame = ttk.Frame(main_frame)
        export_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            export_frame,
            text="Export Results",
            command=self._export_results,
            style='Primary.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            export_frame,
            text="Clear Results",
            command=self._clear_results
        ).pack(side=tk.LEFT, padx=5)

    def _initialize_settings_tab(self):
        """Initialize the Settings tab."""
        main_frame = ttk.Frame(self.settings_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Appearance settings
        appearance_frame = ttk.LabelFrame(main_frame, text="Appearance", padding=(10, 5))
        appearance_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(
            appearance_frame,
            text="Dark Mode",
            variable=self.dark_mode,
            command=self._apply_theme
        ).pack(padx=5, pady=5)
        
        # Cache settings
        cache_frame = ttk.LabelFrame(main_frame, text="Cache Settings", padding=(10, 5))
        cache_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            cache_frame,
            text="Clear Cache",
            command=self._clear_cache
        ).pack(padx=5, pady=5)
        
        self.cache_size_label = ttk.Label(cache_frame, text="Cache Size: 0 MB")
        self.cache_size_label.pack(padx=5, pady=5)
        
        # Category management
        category_frame = ttk.LabelFrame(main_frame, text="Category Management", padding=(10, 5))
        category_frame.pack(fill=tk.X, pady=10)
        
        # Category list
        self.category_list = tk.Listbox(category_frame, height=5)
        self.category_list.pack(fill=tk.X, padx=5, pady=5)
        
        for category in config.CATEGORIZATION_SETTINGS['category_suggestions']:
            self.category_list.insert(tk.END, category)
        
        # Add category
        add_frame = ttk.Frame(category_frame)
        add_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.new_category = tk.StringVar()
        ttk.Entry(
            add_frame,
            textvariable=self.new_category
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            add_frame,
            text="Add Category",
            command=self._add_category
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            add_frame,
            text="Remove Selected",
            command=self._remove_category
        ).pack(side=tk.LEFT, padx=5)
        
        # Reset settings
        reset_frame = ttk.Frame(main_frame)
        reset_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            reset_frame,
            text="Reset All Settings",
            command=self._reset_settings,
            style='Secondary.TButton'
        ).pack(side=tk.RIGHT, padx=5)

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

    def _toggle_key_visibility(self, entry, show_var):
        """Toggle API key visibility."""
        entry.config(show='' if show_var.get() else '*')

    def _toggle_service(self, service, enabled_var):
        """Toggle service enabled state."""
        service.enabled = enabled_var.get()
        if not service.enabled:
            self.root.after(0, lambda: self.queue_message(
                action='update_label',
                label=service.status_label,
                text="Disabled",
                style='NotConfigured.TLabel'
            ))
        else:
            self.root.after(0, lambda: self.queue_message(
                action='update_label',
                label=service.status_label,
                text="Not Tested",
                style='NotConfigured.TLabel'
            ))

    def _save_api_keys(self):
        """Save API keys to config file."""
        try:
            # Update config variables
            for api_name, key_var in self.api_keys.items():
                new_key = key_var.get().strip()
                if not new_key:
                    continue
                
                if api_name == 'gemini':
                    config.GEMINI_API_KEYS[0] = new_key
                elif api_name == 'openai':
                    config.OPENAI_API_KEY = new_key
                elif api_name == 'cohere':
                    config.COHERE_API_KEY = new_key
                elif api_name == 'anthropic':
                    config.ANTHROPIC_API_KEY = new_key
            
            # Save to config.py file
            config_path = os.path.join(os.path.dirname(__file__), 'config.py')
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            # Update the lines
            for i, line in enumerate(lines):
                if line.startswith('GEMINI_API_KEYS'):
                    lines[i] = f'GEMINI_API_KEYS = {config.GEMINI_API_KEYS}\n'
                elif line.startswith('OPENAI_API_KEY'):
                    lines[i] = f'OPENAI_API_KEY = "{config.OPENAI_API_KEY}"\n'
                elif line.startswith('COHERE_API_KEY'):
                    lines[i] = f'COHERE_API_KEY = "{config.COHERE_API_KEY}"\n'
                elif line.startswith('ANTHROPIC_API_KEY'):
                    lines[i] = f'ANTHROPIC_API_KEY = "{config.ANTHROPIC_API_KEY}"\n'
            
            # Write back to file
            with open(config_path, 'w') as f:
                f.writelines(lines)
            
            # Show success message
            self.queue_message(
                action='show_info',
                text="API keys saved successfully!"
            )
            
            # Auto-test the APIs
            self._async_test_api_keys()
            
        except Exception as e:
            logging.error(f"Error saving API keys: {str(e)}")
            self.queue_message(
                action='show_error',
                text=f"Error saving API keys: {str(e)}"
            )

    def test_api_connection(self, api_name):
        """Test connection to a specific API."""
        try:
            if api_name == 'gemini':
                api_key = self.api_keys['gemini'].get()
                if not api_key:
                    raise ValueError("API key is empty")
                
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content("Test connection", safety_settings=[])
                    
                    if not response or not response.text:
                        return False
                    return True
                    
                except Exception as e:
                    logging.error(f"Gemini test failed: {str(e)}")
                    raise
            elif api_name == 'openai':
                api_key = self.api_keys['openai'].get()
                if not api_key:
                    raise ValueError("API key is empty")
                    
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Test connection"}],
                    max_tokens=10
                )
                return bool(response.choices)
                
            elif api_name == 'cohere':
                api_key = self.api_keys['cohere'].get()
                if not api_key:
                    raise ValueError("API key is empty")
                    
                co = cohere.Client(api_key)
                response = co.generate(prompt="Test connection", max_tokens=10)
                return bool(response.generations)
                
            elif api_name == 'anthropic':
                api_key = self.api_keys['anthropic'].get()
                if not api_key:
                    raise ValueError("API key is empty")
                    
                client = Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-2",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Test connection"}]
                )
                return bool(response.content)
                
            return False
                
        except Exception as e:
            logging.error(f"API test failed for {api_name}: {str(e)}")
            raise

    def _async_test_api_keys(self):
        """Test API keys asynchronously."""
        def run_tests():
            try:
                self.test_button.config(state='disabled')
                self.queue_message(
                    action='update_test_status',
                    text="Testing APIs..."
                )
                
                # Test each enabled service
                for service_name, service in self.api_services.items():
                    if not service.enabled:
                        continue
                    
                    # Create local copies for lambda
                    current_service = service
                    current_name = service_name
                    
                    # Update status to testing
                    self.root.after(0, lambda: self.queue_message(
                        action='update_label',
                        label=current_service.status_label,
                        text="Testing...",
                        style='Testing.TLabel'
                    ))
                    
                    try:
                        success = self.test_api_connection(current_name)
                        
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
                        logging.error(f"Error testing {current_name}: {str(e)}")
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
                        elif "empty" in error_msg.lower():
                            status_text = "No Key"
                        
                        self.root.after(0, lambda: self.queue_message(
                            action='update_label',
                            label=current_service.status_label,
                            text=status_text,
                            style='Failed.TLabel'
                        ))
                        current_service.status = ServiceStatus.FAILED
                    
                    # Add delay between tests
                    time.sleep(1)
                
                # Re-enable the test button
                self.root.after(0, lambda: self.test_button.config(state='normal'))
                self.root.after(0, lambda: self.queue_message(
                    action='update_test_status',
                    text="API testing complete"
                ))
                
            except Exception as e:
                logging.error(f"Error in API testing thread: {str(e)}")
                self.root.after(0, lambda: self.test_button.config(state='normal'))
                self.root.after(0, lambda: self.queue_message(
                    action='update_test_status',
                    text=f"Error: {str(e)}"
                ))
        
        # Start testing thread
        threading.Thread(target=run_tests, daemon=True).start()

    def _browse_source_directory(self):
        """Open directory browser dialog for source."""
        directory = filedialog.askdirectory()
        if directory:
            self.selected_dir.set(directory)
            
    def _browse_destination_directory(self):
        """Open directory browser dialog for destination."""
        directory = filedialog.askdirectory()
        if directory:
            self.destination_dir.set(directory)

    def _start_processing(self):
        """Start processing files."""
        if not self.selected_dir.get() or not self.destination_dir.get():
            self.queue_message(
                action='show_error',
                text="Please select both source and destination directories"
            )
            return
            
        if not any(service.enabled and service.status == ServiceStatus.WORKING 
                  for service in self.api_services.values()):
            self.queue_message(
                action='show_error',
                text="No working API services available. Please configure and test APIs first."
            )
            return
        
        # Update UI state
        self.processing = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_var.set(0)
        
        # Start processing thread
        threading.Thread(
            target=self._process_files,
            daemon=True
        ).start()
    
    def _stop_processing(self):
        """Stop processing files."""
        self.processing = False
        self.stop_button.config(state='disabled')
        self.start_button.config(state='normal')
        self.queue_message(
            action='update_status',
            text="Processing stopped"
        )
    
    def _process_files(self):
        """Process files in the selected directory."""
        try:
            source_dir = self.selected_dir.get()
            dest_dir = self.destination_dir.get()
            
            if not os.path.exists(source_dir):
                self.queue_message(
                    action='show_error',
                    text="Source directory does not exist"
                )
                return
                
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            
            # Start processing thread
            threading.Thread(
                target=self._process_files_thread,
                args=(source_dir, dest_dir),
                daemon=True
            ).start()
            
        except Exception as e:
            logging.error(f"Error starting file processing: {str(e)}")
            self.queue_message(
                action='show_error',
                text=f"Error starting file processing: {str(e)}"
            )

    def _process_files_thread(self, source_dir, dest_dir):
        """Process files in a separate thread."""
        try:
            # Get list of files
            files = []
            for root, _, filenames in os.walk(source_dir):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
            
            if not files:
                self.queue_message(
                    action='show_error',
                    text="No files found in source directory"
                )
                return
            
            # Update progress bar
            self.root.after(0, lambda: self.progress_bar.configure(maximum=len(files)))
            self.root.after(0, lambda: self.progress_bar.configure(value=0))
            
            # Process each file
            for i, file_path in enumerate(files):
                try:
                    # Update status
                    filename = os.path.basename(file_path)
                    self.root.after(0, lambda: self.status_text.set(
                        f"Processing {filename}..."
                    ))
                    
                    # Get category
                    category, confidence, service = self._categorize_file(file_path)
                    
                    if confidence >= self.confidence_var.get():
                        # Create category directory
                        category_dir = os.path.join(dest_dir, category)
                        if not os.path.exists(category_dir):
                            os.makedirs(category_dir)
                        
                        # Move file
                        dest_path = os.path.join(category_dir, filename)
                        os.rename(file_path, dest_path)
                        
                        # Add to results
                        self.queue_message(
                            action='add_result',
                            values=(dest_path, category, f"{confidence:.2f}", service)
                        )
                    
                    # Update progress
                    self.root.after(0, lambda: self.progress_bar.configure(value=i+1))
                    
                except Exception as e:
                    logging.error(f"Error processing {file_path}: {str(e)}")
                    continue
            
            # Update status
            self.root.after(0, lambda: self.status_text.set(
                f"Processing complete! {len(files)} files processed."
            ))
            
        except Exception as e:
            logging.error(f"Error in processing thread: {str(e)}")
            self.root.after(0, lambda: self.status_text.set(
                f"Error: {str(e)}"
            ))

    def _categorize_file(self, file_path):
        """Categorize a file using available AI services."""
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {str(e)}")
            raise
        
        # Check cache
        if self.use_cache_var.get():
            cache_key = f"{file_path}:{hash(content)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        # Try each enabled service
        errors = []
        for service_name, service in self.api_services.items():
            if not service.enabled or service.status != ServiceStatus.WORKING:
                continue
                
            try:
                # Rate limiting
                current_time = time.time()
                if service.last_request > 0:
                    time_diff = current_time - service.last_request
                    if time_diff < 60 / config.RATE_LIMIT_SETTINGS[service_name]['requests_per_minute']:
                        time.sleep(60 / config.RATE_LIMIT_SETTINGS[service_name]['requests_per_minute'] - time_diff)
                
                # Prepare prompt
                prompt = f"""Analyze this plugin/file and categorize it:

                File: {os.path.basename(file_path)}
                Content: {content[:1000]}...

                Respond with a category and confidence score (0-1).
                Use one of these categories: {', '.join(config.CATEGORIZATION_SETTINGS['category_suggestions'])}
                """
                
                # Get category from API
                if service_name == 'gemini':
                    genai.configure(api_key=self.api_keys['gemini'].get())
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content(prompt, safety_settings=[])
                    result = response.text
                    
                elif service_name == 'openai':
                    client = openai.OpenAI(api_key=self.api_keys['openai'].get())
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=10
                    )
                    result = response.choices[0].message.content
                    
                elif service_name == 'cohere':
                    co = cohere.Client(self.api_keys['cohere'].get())
                    response = co.generate(prompt=prompt)
                    result = response.generations[0].text
                    
                elif service_name == 'anthropic':
                    client = Anthropic(api_key=self.api_keys['anthropic'].get())
                    response = client.messages.create(
                        model="claude-2",
                        max_tokens=100,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    result = response.content[0].text
                
                # Parse result
                for category in config.CATEGORIZATION_SETTINGS['category_suggestions']:
                    if category.lower() in result.lower():
                        confidence = float(result.split('confidence')[-1].split()[0].strip(':()')[:4])
                        if confidence >= self.confidence_var.get():
                            # Cache result
                            if self.use_cache_var.get():
                                self.cache[cache_key] = (category, confidence, service_name)
                            return category, confidence, service_name
                
                errors.append(f"{service_name}: No valid category found")
                
            except Exception as e:
                logging.error(f"Error with {service_name}: {str(e)}")
                errors.append(f"{service_name}: {str(e)}")
                continue
        
        # If all services failed and web search is enabled
        if self.use_search_var.get():
            try:
                # Search for similar plugins
                query = f"{os.path.basename(file_path)} plugin category"
                search_results = search(query, num_results=5)
                
                # Analyze search results
                categories = {}
                for url in search_results:
                    response = requests.get(url)
                    text = response.text.lower()
                    for category in config.CATEGORIZATION_SETTINGS['category_suggestions']:
                        if category.lower() in text:
                            categories[category] = categories.get(category, 0) + 1
                
                if categories:
                    best_category = max(categories.items(), key=lambda x: x[1])[0]
                    confidence = categories[best_category] / 5
                    if confidence >= self.confidence_var.get():
                        return best_category, confidence, "Web Search"
                
            except Exception as e:
                logging.error(f"Error in web search: {str(e)}")
                errors.append(f"Web Search: {str(e)}")
        
        # If all methods failed
        category = config.CATEGORIZATION_SETTINGS['default_category']
        confidence = 0.0
        service_name = f"Default (Errors: {', '.join(errors)})"
        
        # Cache result
        if self.use_cache_var.get():
            self.cache[cache_key] = (category, confidence, service_name)
        
        return category, confidence, service_name

    def _export_results(self):
        """Export results to a JSON file."""
        try:
            # Get all items from the tree
            items = []
            for item_id in self.results_tree.get_children():
                values = self.results_tree.item(item_id)['values']
                items.append({
                    'file': values[0],
                    'category': values[1],
                    'confidence': float(values[2]),
                    'service': values[3]
                })
            
            if not items:
                self.queue_message(
                    action='show_error',
                    text="No results to export"
                )
                return
            
            # Get save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filename:
                return
            
            # Save results
            with open(filename, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'directory': self.selected_dir.get(),
                    'total_files': len(items),
                    'settings': {
                        'confidence_threshold': self.confidence_var.get(),
                        'batch_size': self.batch_size_var.get(),
                        'use_web_search': self.use_search_var.get(),
                        'use_cache': self.use_cache_var.get()
                    },
                    'results': items
                }, f, indent=4)
            
            self.queue_message(
                action='show_info',
                text=f"Results exported to {filename}"
            )
            
        except Exception as e:
            logging.error(f"Error exporting results: {str(e)}")
            self.queue_message(
                action='show_error',
                text=f"Error exporting results: {str(e)}"
            )
    
    def _clear_results(self):
        """Clear all results from the tree."""
        try:
            if not self.results_tree.get_children():
                return
                
            if messagebox.askyesno(
                "Confirm Clear",
                "Are you sure you want to clear all results?"
            ):
                for item in self.results_tree.get_children():
                    self.results_tree.delete(item)
                
                self.queue_message(
                    action='show_info',
                    text="Results cleared"
                )
        except Exception as e:
            logging.error(f"Error clearing results: {str(e)}")
    
    def _add_category(self):
        """Add a new category to the list."""
        try:
            category = self.new_category.get().strip()
            if not category:
                return
                
            # Check if category already exists
            existing = list(self.category_list.get(0, tk.END))
            if category in existing:
                self.queue_message(
                    action='show_error',
                    text="Category already exists"
                )
                return
            
            # Add to list and clear entry
            self.category_list.insert(tk.END, category)
            self.new_category.set("")
            
            # Update config
            config.CATEGORIZATION_SETTINGS['category_suggestions'].append(category)
            
        except Exception as e:
            logging.error(f"Error adding category: {str(e)}")
    
    def _remove_category(self):
        """Remove selected category from the list."""
        try:
            selection = self.category_list.curselection()
            if not selection:
                return
                
            if messagebox.askyesno(
                "Confirm Remove",
                "Are you sure you want to remove this category?"
            ):
                category = self.category_list.get(selection)
                self.category_list.delete(selection)
                
                # Update config
                if category in config.CATEGORIZATION_SETTINGS['category_suggestions']:
                    config.CATEGORIZATION_SETTINGS['category_suggestions'].remove(category)
                
        except Exception as e:
            logging.error(f"Error removing category: {str(e)}")
    
    def _clear_cache(self):
        """Clear the categorization cache."""
        try:
            if not self.cache:
                self.queue_message(
                    action='show_info',
                    text="Cache is already empty"
                )
                return
                
            if messagebox.askyesno(
                "Confirm Clear Cache",
                f"Are you sure you want to clear {len(self.cache)} cached results?"
            ):
                self.cache.clear()
                self.cache_size_label.config(text="Cache Size: 0 MB")
                
                self.queue_message(
                    action='show_info',
                    text="Cache cleared"
                )
        except Exception as e:
            logging.error(f"Error clearing cache: {str(e)}")
    
    def _reset_settings(self):
        """Reset all settings to defaults."""
        try:
            if messagebox.askyesno(
                "Confirm Reset",
                "Are you sure you want to reset all settings to defaults?"
            ):
                # Reset variables
                self.confidence_var.set(config.CATEGORIZATION_SETTINGS['min_confidence'])
                self.batch_size_var.set(config.RATE_LIMIT_SETTINGS['gemini']['batch_size'])
                self.use_search_var.set(config.CATEGORIZATION_SETTINGS['fallback_to_search'])
                self.use_cache_var.set(config.CACHE_SETTINGS['enabled'])
                self.dark_mode.set(False)
                
                # Clear API keys
                for key_var in self.api_keys.values():
                    key_var.set("")
                
                # Reset services
                for service in self.api_services.values():
                    service.enabled = True
                    service.status = ServiceStatus.NOT_CONFIGURED
                    service.status_label.config(
                        text="Not Configured",
                        style='NotConfigured.TLabel'
                    )
                
                # Clear cache
                self.cache.clear()
                
                # Reset categories
                self.category_list.delete(0, tk.END)
                for category in config.CATEGORIZATION_SETTINGS['category_suggestions']:
                    self.category_list.insert(tk.END, category)
                
                # Apply theme
                self._apply_theme()
                
                self.queue_message(
                    action='show_info',
                    text="All settings reset to defaults"
                )
        except Exception as e:
            logging.error(f"Error resetting settings: {str(e)}")
            self.queue_message(
                action='show_error',
                text=f"Error resetting settings: {str(e)}"
            )

    def _on_closing(self):
        """Handle application shutdown."""
        try:
            # Save settings
            self._save_settings()
            
            # Clean up Gemini resources
            try:
                genai.reset_session()
            except Exception as e:
                logging.warning(f"Failed to reset Gemini session: {e}")
            
            # Destroy the window
            self.root.destroy()
            
        except Exception as e:
            logging.error(f"Error during shutdown: {str(e)}")
            self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Advanced Directory Categorizer V8")
    root.geometry("800x600")
    
    app = PluginCategorizerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app._on_closing)  # Handle window close
    root.mainloop()
