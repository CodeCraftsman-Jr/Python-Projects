import os
import shutil
from anthropic import Anthropic
import google.generativeai as genai
import cohere
from pathlib import Path
import json
from typing import Dict, List, Optional
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import threading
from datetime import datetime
import webbrowser
import config
import time
from predefined_categories import find_matching_category
import concurrent.futures

def get_settings_file_path():
    """Get the absolute path to the settings file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "categorizer_settings.json")

def load_settings():
    """Load settings from the settings file."""
    settings_file = get_settings_file_path()
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
    return {}

def save_settings(settings):
    """Save settings to the settings file."""
    settings_file = get_settings_file_path()
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        
        # Save settings with proper encoding
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings: {str(e)}")
        raise  # Re-raise to show error in GUI

class APITester:
    @staticmethod
    def test_anthropic():
        try:
            api_key = config.get_api_key("ANTHROPIC_API_KEY")
            if not api_key:
                return False, "API key not found"
                
            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-3",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'test'"}]
            )
            return True, "Success"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def test_gemini():
        """Test the Gemini API connection with fallback to multiple keys."""
        for i in range(1, 6):  # Try keys 1 through 5
            try:
                key = config.get_api_key(f"GEMINI_API_KEY_{i}")
                if not key:
                    continue
                    
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content("Test")
                
                if response and response.text:
                    return True, f"Connection successful using API Key {i}"
                    
            except Exception as e:
                error_str = str(e).lower()
                if "quota exceeded" in error_str and i < 5:
                    continue  # Try next key
                return False, str(e)
                
        return False, "All Gemini API keys failed or quota exceeded"

    @staticmethod
    def test_cohere():
        try:
            api_key = config.get_api_key("COHERE_API_KEY")
            if not api_key:
                return False, "API key not found"
                
            co = cohere.Client(api_key)
            response = co.generate(prompt="Say 'test'", max_tokens=10)
            return True, "Success"
        except Exception as e:
            return False, str(e)

class AIModelSelector(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("AI Model Selection")
        self.geometry("500x400")
        self.grab_set()  # Make window modal
        
        # Initialize variables
        self.selected_model = ctk.StringVar(value="anthropic")  # Default to Anthropic
        self.model_configs = {
            "anthropic": {
                "name": "Anthropic Claude",
                "model": "claude-3",
                "key_name": "ANTHROPIC_API_KEY"
            },
            "gemini": {
                "name": "Google Gemini Pro",
                "model": "gemini-pro",
                "key_name": "GEMINI_API_KEY"
            },
            "cohere": {
                "name": "Cohere",
                "model": "command",
                "key_name": "COHERE_API_KEY"
            }
        }
        
        # Check API keys and update configs
        for model_id, cfg in self.model_configs.items():
            cfg["api_key"] = config.get_api_key(cfg["key_name"])
        
        # Create widgets
        self.create_widgets()
        
        # Center the window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Select AI Model for Plugin Categorization",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=20)

        # Model selection frame
        model_frame = ctk.CTkFrame(self)
        model_frame.pack(fill="x", padx=20, pady=10)

        # Radio buttons for each model
        for model_id, config in self.model_configs.items():
            model_radio = ctk.CTkRadioButton(
                model_frame,
                text=config["name"],
                variable=self.selected_model,
                value=model_id
            )
            model_radio.pack(anchor="w", pady=5)

            # Show API key status
            has_key = bool(config.get("api_key"))
            status_text = "✅ API Key configured" if has_key else "❌ API Key not found"
            status_color = "green" if has_key else "red"
            
            status_label = ctk.CTkLabel(
                model_frame,
                text=f"    {status_text}",
                text_color=status_color
            )
            status_label.pack(anchor="w", padx=30)

            if not has_key:
                config_btn = ctk.CTkButton(
                    model_frame,
                    text="Configure API Key",
                    command=lambda k=config["key_name"]: self.configure_api_key(k),
                    width=120
                )
                config_btn.pack(anchor="w", padx=30, pady=(0, 10))

        # Description
        desc_frame = ctk.CTkFrame(self)
        desc_frame.pack(fill="x", padx=20, pady=10)
        
        desc_label = ctk.CTkLabel(
            desc_frame,
            text="Model Descriptions:",
            font=("Helvetica", 12, "bold")
        )
        desc_label.pack(anchor="w", pady=5)
        
        descriptions = {
            "Anthropic Claude": "Best for understanding context and providing detailed categorization",
            "Google Gemini Pro": "Efficient for processing multiple plugins quickly",
            "Cohere": "Good balance of speed and accuracy"
        }
        
        for model, desc in descriptions.items():
            model_desc = ctk.CTkLabel(
                desc_frame,
                text=f"• {model}: {desc}",
                wraplength=400,
                justify="left"
            )
            model_desc.pack(anchor="w", pady=2)

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        test_btn = ctk.CTkButton(
            button_frame,
            text="Test Selected Model",
            command=self.test_model
        )
        test_btn.pack(side="left", padx=5)
        
        ok_btn = ctk.CTkButton(
            button_frame,
            text="OK",
            command=self.on_ok
        )
        ok_btn.pack(side="right", padx=5)

    def configure_api_key(self, key_name):
        """Open API Key Manager window."""
        api_key_manager = APIKeyManager()
        api_key_manager.grab_set()  # Make it modal
        api_key_manager.wait_window()
        
        # Refresh the window after API key configuration
        self.destroy()
        self.__init__(self.master)

    def test_model(self):
        model_id = self.selected_model.get()
        config = self.model_configs[model_id]
        
        if not config.get("api_key"):
            messagebox.showerror("Error", f"Please configure the API key for {config['name']} first!")
            return
        
        def run_test():
            try:
                if model_id == "anthropic":
                    success, message = APITester.test_anthropic()
                elif model_id == "gemini":
                    success, message = APITester.test_gemini()
                else:  # cohere
                    success, message = APITester.test_cohere()
                
                status = "✅ Test successful" if success else f"❌ Test failed: {message}"
                messagebox.showinfo("Test Result", f"{config['name']}\n\n{status}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error testing {config['name']}: {str(e)}")
        
        threading.Thread(target=run_test).start()

    def on_ok(self):
        """Validate selection before closing."""
        model_id = self.selected_model.get()
        config = self.model_configs[model_id]
        
        if not config.get("api_key"):
            if not messagebox.askyesno("Warning", 
                f"No API key configured for {config['name']}. Would you like to configure it now?"):
                return
            self.configure_api_key(config["key_name"])
        else:
            self.destroy()

    def get_selected_config(self):
        config = self.model_configs[self.selected_model.get()]
        if not config.get("api_key"):
            return None
        return config

class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window  # in seconds
        self.requests = []
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            # Remove old requests
            self.requests = [req for req in self.requests if now - req < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                wait_time = self.requests[0] + self.time_window - now
                if wait_time > 0:
                    time.sleep(wait_time)
                    # After waiting, clean up old requests again
                    self.requests = [req for req in self.requests if time.time() - req < self.time_window]
            
            self.requests.append(now)

class PluginCategorizer:
    def __init__(self, source_dir=None, dest_dir=None, batch_size=50, gui=None, categories_file="categories.json"):
        """Initialize the plugin categorizer."""
        self.source_dir = Path(source_dir) if source_dir else None
        self.dest_dir = Path(dest_dir) if dest_dir else None
        self.batch_size = batch_size
        self.gui = gui
        self.categories_file = Path(categories_file)
        self.categories_cache = self.load_categories_cache()
        self.is_processing = False
        self.ai_clients = {}
        self.quota_exhausted = set()
        self.rate_limiters = {}
        self.move_status = {
            'total': 0,
            'moved': 0,
            'failed': 0,
            'skipped': 0,
            'failures': []
        }
        
        # Load existing categories
        self.load_existing_categories()
        
        # Load selected APIs from settings
        settings = load_settings()
        selected_apis = settings.get("selected_apis", {
            "gemini_1": True,
            "gemini_2": False,
            "gemini_3": False,
            "gemini_4": False,
            "gemini_5": False,
            "anthropic": True,
            "cohere": True
        })
        
        # Initialize selected AI clients
        if selected_apis.get("anthropic", True):
            anthropic_key = config.get_api_key("ANTHROPIC_API_KEY")
            if anthropic_key:
                try:
                    import anthropic
                    self.ai_clients["anthropic"] = {
                        "client": anthropic.Anthropic(api_key=anthropic_key),
                        "model": "claude-3",
                        "name": "Anthropic Claude"
                    }
                except Exception as e:
                    if self.gui:
                        self.gui.add_log(f"Error initializing Anthropic client: {str(e)}")

        # Initialize selected Gemini clients
        for i in range(1, 6):
            if selected_apis.get(f"gemini_{i}", False):
                key = config.get_api_key(f"GEMINI_API_KEY_{i}")
                if key:
                    try:
                        import google.generativeai as genai
                        client_id = f"gemini_{i}"
                        genai.configure(api_key=key)
                        self.ai_clients[client_id] = {
                            "client": genai,
                            "model": "gemini-pro",
                            "name": f"Google Gemini {i}"
                        }
                    except Exception as e:
                        if self.gui:
                            self.gui.add_log(f"Error initializing Gemini client {i}: {str(e)}")

        if selected_apis.get("cohere", True):
            cohere_key = config.get_api_key("COHERE_API_KEY")
            if cohere_key:
                try:
                    import cohere
                    self.ai_clients["cohere"] = {
                        "client": cohere.Client(api_key=cohere_key),
                        "name": "Cohere"
                    }
                except Exception as e:
                    if self.gui:
                        self.gui.add_log(f"Error initializing Cohere client: {str(e)}")
        
        # Initialize rate limiters for active APIs
        self.rate_limiters = {}
        for api_id in self.ai_clients.keys():
            if api_id.startswith("gemini_"):
                self.rate_limiters[api_id] = RateLimiter(20, 60)  # 20 requests per minute each
            elif api_id == "anthropic":
                self.rate_limiters[api_id] = RateLimiter(3, 60)
            elif api_id == "cohere":
                self.rate_limiters[api_id] = RateLimiter(30, 60)
        
    def load_categories_cache(self):
        """Load categories from cache file."""
        try:
            if self.categories_file and self.categories_file.exists():
                with open(self.categories_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.log_error(f"Error loading categories cache: {str(e)}")
            return {}

    def save_categories_cache(self):
        """Save categories to cache file."""
        try:
            if self.categories_file:
                with open(self.categories_file, 'w') as f:
                    json.dump(self.categories_cache, f, indent=4)
        except Exception as e:
            self.log_error(f"Error saving categories cache: {str(e)}")

    def load_existing_categories(self):
        """Load existing categories from the destination directory."""
        try:
            if not self.dest_dir:
                self.log_general("Destination directory not set, skipping category load")
                return
                
            if not self.dest_dir.exists():
                self.log_general("Destination directory does not exist yet")
                return
                
            self.existing_categories = set()
            for item in self.dest_dir.iterdir():
                if item.is_dir():
                    self.existing_categories.add(item.name)
                    
            if self.existing_categories:
                self.log_general(f"Loaded {len(self.existing_categories)} existing categories")
            
        except Exception as e:
            self.log_error(f"Error loading existing categories: {str(e)}")

    def process(self, plugin_names: list) -> None:
        """Process a list of plugins."""
        try:
            # Ensure source and destination directories exist
            if not self.source_dir or not self.dest_dir:
                self.log_error("Source or destination directory not set")
                return
                
            if not self.source_dir.exists():
                self.log_error(f"Source directory does not exist: {self.source_dir}")
                return
                
            if not self.dest_dir.exists():
                try:
                    self.dest_dir.mkdir(parents=True, exist_ok=True)
                    self.log_general(f"Created destination directory: {self.dest_dir}")
                except Exception as e:
                    self.log_error(f"Failed to create destination directory: {str(e)}")
                    return
            
            self.log_general(f"Starting to process {len(plugin_names)} plugins")
            self.log_general(f"Source directory: {self.source_dir}")
            self.log_general(f"Destination directory: {self.dest_dir}")
            
            self.move_status = {
                'total': 0,
                'moved': 0,
                'failed': 0,
                'skipped': 0,
                'failures': []
            }
            
            # Get categories for all plugins
            categories = self.get_categories_for_batch(plugin_names)
            if not categories:
                self.log_error("Failed to get categories for plugins")
                return
            
            self.log_general(f"Successfully got categories for {len(categories)} plugins")
            self.log_general("Moving plugins to their categories...")
            
            for plugin_name in plugin_names:
                if not self.is_processing:
                    self.log_general("Processing stopped by user")
                    break
                
                if plugin_name in categories:
                    category = categories[plugin_name]
                    self.log_move(f"Moving {plugin_name} to category: {category}")
                    success = self.move_plugin_to_category(plugin_name, category)
                    if success:
                        self.log_move(f"Successfully moved {plugin_name} to {category}")
                    else:
                        self.log_error(f"Failed to move {plugin_name} to {category}")
                else:
                    self.log_error(f"No category found for {plugin_name}")
                    self.move_status['failed'] += 1
                    self.move_status['failures'].append(f"{plugin_name}: No category found")
            
            # Log final status
            self.log_general("\nProcessing completed!")
            self.log_general(f"Total plugins: {self.move_status['total']}")
            self.log_general(f"Successfully moved: {self.move_status['moved']}")
            self.log_general(f"Failed: {self.move_status['failed']}")
            self.log_general(f"Skipped: {self.move_status['skipped']}")
            
            if self.move_status['failures']:
                self.log_error("\nFailed plugins:")
                for failure in self.move_status['failures']:
                    self.log_error(f"- {failure}")
            
        except Exception as e:
            self.log_error(f"Error during processing: {str(e)}")
            raise

    def move_plugin_to_category(self, plugin_name: str, category: str) -> bool:
        """Move plugin to its category folder with status tracking."""
        try:
            # Convert to absolute paths
            source_path = self.source_dir.resolve() / plugin_name
            dest_path = self.dest_dir.resolve() / category / plugin_name
            
            self.log_general(f"Moving plugin from {source_path} to {dest_path}")
            self.move_status['total'] += 1
            
            # Check source exists
            if not source_path.exists():
                self.log_error(f"Source path does not exist: {source_path}")
                self.move_status['failed'] += 1
                self.move_status['failures'].append(f"{plugin_name}: Source not found")
                return False
            
            # Ensure source is a directory
            if not source_path.is_dir():
                self.log_error(f"{plugin_name} is not a directory at {source_path}")
                self.move_status['failed'] += 1
                self.move_status['failures'].append(f"{plugin_name}: Not a directory")
                return False
            
            # Create category directory
            category_path = self.dest_dir.resolve() / category
            try:
                category_path.mkdir(parents=True, exist_ok=True)
                self.log_general(f"Created/verified category directory: {category_path}")
            except Exception as e:
                self.log_error(f"Failed to create category directory {category_path}: {str(e)}")
                self.move_status['failed'] += 1
                self.move_status['failures'].append(f"{plugin_name}: Failed to create category directory")
                return False
            
            # Check if destination exists
            if dest_path.exists():
                self.log_move(f"Plugin already exists in category: {dest_path}")
                self.move_status['skipped'] += 1
                return False
            
            # Move the plugin folder
            try:
                # First try with shutil.move
                self.log_general(f"Attempting to move {source_path} to {dest_path}")
                shutil.move(str(source_path), str(dest_path))
                self.log_move(f"Successfully moved {plugin_name} to {category}")
                self.move_status['moved'] += 1
                return True
                
            except PermissionError:
                self.log_error(f"Permission denied when moving {plugin_name}")
                self.move_status['failed'] += 1
                self.move_status['failures'].append(f"{plugin_name}: Permission denied")
                return False
                
            except Exception as e:
                # If shutil.move fails, try alternative approach
                try:
                    self.log_general(f"First attempt failed, trying alternative move method")
                    # Try to copy first then remove original
                    shutil.copytree(str(source_path), str(dest_path))
                    shutil.rmtree(str(source_path))
                    self.log_move(f"Successfully moved {plugin_name} to {category} using alternative method")
                    self.move_status['moved'] += 1
                    return True
                except Exception as e2:
                    self.log_error(f"Error moving {plugin_name}: {str(e2)}")
                    self.move_status['failed'] += 1
                    self.move_status['failures'].append(f"{plugin_name}: {str(e2)}")
                    return False
            
        except Exception as e:
            self.log_error(f"Error processing {plugin_name}: {str(e)}")
            self.move_status['failed'] += 1
            self.move_status['failures'].append(f"{plugin_name}: {str(e)}")
            return False

    def log_error(self, message):
        """Log an error message."""
        if self.gui:
            self.gui.add_log(message, "error")
        print(f"Error: {message}")
    
    def log_api(self, message):
        """Log an API-related message."""
        if self.gui:
            self.gui.add_log(message, "api")
        print(f"API: {message}")
    
    def log_move(self, message):
        """Log a plugin move operation."""
        if self.gui:
            self.gui.add_log(message, "move")
        print(f"Move: {message}")
    
    def log_general(self, message):
        """Log a general message."""
        if self.gui:
            self.gui.add_log(message, "general")
        print(message)
    
    def get_categories_for_batch(self, plugin_names):
        """Get categories for a batch of plugins using all available models."""
        self.log_general(f"Processing batch of {len(plugin_names)} plugins")
        
        # Try Gemini first with fallback
        for i in range(1, 6):
            gemini_key = f"gemini_{i}"
            if gemini_key in self.ai_clients:
                self.log_api(f"Trying Gemini API (Key {i})...")
                try:
                    client = self.ai_clients[gemini_key]["client"]
                    model = client.GenerativeModel('gemini-pro')
                    prompt = f"Given these plugin names, suggest a single-word category for each that best describes its purpose. Only output the category name, nothing else. Plugin names: {', '.join(plugin_names)}"
                    
                    response = model.generate_content(prompt)
                    
                    if response and hasattr(response, 'text'):
                        categories = response.text.strip().split('\n')
                        categories = {name: cat.strip() for name, cat in zip(plugin_names, categories)}
                        if categories:
                            self.log_api(f"Successfully got categories from Gemini (Key {i})")
                            return categories
                            
                except Exception as e:
                    error_str = str(e).lower()
                    if "quota exceeded" in error_str and i < 5:
                        self.log_error(f"Gemini API Key {i} quota exceeded, trying next key...")
                        continue
                    self.log_error(f"Error with Gemini API (Key {i}): {str(e)}")
        
        # Try Anthropic as backup
        if "anthropic" in self.ai_clients:
            self.log_api("Trying Anthropic API...")
            categories = self.get_categories_from_anthropic(plugin_names)
            if categories:
                self.log_api("Successfully got categories from Anthropic")
                return categories
            self.log_api("Anthropic API failed, trying next API...")
        
        # Try Cohere as last resort
        if "cohere" in self.ai_clients:
            self.log_api("Trying Cohere API...")
            categories = self.get_categories_from_cohere(plugin_names)
            if categories:
                self.log_api("Successfully got categories from Cohere")
                return categories
            self.log_api("Cohere API failed")
        
        self.log_error("All APIs failed to generate categories")
        return {}

    def export_settings(self, filename: str = None) -> str:
        """Export current settings to a JSON file."""
        try:
            if filename is None:
                filename = "categorizer_settings.json"
                
            settings = {
                "source_dir": str(self.source_dir) if self.source_dir else None,
                "dest_dir": str(self.dest_dir) if self.dest_dir else None,
                "batch_size": self.batch_size,
                "categories_file": str(self.categories_file) if self.categories_file else None
            }
            
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=4)
            
            self.log_general(f"Settings exported to: {filename}")
            return filename
            
        except Exception as e:
            self.log_error(f"Error exporting settings: {str(e)}")
            raise

    def import_settings(self, filename: str = None) -> dict:
        """Import settings from a JSON file."""
        try:
            if filename is None:
                filename = "categorizer_settings.json"
                
            if not os.path.exists(filename):
                self.log_error(f"Settings file not found: {filename}")
                return {}
                
            with open(filename, 'r') as f:
                settings = json.load(f)
            
            # Update instance variables
            if "source_dir" in settings and settings["source_dir"]:
                self.source_dir = Path(settings["source_dir"])
            if "dest_dir" in settings and settings["dest_dir"]:
                self.dest_dir = Path(settings["dest_dir"])
            if "batch_size" in settings:
                self.batch_size = settings["batch_size"]
            if "categories_file" in settings and settings["categories_file"]:
                self.categories_file = Path(settings["categories_file"])
            
            self.log_general(f"Settings imported from: {filename}")
            return settings
            
        except Exception as e:
            self.log_error(f"Error importing settings: {str(e)}")
            return {}

    def create_category_folder(self, category: str) -> Path:
        """Create a category folder if it doesn't exist."""
        try:
            if not self.dest_dir:
                raise ValueError("Destination directory not set")
                
            category_path = self.dest_dir.resolve() / category
            category_path.mkdir(parents=True, exist_ok=True)
            self.log_general(f"Created/verified category folder: {category}")
            return category_path
            
        except Exception as e:
            self.log_error(f"Error creating category folder {category}: {str(e)}")
            raise

    def get_categories_from_anthropic(self, plugin_names):
        """Get categories from Anthropic API."""
        try:
            if "anthropic" not in self.ai_clients:
                self.log_error("Anthropic API client not initialized")
                return {}
                
            self.log_api("Requesting categories from Anthropic API...")
            client = self.ai_clients["anthropic"]["client"]
            prompt = f"Given these plugin names, suggest a single-word category for each that best describes its purpose. Only output the category name, nothing else. Plugin names: {', '.join(plugin_names)}"
            
            response = client.messages.create(
                model="claude-3-opus-20240229",  # Updated to latest model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0
            )
            
            if hasattr(response, 'content') and response.content:
                categories = response.content[0].text.strip().split('\n')
                result = {name: category.strip() for name, category in zip(plugin_names, categories)}
                self.log_api(f"Anthropic API returned {len(result)} categories")
                return result
            
            return {}
            
        except Exception as e:
            self.log_error(f"Error with Anthropic API: {str(e)}")
            return {}
    
    def get_categories_from_gemini(self, plugin_names):
        """Get categories from Google Gemini API with fallback to multiple keys."""
        for i in range(1, 6):  # Try keys 1 through 5
            client_key = f"gemini_{i}"
            if client_key not in self.ai_clients:
                continue
                
            try:
                self.log_api(f"Requesting categories from Gemini API (Key {i})...")
                client = self.ai_clients[client_key]["client"]
                model = client.GenerativeModel('gemini-pro')  # Create model instance
                prompt = f"Given these plugin names, suggest a single-word category for each that best describes its purpose. Only output the category name, nothing else. Plugin names: {', '.join(plugin_names)}"
                
                response = model.generate_content(prompt)  # Use model instance to generate
                
                if response and hasattr(response, 'text'):
                    categories = response.text.strip().split('\n')
                    result = {name: category.strip() for name, category in zip(plugin_names, categories)}
                    self.log_api(f"Gemini API (Key {i}) returned {len(result)} categories")
                    return result
                    
            except Exception as e:
                error_str = str(e).lower()
                if "quota exceeded" in error_str and i < 5:
                    self.log_error(f"Gemini API Key {i} quota exceeded, trying next key...")
                    continue
                self.log_error(f"Error with Gemini API (Key {i}): {str(e)}")
                
        return {}
    
    def get_categories_from_cohere(self, plugin_names):
        """Get categories from Cohere API."""
        try:
            if "cohere" not in self.ai_clients:
                self.log_error("Cohere API client not initialized")
                return {}
                
            self.log_api("Requesting categories from Cohere API...")
            client = self.ai_clients["cohere"]["client"]
            
            # Split into smaller batches to handle rate limits
            batch_size = 5  # Process 5 plugins at a time
            results = {}
            
            for i in range(0, len(plugin_names), batch_size):
                batch = plugin_names[i:i + batch_size]
                prompt = f"Given these plugin names, suggest a single-word category for each that best describes its purpose. Only output the category name, nothing else. Plugin names: {', '.join(batch)}"
                
                try:
                    response = client.generate(
                        prompt=prompt,
                        max_tokens=len(batch) * 10,
                        temperature=0,
                        num_generations=1
                    )
                    
                    if response and response.generations:
                        categories = response.generations[0].text.strip().split('\n')
                        batch_results = {name: category.strip() for name, category in zip(batch, categories)}
                        results.update(batch_results)
                        self.log_api(f"Cohere API processed batch {i//batch_size + 1}")
                        
                    # Add a small delay between batches
                    if i + batch_size < len(plugin_names):
                        time.sleep(1)
                        
                except Exception as e:
                    if "429" in str(e):  # Rate limit hit
                        self.log_error("Cohere API rate limit reached, waiting 5 seconds...")
                        time.sleep(5)  # Wait longer on rate limit
                        try:
                            # Retry once
                            response = client.generate(
                                prompt=prompt,
                                max_tokens=len(batch) * 10,
                                temperature=0,
                                num_generations=1
                            )
                            if response and response.generations:
                                categories = response.generations[0].text.strip().split('\n')
                                batch_results = {name: category.strip() for name, category in zip(batch, categories)}
                                results.update(batch_results)
                        except:
                            self.log_error(f"Failed to process batch after retry: {batch}")
                    else:
                        self.log_error(f"Error processing batch: {str(e)}")
            
            self.log_api(f"Cohere API returned {len(results)} categories total")
            return results
            
        except Exception as e:
            self.log_error(f"Error with Cohere API: {str(e)}")
            return {}

class APIKeyManager(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        
        self.title("API Key Manager")
        self.geometry("600x900")  # Made taller for additional controls
        
        # Create main frame with scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # API Selection Section
        self.selection_frame = ctk.CTkFrame(self.main_frame)
        self.selection_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(self.selection_frame, text="Select APIs to Use", font=("Arial", 16, "bold")).pack(pady=5)
        
        try:
            # Load current API selections from settings
            settings = load_settings()
            selected_apis = settings.get("selected_apis", {
                "gemini_1": True,
                "gemini_2": False,
                "gemini_3": False,
                "gemini_4": False,
                "gemini_5": False,
                "anthropic": True,
                "cohere": True
            })
            
            # Gemini API Selection
            self.gemini_selections = {}
            for i in range(1, 6):
                var = ctk.BooleanVar(value=selected_apis.get(f"gemini_{i}", False))
                cb = ctk.CTkCheckBox(
                    self.selection_frame,
                    text=f"Use Gemini API {i}",
                    variable=var,
                    onvalue=True,
                    offvalue=False
                )
                cb.pack(anchor="w", padx=10, pady=2)
                self.gemini_selections[f"gemini_{i}"] = var
            
            # Other APIs Selection
            self.anthropic_var = ctk.BooleanVar(value=selected_apis.get("anthropic", True))
            self.cohere_var = ctk.BooleanVar(value=selected_apis.get("cohere", True))
            
            ctk.CTkCheckBox(
                self.selection_frame,
                text="Use Anthropic API",
                variable=self.anthropic_var,
                onvalue=True,
                offvalue=False
            ).pack(anchor="w", padx=10, pady=2)
            
            ctk.CTkCheckBox(
                self.selection_frame,
                text="Use Cohere API",
                variable=self.cohere_var,
                onvalue=True,
                offvalue=False
            ).pack(anchor="w", padx=10, pady=2)
            
        except Exception as e:
            self.status_label = ctk.CTkLabel(self.main_frame, text=f"Error loading settings: {str(e)}", text_color="red")
            self.status_label.pack(pady=10)
            return
        
        # Gemini API Keys Section
        self.gemini_frame = ctk.CTkFrame(self.main_frame)
        self.gemini_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(self.gemini_frame, text="Gemini API Keys", font=("Arial", 16, "bold")).pack(pady=5)
        
        self.gemini_keys = []
        for i in range(1, 6):
            key_frame = ctk.CTkFrame(self.gemini_frame)
            key_frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(key_frame, text=f"Gemini API Key {i}:").pack(side="left", padx=5)
            key_var = ctk.StringVar(value=config.get_api_key(f"GEMINI_API_KEY_{i}") or "")
            key_entry = ctk.CTkEntry(key_frame, width=300, show="*")
            key_entry.pack(side="left", padx=5)
            key_entry.insert(0, key_var.get())
            
            # Add test button for each key
            test_btn = ctk.CTkButton(
                key_frame, 
                text="Test", 
                width=60,
                command=lambda e=key_entry, i=i: self.test_gemini_key(e.get(), i)
            )
            test_btn.pack(side="left", padx=5)
            
            self.gemini_keys.append((f"GEMINI_API_KEY_{i}", key_entry))
        
        # Other APIs Section
        other_apis_frame = ctk.CTkFrame(self.main_frame)
        other_apis_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(other_apis_frame, text="Other APIs", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Anthropic
        anthropic_frame = ctk.CTkFrame(other_apis_frame)
        anthropic_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(anthropic_frame, text="Anthropic API Key:").pack(side="left", padx=5)
        self.anthropic_key = ctk.CTkEntry(anthropic_frame, width=300, show="*")
        self.anthropic_key.pack(side="left", padx=5)
        self.anthropic_key.insert(0, config.get_api_key("ANTHROPIC_API_KEY") or "")
        
        # Add test button for Anthropic
        ctk.CTkButton(
            anthropic_frame, 
            text="Test", 
            width=60,
            command=lambda: self.test_anthropic_key(self.anthropic_key.get())
        ).pack(side="left", padx=5)
        
        # Cohere
        cohere_frame = ctk.CTkFrame(other_apis_frame)
        cohere_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(cohere_frame, text="Cohere API Key:").pack(side="left", padx=5)
        self.cohere_key = ctk.CTkEntry(cohere_frame, width=300, show="*")
        self.cohere_key.pack(side="left", padx=5)
        self.cohere_key.insert(0, config.get_api_key("COHERE_API_KEY") or "")
        
        # Add test button for Cohere
        ctk.CTkButton(
            cohere_frame, 
            text="Test", 
            width=60,
            command=lambda: self.test_cohere_key(self.cohere_key.get())
        ).pack(side="left", padx=5)
        
        # Status Label
        self.status_label = ctk.CTkLabel(self.main_frame, text="")
        self.status_label.pack(pady=10)
        
        # Save Button
        ctk.CTkButton(
            self.main_frame,
            text="Save API Keys",
            command=self.save_keys
        ).pack(pady=10)

    def test_gemini_key(self, key, index):
        """Test a Gemini API key."""
        if not key:
            self.status_label.configure(text=f"Please enter Gemini API Key {index}")
            return
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Test")
            self.status_label.configure(text=f"✓ Gemini API Key {index} is valid", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"✗ Gemini API Key {index} error: {str(e)}", text_color="red")

    def test_anthropic_key(self, key):
        """Test the Anthropic API key."""
        if not key:
            self.status_label.configure(text="Please enter Anthropic API Key")
            return
            
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=key)
            response = client.messages.create(
                model="claude-3",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            self.status_label.configure(text="✓ Anthropic API Key is valid", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"✗ Anthropic API Key error: {str(e)}", text_color="red")

    def test_cohere_key(self, key):
        """Test the Cohere API key."""
        if not key:
            self.status_label.configure(text="Please enter Cohere API Key")
            return
            
        try:
            import cohere
            client = cohere.Client(api_key=key)
            response = client.generate(prompt="Test")
            self.status_label.configure(text="✓ Cohere API Key is valid", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"✗ Cohere API Key error: {str(e)}", text_color="red")

    def save_keys(self):
        """Save all API keys and selections to config."""
        try:
            # Save API keys as before
            for key_name, key_entry in self.gemini_keys:
                if key_entry.get():
                    config.save_api_key(key_name, key_entry.get())
            
            if self.anthropic_key.get():
                config.save_api_key("ANTHROPIC_API_KEY", self.anthropic_key.get())
            
            if self.cohere_key.get():
                config.save_api_key("COHERE_API_KEY", self.cohere_key.get())
            
            # Save API selections
            settings = load_settings()
            
            # Create selected_apis dict
            selected_apis = {}
            
            # Add Gemini selections
            for key, var in self.gemini_selections.items():
                selected_apis[key] = var.get()
            
            # Add other API selections
            selected_apis.update({
                "anthropic": self.anthropic_var.get(),
                "cohere": self.cohere_var.get()
            })
            
            # Update settings and save
            settings["selected_apis"] = selected_apis
            save_settings(settings)
            
            self.status_label.configure(text="✓ All settings saved successfully", text_color="green")
            
        except Exception as e:
            error_msg = f"Error saving settings: {str(e)}"
            self.status_label.configure(text=error_msg, text_color="red")
            print(error_msg)  # Print to console for debugging

class SetupWizard(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Setup Wizard")
        self.geometry("600x600")  # Made taller for additional controls
        
        # Initialize variables
        self.api_tests_passed = {
            "anthropic": False,
            "gemini": False,
            "cohere": False
        }
        
        # Create widgets
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Plugin Categorizer Setup",
            font=("Helvetica", 24, "bold")
        )
        self.title_label.pack(pady=20)
        
        # Steps indicator
        self.steps_frame = ctk.CTkFrame(self)
        self.steps_frame.pack(fill="x", padx=20, pady=10)
        
        self.step1_label = ctk.CTkLabel(
            self.steps_frame,
            text="① Configure API Keys",
            font=("Helvetica", 12, "bold")
        )
        self.step1_label.pack(side="left", padx=10)
        
        self.step2_label = ctk.CTkLabel(
            self.steps_frame,
            text="→ ② Test API",
            font=("Helvetica", 12)
        )
        self.step2_label.pack(side="left", padx=10)
        
        # Main content area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.show_step1()
        
    def show_step1(self):
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Update steps indicator
        self.step1_label.configure(font=("Helvetica", 12, "bold"))
        self.step2_label.configure(font=("Helvetica", 12))
        
        # Add content
        ctk.CTkLabel(
            self.content_frame,
            text="First, let's configure your API keys",
            font=("Helvetica", 14)
        ).pack(pady=20)
        
        self.api_status = ctk.CTkLabel(
            self.content_frame,
            text="Checking API keys...",
            font=("Helvetica", 12)
        )
        self.api_status.pack(pady=10)
        
        self.open_manager_btn = ctk.CTkButton(
            self.content_frame,
            text="Open API Key Manager",
            command=self.open_api_manager,
            height=40
        )
        self.open_manager_btn.pack(pady=10)
        
        self.next_btn = ctk.CTkButton(
            self.content_frame,
            text="Next →",
            command=self.show_step2,
            state="disabled",
            height=40
        )
        self.next_btn.pack(pady=20)
        
        # Check API key status
        self.check_api_keys()
        
    def show_step2(self):
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Update steps indicator
        self.step1_label.configure(font=("Helvetica", 12))
        self.step2_label.configure(font=("Helvetica", 12, "bold"))
        
        # Add content
        ctk.CTkLabel(
            self.content_frame,
            text="Let's test the API connection",
            font=("Helvetica", 14)
        ).pack(pady=20)
        
        self.test_status = ctk.CTkLabel(
            self.content_frame,
            text="Click the button below to test the API",
            font=("Helvetica", 12)
        )
        self.test_status.pack(pady=10)
        
        self.test_btn = ctk.CTkButton(
            self.content_frame,
            text="Test API Connection",
            command=self.test_api,
            height=40
        )
        self.test_btn.pack(pady=10)
        
        self.finish_btn = ctk.CTkButton(
            self.content_frame,
            text="Finish",
            command=self.finish_setup,
            state="disabled",
            height=40
        )
        self.finish_btn.pack(pady=20)
        
    def check_api_keys(self):
        api_key = config.get_api_key("ANTHROPIC_API_KEY")
        if api_key:
            self.api_status.configure(
                text="✅ API key found",
                text_color="green"
            )
            self.next_btn.configure(state="normal")
        else:
            self.api_status.configure(
                text="❌ API key not found",
                text_color="red"
            )
            self.next_btn.configure(state="disabled")
    
    def open_api_manager(self):
        os.system('python api_key_manager.py')
        self.check_api_keys()
        
    def test_api(self):
        self.test_btn.configure(state="disabled")
        self.test_status.configure(text="Testing API connections...")
        
        def run_tests():
            # Test Anthropic
            success, message = APITester.test_anthropic()
            self.api_tests_passed["anthropic"] = success
            self.after(0, lambda: self.update_test_status("Anthropic", success, message))

            # Test Gemini
            success, message = APITester.test_gemini()
            self.api_tests_passed["gemini"] = success
            self.after(0, lambda: self.update_test_status("Gemini", success, message))

            # Test Cohere
            success, message = APITester.test_cohere()
            self.api_tests_passed["cohere"] = success
            self.after(0, lambda: self.update_test_status("Cohere", success, message))

            # Enable finish button if at least one API is working
            if any(self.api_tests_passed.values()):
                self.after(0, lambda: self.finish_btn.configure(state="normal"))
            
            self.after(0, lambda: self.test_btn.configure(state="normal"))
        
        threading.Thread(target=run_tests).start()

    def update_test_status(self, api_name, success, message):
        status = "✅" if success else "❌"
        color = "green" if success else "red"
        
        if not hasattr(self, f'{api_name.lower()}_status_label'):
            label = ctk.CTkLabel(
                self.content_frame,
                text=f"{api_name}: {status} {message}",
                font=("Helvetica", 12),
                text_color=color
            )
            label.pack(pady=5)
            setattr(self, f'{api_name.lower()}_status_label', label)
        else:
            getattr(self, f'{api_name.lower()}_status_label').configure(
                text=f"{api_name}: {status} {message}",
                text_color=color
            )

    def finish_setup(self):
        if any(self.api_tests_passed.values()):
            self.destroy()

class ModernGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.window = ctk.CTk()
        self.window.title("Plugin Categorizer")
        self.window.geometry("800x600")  # Made taller for additional controls
        
        # Initialize API Key Manager as None
        self.api_manager = None
        
        # Check if setup is needed
        if not self.check_api_configured():
            self.setup_wizard = SetupWizard(self)
            self.setup_wizard.wait_window()  # Wait for setup to complete
            
        # Initialize variables
        self.source_dir = None
        self.dest_dir = None
        self.categorizer = None
        self.batch_size_var = ctk.StringVar(value="15")  # Default batch size of 15
        self.model_config = None
        
        # Configure window
        self.title("Plugin Categorizer")
        self.geometry("800x600")
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Directory selection frame
        self.dir_frame = ctk.CTkFrame(self.main_frame)
        self.dir_frame.pack(fill="x", padx=5, pady=5)
        
        # Source directory selection
        self.source_label = ctk.CTkLabel(self.dir_frame, text="Source Directory:")
        self.source_label.pack(side="left", padx=5)
        
        self.source_entry = ctk.CTkEntry(self.dir_frame, width=400)
        self.source_entry.pack(side="left", padx=5)
        
        self.source_btn = ctk.CTkButton(self.dir_frame, text="Browse", command=self.select_source_directory)
        self.source_btn.pack(side="left", padx=5)

        # Destination directory selection
        self.dest_frame = ctk.CTkFrame(self.main_frame)
        self.dest_frame.pack(fill="x", padx=5, pady=5)
        
        self.dest_label = ctk.CTkLabel(self.dest_frame, text="Destination Directory:")
        self.dest_label.pack(side="left", padx=5)
        
        self.dest_entry = ctk.CTkEntry(self.dest_frame, width=400)
        self.dest_entry.pack(side="left", padx=5)
        
        self.dest_btn = ctk.CTkButton(self.dest_frame, text="Browse", command=self.select_dest_directory)
        self.dest_btn.pack(side="left", padx=5)

        # Settings frame
        self.settings_frame = ctk.CTkFrame(self.main_frame)
        self.settings_frame.pack(fill="x", padx=5, pady=5)
        
        # Batch size
        self.batch_label = ctk.CTkLabel(self.settings_frame, text="Batch Size:")
        self.batch_label.pack(side="left", padx=5)
        
        self.batch_entry = ctk.CTkEntry(self.settings_frame, width=100, textvariable=self.batch_size_var)
        self.batch_entry.pack(side="left", padx=5)
        
        # AI Model selection button
        self.model_btn = ctk.CTkButton(self.settings_frame, text="Select AI Model", command=self.select_ai_model)
        self.model_btn.pack(side="left", padx=5)
        
        # API Key Manager button
        self.api_key_button = ctk.CTkButton(
            self.settings_frame,
            text="Manage API Keys",
            command=self.open_api_manager
        )
        self.api_key_button.pack(pady=5)
        
        # Settings import/export buttons
        self.export_btn = ctk.CTkButton(self.settings_frame, text="Export Settings", command=self.export_settings)
        self.export_btn.pack(side="right", padx=5)
        
        self.import_btn = ctk.CTkButton(self.settings_frame, text="Import Settings", command=self.import_settings)
        self.import_btn.pack(side="right", padx=5)
        
        # Control buttons frame
        self.control_frame = ctk.CTkFrame(self.main_frame)
        self.control_frame.pack(fill="x", padx=5, pady=5)
        
        self.start_button = ctk.CTkButton(self.control_frame, text="Start Categorization", command=self.start_categorization)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ctk.CTkButton(self.control_frame, text="Stop", command=self.stop_categorization, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        self.test_api_btn = ctk.CTkButton(self.control_frame, text="Test API", command=self.test_api)
        self.test_api_btn.pack(side="left", padx=5)
        
        # Log frame with tabs
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="Logs:")
        self.log_label.pack(anchor="w", padx=5, pady=2)
        
        # Create tabview for different log types
        self.log_tabs = ctk.CTkTabview(self.log_frame)
        self.log_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add different log tabs
        self.log_tabs.add("General")  # General logs
        self.log_tabs.add("API")      # API-related logs
        self.log_tabs.add("Errors")   # Error logs
        self.log_tabs.add("Moves")    # Plugin move operations
        
        # Create text boxes for each tab
        self.log_text_general = ctk.CTkTextbox(self.log_tabs.tab("General"), wrap="word")
        self.log_text_general.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text_api = ctk.CTkTextbox(self.log_tabs.tab("API"), wrap="word")
        self.log_text_api.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text_errors = ctk.CTkTextbox(self.log_tabs.tab("Errors"), wrap="word")
        self.log_text_errors.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text_moves = ctk.CTkTextbox(self.log_tabs.tab("Moves"), wrap="word")
        self.log_text_moves.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Control buttons for logs
        self.log_control_frame = ctk.CTkFrame(self.log_frame)
        self.log_control_frame.pack(fill="x", padx=5, pady=5)
        
        self.clear_log_btn = ctk.CTkButton(self.log_control_frame, text="Clear Current Tab", command=self.clear_current_log)
        self.clear_log_btn.pack(side="left", padx=5)
        
        self.clear_all_logs_btn = ctk.CTkButton(self.log_control_frame, text="Clear All Logs", command=self.clear_all_logs)
        self.clear_all_logs_btn.pack(side="left", padx=5)
        
        self.export_logs_btn = ctk.CTkButton(self.log_control_frame, text="Export Logs", command=self.export_logs)
        self.export_logs_btn.pack(side="right", padx=5)
        
        # Show AI model selector on startup
        self.after(100, self.select_ai_model)

    def check_api_configured(self):
        return bool(config.get_api_key("ANTHROPIC_API_KEY"))

    def select_source_directory(self):
        dir_path = filedialog.askdirectory(title="Select Plugins Directory")
        if dir_path:
            self.source_dir = dir_path
            self.source_entry.delete(0, "end")
            self.source_entry.insert(0, dir_path)

    def select_dest_directory(self):
        dir_path = filedialog.askdirectory(title="Select Destination Directory")
        if dir_path:
            self.dest_dir = dir_path
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, dir_path)

    def select_ai_model(self):
        """Open the AI model selection window."""
        selector = AIModelSelector(self)
        selector.wait_window()
        self.model_config = selector.get_selected_config()
        self.add_log(f"Selected AI Model: {self.model_config['name']}")

    def start_categorization(self):
        """Start the categorization process."""
        if not self.source_dir:
            messagebox.showerror("Error", "Please select a source directory first!")
            return
            
        if not self.dest_dir:
            messagebox.showerror("Error", "Please select a destination directory first!")
            return
            
        try:
            # Validate batch size
            try:
                batch_size = int(self.batch_size_var.get())
                if batch_size < 1:
                    raise ValueError("Batch size must be at least 1")
                batch_size = min(batch_size, 50)  # Limit to 50 for better accuracy
                if batch_size != int(self.batch_size_var.get()):
                    self.batch_size_var.set(str(batch_size))
                    self.add_log("Note: Batch size limited to 50 for better accuracy")
            except ValueError:
                self.batch_size_var.set("15")
                batch_size = 15
                self.add_log("Invalid batch size, using default value of 15")
                
            self.categorizer = PluginCategorizer(
                self.source_dir,
                self.dest_dir,
                gui=self,
                batch_size=batch_size
            )
            
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.add_log(f"Starting plugin categorization using all available models...")
            
            def process():
                try:
                    # Get all plugin directories
                    plugin_dirs = [d for d in Path(self.source_dir).iterdir() if d.is_dir()]
                    if not plugin_dirs:
                        self.add_log("No plugin directories found in source directory!")
                        return
                        
                    self.add_log(f"Found {len(plugin_dirs)} plugin directories")
                    
                    # Process in batches
                    batch_size = self.categorizer.batch_size
                    for i in range(0, len(plugin_dirs), batch_size):
                        if not self.categorizer.is_processing:
                            self.add_log("Categorization stopped by user")
                            break
                            
                        batch = plugin_dirs[i:i + batch_size]
                        self.add_log(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} plugins)")
                        
                        try:
                            # Process will now move plugins immediately
                            self.categorizer.process([d.name for d in batch])
                            
                        except Exception as e:
                            self.add_log(f"Error processing batch: {str(e)}")
                            continue
                    
                    self.add_log("\nCategorization completed!")
                    
                except Exception as e:
                    self.add_log(f"Error during categorization: {str(e)}")
                
                finally:
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.categorizer.is_processing = False
            
            self.categorizer.is_processing = True
            threading.Thread(target=process).start()
            
        except Exception as e:
            self.add_log(f"Error: {str(e)}")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def stop_categorization(self):
        if self.categorizer:
            self.categorizer.is_processing = False
            self.stop_button.configure(state="disabled")
            self.add_log("Stopping categorization...")

    def test_api(self):
        self.test_api_btn.configure(state="disabled")
        self.add_log("Testing API connections...")
        
        def run_tests():
            # Test Anthropic
            success, message = APITester.test_anthropic()
            self.add_log(f"Anthropic API: {'✅ Success' if success else f'❌ Failed - {message}'}")

            # Test Gemini
            success, message = APITester.test_gemini()
            self.add_log(f"Gemini API: {'✅ Success' if success else f'❌ Failed - {message}'}")

            # Test Cohere
            success, message = APITester.test_cohere()
            self.add_log(f"Cohere API: {'✅ Success' if success else f'❌ Failed - {message}'}")

            self.after(0, lambda: self.test_api_btn.configure(state="normal"))
        
        threading.Thread(target=run_tests).start()

    def add_log(self, message: str, log_type: str = "general"):
        """Add a message to the specified log tab."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Map log type to text widget
        log_widgets = {
            "general": self.log_text_general,
            "api": self.log_text_api,
            "error": self.log_text_errors,
            "move": self.log_text_moves
        }
        
        # Get the appropriate text widget
        text_widget = log_widgets.get(log_type.lower(), self.log_text_general)
        
        # Add the log entry and scroll to bottom
        text_widget.insert("end", log_entry)
        text_widget.see("end")
        
        # If it's an error, also show in errors tab
        if log_type.lower() != "error" and "error" in message.lower():
            self.log_text_errors.insert("end", log_entry)
            self.log_text_errors.see("end")
    
    def clear_current_log(self):
        """Clear the currently selected log tab."""
        current_tab = self.log_tabs.get()
        if current_tab == "General":
            self.log_text_general.delete("1.0", "end")
        elif current_tab == "API":
            self.log_text_api.delete("1.0", "end")
        elif current_tab == "Errors":
            self.log_text_errors.delete("1.0", "end")
        elif current_tab == "Moves":
            self.log_text_moves.delete("1.0", "end")
        self.add_log(f"Cleared {current_tab} logs")
    
    def clear_all_logs(self):
        """Clear all log tabs."""
        self.log_text_general.delete("1.0", "end")
        self.log_text_api.delete("1.0", "end")
        self.log_text_errors.delete("1.0", "end")
        self.log_text_moves.delete("1.0", "end")
        self.add_log("All logs cleared")
    
    def export_logs(self):
        """Export all logs to a file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log")],
                initialfile=f"plugin_categorizer_logs_{timestamp}.log"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("=== GENERAL LOGS ===\n")
                    f.write(self.log_text_general.get("1.0", "end"))
                    f.write("\n=== API LOGS ===\n")
                    f.write(self.log_text_api.get("1.0", "end"))
                    f.write("\n=== ERROR LOGS ===\n")
                    f.write(self.log_text_errors.get("1.0", "end"))
                    f.write("\n=== MOVE LOGS ===\n")
                    f.write(self.log_text_moves.get("1.0", "end"))
                
                self.add_log(f"Logs exported to: {filename}")
        except Exception as e:
            self.add_log(f"Error exporting logs: {str(e)}", "error")
    
    def log_error(self, message: str):
        """Log an error message."""
        self.add_log(message, "error")
    
    def log_api(self, message: str):
        """Log an API-related message."""
        self.add_log(message, "api")
    
    def log_move(self, message: str):
        """Log a plugin move operation."""
        self.add_log(message, "move")
    
    def open_api_manager(self):
        """Open the API Key Manager window."""
        if self.api_manager is None or not self.api_manager.winfo_exists():
            self.api_manager = APIKeyManager()
            self.api_manager.focus()  # Give focus to the new window
        else:
            self.api_manager.focus()  # If window exists, just give it focus

    def export_settings(self):
        """Export current settings to a JSON file."""
        if not self.categorizer:
            messagebox.showwarning("Warning", "Please start categorization first to initialize settings.")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="categorizer_settings.json"
        )
        
        if filename:
            try:
                saved_file = self.categorizer.export_settings(filename)
                self.add_log(f"Settings exported to: {saved_file}")
            except Exception as e:
                self.add_log(f"Error exporting settings: {str(e)}")
                messagebox.showerror("Error", f"Failed to export settings: {str(e)}")

    def import_settings(self):
        """Import settings from a JSON file."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            initialfile="categorizer_settings.json"
        )
        
        if filename:
            try:
                if not self.categorizer:
                    self.categorizer = PluginCategorizer("", "", gui=self)
                
                settings = self.categorizer.import_settings(filename)
                
                # Update GUI with imported settings
                self.source_entry.delete(0, "end")
                self.source_entry.insert(0, settings["source_dir"])
                self.source_dir = settings["source_dir"]
                
                self.dest_entry.delete(0, "end")
                self.dest_entry.insert(0, settings["dest_dir"])
                self.dest_dir = settings["dest_dir"]
                
                self.batch_size_var.set(str(settings["batch_size"]))
                
                self.add_log(f"Settings imported from: {filename}")
                messagebox.showinfo("Success", "Settings imported successfully!")
            except Exception as e:
                self.add_log(f"Error importing settings: {str(e)}")
                messagebox.showerror("Error", f"Failed to import settings: {str(e)}")

if __name__ == "__main__":
    app = ModernGUI()
    app.mainloop()
