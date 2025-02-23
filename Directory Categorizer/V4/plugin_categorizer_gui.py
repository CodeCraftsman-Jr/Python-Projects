import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import logging
import shutil
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from difflib import get_close_matches
import queue
import threading
from datetime import datetime, timedelta
import random
from config import GEMINI_API_KEYS, GEMINI_API_URL, REQUESTS_PER_MINUTE, BATCH_SIZE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DetailedLogWindow:
    def __init__(self):
        self.window = None
        self.log_text = None
        self.api_stats = {}
        self.category_stats = {}

    def show(self):
        if self.window is None or not self.window.winfo_exists():
            self.window = tk.Toplevel()
            self.window.title("Detailed Logs & Statistics")
            self.window.geometry("1000x800")

            # Create notebook for tabs
            notebook = ttk.Notebook(self.window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Logs tab
            logs_frame = ttk.Frame(notebook)
            notebook.add(logs_frame, text="Logs")

            # Create log text widget
            self.log_text = scrolledtext.ScrolledText(logs_frame, height=30, wrap=tk.WORD)
            self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Configure tags for different log levels and categories
            self.log_text.tag_configure('INFO', foreground='black')
            self.log_text.tag_configure('WARNING', foreground='orange')
            self.log_text.tag_configure('ERROR', foreground='red')
            self.log_text.tag_configure('SUCCESS', foreground='green')
            self.log_text.tag_configure('API1', foreground='blue')
            self.log_text.tag_configure('API2', foreground='purple')
            self.log_text.tag_configure('API3', foreground='brown')
            self.log_text.tag_configure('API4', foreground='teal')
            self.log_text.tag_configure('API5', foreground='navy')

            # Stats tab
            stats_frame = ttk.Frame(notebook)
            notebook.add(stats_frame, text="API Statistics")

            # Create stats display
            self.stats_text = scrolledtext.ScrolledText(stats_frame, height=30, wrap=tk.WORD)
            self.stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Button frame
            button_frame = ttk.Frame(self.window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            ttk.Button(button_frame, text="Clear Logs", 
                      command=self.clear_logs).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Save Logs", 
                      command=self.save_logs).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Refresh Stats", 
                      command=self.update_stats).pack(side=tk.LEFT, padx=5)
        else:
            self.window.lift()

    def add_log(self, message, level='INFO', api_key=None):
        if self.window is not None and self.window.winfo_exists():
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            formatted_message = f"[{timestamp}] {message}"
            
            # Update API stats
            if api_key:
                api_index = GEMINI_API_KEYS.index(api_key) + 1
                tag = f'API{api_index}'
                if api_key not in self.api_stats:
                    self.api_stats[api_key] = {'success': 0, 'error': 0, 'total': 0}
                self.api_stats[api_key]['total'] += 1
                if level == 'ERROR':
                    self.api_stats[api_key]['error'] += 1
                elif level in ['INFO', 'SUCCESS']:
                    self.api_stats[api_key]['success'] += 1
                
                self.log_text.insert(tk.END, formatted_message + '\n', (level, tag))
            else:
                self.log_text.insert(tk.END, formatted_message + '\n', level)
            
            self.log_text.see(tk.END)
            self.update_stats()

    def update_stats(self):
        if self.stats_text:
            self.stats_text.delete(1.0, tk.END)
            
            # API Statistics
            self.stats_text.insert(tk.END, "=== API Usage Statistics ===\n\n")
            for api_key, stats in self.api_stats.items():
                api_index = GEMINI_API_KEYS.index(api_key) + 1
                success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                self.stats_text.insert(tk.END, f"API {api_index}:\n")
                self.stats_text.insert(tk.END, f"  Total Requests: {stats['total']}\n")
                self.stats_text.insert(tk.END, f"  Successful: {stats['success']}\n")
                self.stats_text.insert(tk.END, f"  Errors: {stats['error']}\n")
                self.stats_text.insert(tk.END, f"  Success Rate: {success_rate:.2f}%\n\n")

            # Category Statistics
            self.stats_text.insert(tk.END, "=== Category Statistics ===\n\n")
            for category, count in self.category_stats.items():
                self.stats_text.insert(tk.END, f"{category}: {count} plugins\n")

    def clear_logs(self):
        if self.log_text:
            self.log_text.delete(1.0, tk.END)
        self.api_stats = {}
        self.category_stats = {}
        self.update_stats()

    def save_logs(self):
        if self.log_text:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("All files", "*.*")]
            )
            if file_path:
                with open(file_path, 'w') as f:
                    # Save logs
                    f.write("=== Detailed Logs ===\n\n")
                    f.write(self.log_text.get(1.0, tk.END))
                    
                    # Save statistics
                    f.write("\n=== API Statistics ===\n\n")
                    for api_key, stats in self.api_stats.items():
                        api_index = GEMINI_API_KEYS.index(api_key) + 1
                        f.write(f"API {api_index}:\n")
                        f.write(f"  Total Requests: {stats['total']}\n")
                        f.write(f"  Successful: {stats['success']}\n")
                        f.write(f"  Errors: {stats['error']}\n\n")
                    
                    f.write("\n=== Category Statistics ===\n\n")
                    for category, count in self.category_stats.items():
                        f.write(f"{category}: {count} plugins\n")

class APIKeyManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.last_used = {key: 0 for key in api_keys}
        self.request_counts = {key: 0 for key in api_keys}
        self.current_key_index = 0
        self.lock = threading.Lock()

    def get_available_key(self):
        with self.lock:
            current_time = time.time()
            attempts = 0
            
            while attempts < len(self.api_keys):
                key = self.api_keys[self.current_key_index]
                
                # Reset counter if a minute has passed
                if current_time - self.last_used[key] >= 60:
                    self.request_counts[key] = 0
                    self.last_used[key] = current_time
                
                if self.request_counts[key] < REQUESTS_PER_MINUTE:
                    self.request_counts[key] += 1
                    self.last_used[key] = current_time
                    # Move to next key for next request (round-robin)
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    return key
                
                # Try next key
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                attempts += 1
            
            return None

class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put((self.format(record), record.levelname))

class PluginCategorizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WordPress Plugin Categorizer")
        self.root.geometry("1200x800")
        
        # Initialize API key manager
        self.api_manager = APIKeyManager(GEMINI_API_KEYS)
        
        # Configure style
        self._configure_style()
        
        # Variables
        self._initialize_variables()
        
        # Create main container
        self.main_container = ttk.Frame(root, style='Custom.TFrame')
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create and pack widgets
        self.create_directory_section()
        self.create_progress_section()
        self.create_simple_log_section()
        self.create_control_section()

        # Initialize detailed log window
        self.detailed_log_window = DetailedLogWindow()

        # Configure logging to GUI
        self._configure_logging()

        # Start log consumer
        self.consume_logs()

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.TFrame', background='#f0f0f0')
        style.configure('Custom.TButton', padding=5, font=('Segoe UI', 10))
        style.configure('Custom.TLabel', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Custom.Horizontal.TProgressbar',
                       troughcolor='#E0E0E0',
                       background='#4CAF50',
                       thickness=20)
        style.configure('Action.TButton',
                       padding=5,
                       font=('TkDefaultFont', 10, 'bold'))

    def _initialize_variables(self):
        self.source_dir = tk.StringVar(value=r'C:\Users\evasa\Documents\WP_PLUGINS\Utilities')
        self.target_dir = tk.StringVar(value=r'C:\Users\evasa\Documents\WP_PLUGINS')
        self.total_progress = tk.DoubleVar(value=0)
        self.current_progress = tk.DoubleVar(value=0)
        self.current_file = tk.StringVar(value="")
        self.is_processing = False
        self.log_queue = queue.Queue()
        self.MAX_CATEGORIES = 25
        self.MAX_TOTAL_CATEGORIES = 50
        # Time tracking variables
        self.start_time = None
        self.elapsed_time = tk.StringVar(value="00:00:00")
        self.estimated_time = tk.StringVar(value="--:--:--")
        self.completion_time = tk.StringVar(value="--:--:--")

    def create_simple_log_section(self):
        log_frame = ttk.LabelFrame(self.main_container, text="Recent Activity")
        log_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create simple log text widget with smaller height
        self.simple_log_text = scrolledtext.ScrolledText(log_frame, height=5, wrap=tk.WORD)
        self.simple_log_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Configure tags for different message types
        self.simple_log_text.tag_configure('INFO', foreground='black')
        self.simple_log_text.tag_configure('SUCCESS', foreground='green')
        self.simple_log_text.tag_configure('WARNING', foreground='orange')
        self.simple_log_text.tag_configure('ERROR', foreground='red')
        
        # Add "Show Detailed Logs" button
        ttk.Button(log_frame, text="Show Detailed Logs", 
                  command=self.show_detailed_logs).pack(pady=(0, 5))

    def show_detailed_logs(self):
        self.detailed_log_window.show()

    def update_log(self, message, level='INFO', api_key=None):
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        # Update simple log for move operations and important messages
        if "Moved" in message or level in ['ERROR', 'WARNING']:
            try:
                self.simple_log_text.insert(tk.END, formatted_message + '\n', level)
                # Keep only last 5 entries
                lines = self.simple_log_text.get('1.0', tk.END).splitlines()
                if len(lines) > 5:
                    self.simple_log_text.delete('1.0', tk.END)
                    for line in lines[-5:]:
                        self.simple_log_text.insert(tk.END, line + '\n')
                self.simple_log_text.see(tk.END)
            except Exception as e:
                print(f"Error updating simple log: {str(e)}")

        # Update detailed log
        if hasattr(self, 'detailed_log_window'):
            self.detailed_log_window.add_log(message, level, api_key)

    def analyze_plugin_deeply(self, plugin_name, api_key):
        """Perform a deeper analysis of the plugin name to determine its category."""
        clean_name = plugin_name.replace('-', ' ').replace('_', ' ').lower()
        words = clean_name.split()
        
        # Common keywords mapping to categories
        keyword_categories = {
            'content management': ['post', 'page', 'content', 'editor', 'edit', 'article', 'blog', 'category', 'tag', 'taxonomy'],
            'admin tools': ['admin', 'dashboard', 'manage', 'column', 'list', 'menu', 'widget', 'toolbar', 'panel'],
            'seo': ['seo', 'meta', 'sitemap', 'redirect', 'permalink', 'slug', 'search', 'keyword'],
            'security': ['security', 'protect', 'spam', 'captcha', 'firewall', 'login', 'auth', 'permission', 'role'],
            'performance': ['cache', 'speed', 'optimize', 'compress', 'minify', 'lazy', 'load', 'performance'],
            'e-commerce': ['shop', 'store', 'cart', 'checkout', 'payment', 'product', 'woo', 'commerce', 'sell'],
            'social media': ['social', 'share', 'facebook', 'twitter', 'instagram', 'linkedin', 'pinterest'],
            'forms': ['form', 'contact', 'survey', 'poll', 'quiz', 'input', 'field', 'submit'],
            'media': ['media', 'image', 'video', 'audio', 'gallery', 'slider', 'file', 'upload', 'svg', 'photo'],
            'backup': ['backup', 'restore', 'export', 'import', 'migrate', 'clone', 'copy'],
            'analytics': ['analytics', 'track', 'stat', 'monitor', 'report', 'log', 'pixel'],
            'development tools': ['debug', 'dev', 'tool', 'code', 'script', 'css', 'style', 'header', 'footer', 'api']
        }

        # First try: Check for direct keyword matches
        keyword_scores = {category: 0 for category in keyword_categories}
        for word in words:
            for category, keywords in keyword_categories.items():
                if word in keywords:
                    keyword_scores[category] += 1
                # Check for partial matches too
                for keyword in keywords:
                    if keyword in word or word in keyword:
                        keyword_scores[category] += 0.5

        # If we found any matches, use the highest scoring category
        max_score = max(keyword_scores.values())
        if max_score > 0:
            return max(keyword_scores.items(), key=lambda x: x[1])[0]

        # Second try: Use Gemini API for deeper analysis
        prompt = f"""Analyze this WordPress plugin name in detail: '{clean_name}'
        
        Consider these aspects:
        1. Break down each word and analyze its potential meaning
        2. Think about what problem this plugin might solve
        3. Consider common WordPress plugin patterns
        4. Think about where in WordPress this plugin would be used
        
        Based on your analysis, categorize it into ONE of these categories:
        - Content Management (for posts, pages, content editing, taxonomies)
        - Admin Tools (for admin interface improvements, dashboard widgets, etc.)
        - SEO (for search optimization, meta tags, sitemaps)
        - Security (for security and protection features)
        - Performance (for optimization, caching, speed improvements)
        - E-commerce (for online stores, products, payments)
        - Social Media (for social network integration, sharing)
        - Forms (for contact forms and other form builders)
        - Media (for images, videos, files, galleries)
        - Backup (for backup, restore, migration)
        - Analytics (for tracking, statistics, monitoring)
        - Development Tools (for coding, debugging, customization)
        
        DO NOT return 'Other'. Find the most appropriate category from the list above.
        Explain your reasoning, then return ONLY the category name in the last line."""

        try:
            response = requests.post(
                GEMINI_API_URL,
                headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "topK": 1,
                        "topP": 0.1,
                        "maxOutputTokens": 200
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    analysis = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    # Get the last line as the category
                    category = analysis.split('\n')[-1].strip()
                    return category.lower()

        except Exception:
            pass

        # If all else fails, make an educated guess based on the context
        if any(word in clean_name for word in ['add', 'edit', 'show', 'display', 'manage']):
            return 'admin tools'
        if any(word in clean_name for word in ['custom', 'style', 'css', 'js', 'script']):
            return 'development tools'
        if any(word in clean_name for word in ['image', 'media', 'file']):
            return 'media'
        
        # Final fallback to Content Management as it's the most common category
        return 'content management'

    def get_plugin_category_from_gemini(self, plugin_name):
        api_key = self.api_manager.get_available_key()
        if not api_key:
            self.update_log(f"All API keys are rate limited. Waiting for reset...", "WARNING")
            time.sleep(2)  # Wait before retrying
            return None

        # Clean up plugin name for better analysis
        clean_name = plugin_name.replace('-', ' ').replace('_', ' ')
        
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': api_key
        }

        prompt = f"""Analyze this WordPress plugin name and categorize it into exactly one of these categories:
        - Content Management (for plugins that help manage posts, pages, media, etc.)
        - Admin Tools (for admin interface improvements, dashboard widgets, etc.)
        - SEO (for search engine optimization tools)
        - Security (for security and protection features)
        - Performance (for caching, optimization, etc.)
        - E-commerce (for online store and payment features)
        - Social Media (for social network integration)
        - Forms (for contact forms and other form builders)
        - Media (for image, video, and file management)
        - Backup (for backup and restoration tools)
        - Analytics (for statistics and tracking)
        - Development Tools (for debugging, coding, etc.)

        Plugin name to analyze: {clean_name}

        Consider the following:
        1. Look for keywords that indicate the plugin's purpose
        2. Consider common WordPress plugin naming patterns
        3. Think about what functionality the name suggests

        Return ONLY the category name, nothing else."""

        try:
            response = requests.post(
                GEMINI_API_URL,
                headers=headers,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 1,
                        "topP": 0.1,
                        "maxOutputTokens": 10
                    }
                }
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        category = result['candidates'][0]['content']['parts'][0]['text'].strip().lower()
                        
                        # Validate and normalize category
                        valid_categories = {
                            'content management', 'admin tools', 'seo', 'security', 
                            'performance', 'e-commerce', 'social media', 'forms', 
                            'media', 'backup', 'analytics', 'development tools'
                        }
                        
                        # If category is not valid or is "other", do deeper analysis
                        if category not in valid_categories or category == 'other':
                            self.update_log(f"Initial category unclear for '{plugin_name}', performing deeper analysis...", "INFO", api_key)
                            category = self.analyze_plugin_deeply(plugin_name, api_key)
                        
                        # Capitalize for display
                        category = ' '.join(word.capitalize() for word in category.split())
                        
                        self.update_log(f"API {GEMINI_API_KEYS.index(api_key) + 1}: Successfully categorized '{plugin_name}' as '{category}'", "SUCCESS", api_key)
                        
                        # Update category statistics
                        if hasattr(self, 'detailed_log_window'):
                            if category not in self.detailed_log_window.category_stats:
                                self.detailed_log_window.category_stats[category] = 0
                            self.detailed_log_window.category_stats[category] += 1
                        
                        return category
                    else:
                        self.update_log(f"Invalid response format for '{plugin_name}', performing deeper analysis...", "INFO", api_key)
                        category = self.analyze_plugin_deeply(plugin_name, api_key)
                        return ' '.join(word.capitalize() for word in category.split())
                except Exception as e:
                    self.update_log(f"Error parsing response for '{plugin_name}', performing deeper analysis...", "INFO", api_key)
                    category = self.analyze_plugin_deeply(plugin_name, api_key)
                    return ' '.join(word.capitalize() for word in category.split())
            else:
                self.update_log(f"API error for '{plugin_name}', performing deeper analysis...", "INFO", api_key)
                category = self.analyze_plugin_deeply(plugin_name, api_key)
                return ' '.join(word.capitalize() for word in category.split())

        except Exception as e:
            self.update_log(f"Exception for '{plugin_name}', performing deeper analysis...", "INFO", api_key)
            category = self.analyze_plugin_deeply(plugin_name, api_key)
            return ' '.join(word.capitalize() for word in category.split())

    def move_plugin(self, folder):
        if not self.is_processing:
            return

        try:
            # Get the full source path and plugin name
            source_path = folder  # folder is already the full path
            plugin_name = os.path.basename(folder)
            
            # Get category for the plugin
            category = self.get_plugin_category_from_gemini(plugin_name)
            
            if category:
                # Create category directory if it doesn't exist
                category_dir = os.path.join(self.target_dir.get(), category)
                os.makedirs(category_dir, exist_ok=True)
                
                # Construct target path
                target_path = os.path.join(category_dir, plugin_name)
                
                try:
                    # Handle case where target already exists
                    if os.path.exists(target_path):
                        base_name = plugin_name
                        counter = 1
                        while os.path.exists(target_path):
                            name_parts = base_name.rsplit('.', 1) if '.' in base_name else [base_name, '']
                            new_name = f"{name_parts[0]}_v{counter}"
                            if name_parts[1]:
                                new_name = f"{new_name}.{name_parts[1]}"
                            target_path = os.path.join(category_dir, new_name)
                            counter += 1
                    
                    # Move the plugin folder
                    shutil.move(source_path, target_path)
                    move_status = f"Moved '{plugin_name}' to {category}"
                    self.update_log(move_status, "SUCCESS")
                    
                except Exception as e:
                    error_msg = f"Error moving '{plugin_name}': {str(e)}"
                    self.update_log(error_msg, "ERROR")
                    
            else:
                self.update_log(f"Could not categorize '{plugin_name}'", "WARNING")
                
        except Exception as e:
            self.update_log(f"Error processing folder: {str(e)}", "ERROR")

    def process_plugins(self):
        try:
            if not self.source_dir.get() or not self.target_dir.get():
                messagebox.showerror("Error", "Please select both source and target directories")
                return
            
            if not os.path.exists(self.source_dir.get()):
                messagebox.showerror("Error", "Source directory does not exist")
                return
            
            # Create target directory if it doesn't exist
            os.makedirs(self.target_dir.get(), exist_ok=True)
            
            # Get list of folders in source directory
            folders = [f for f in os.listdir(self.source_dir.get()) 
                      if os.path.isdir(os.path.join(self.source_dir.get(), f))]
            
            if not folders:
                messagebox.showinfo("Info", "No folders found in source directory")
                return
            
            self.is_processing = True
            self.start_time = time.time()  # Start timing
            self.update_time_estimates()  # Start time updates
            
            total_folders = len(folders)
            self.total_progress.set(0)
            
            # Process folders in batches
            futures = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                for i in range(0, total_folders, BATCH_SIZE):
                    if not self.is_processing:
                        break
                        
                    batch = folders[i:i + BATCH_SIZE]
                    logger.info(f"Processing batch {i//BATCH_SIZE + 1} of {(total_folders + BATCH_SIZE - 1)//BATCH_SIZE}")
                    logger.info(f"Current number of categories: {len(self.detailed_log_window.category_stats)}/{self.MAX_TOTAL_CATEGORIES}")
                    
                    # Reset current batch progress
                    self.current_progress.set(0)
                    
                    # Create full paths for the folders
                    batch_futures = {
                        executor.submit(
                            self.move_plugin, 
                            os.path.join(self.source_dir.get(), folder)
                        ): folder for folder in batch
                    }
                    futures.extend(batch_futures.items())
                    
                    completed = 0
                    for future, folder in batch_futures.items():
                        if not self.is_processing:
                            break
                        try:
                            future.result()  # Wait for the result
                            completed += 1
                            self.current_progress.set((completed / len(batch)) * 100)
                            self.total_progress.set(((i + completed) / total_folders) * 100)
                        except Exception as e:
                            logger.error(f"Error processing {folder}: {str(e)}")
                    
                    if not self.is_processing:
                        break

            self.is_processing = False
            self.start_time = None
            self.elapsed_time.set("00:00:00")
            self.estimated_time.set("--:--:--")
            self.completion_time.set("--:--:--")
            messagebox.showinfo("Complete", "Plugin categorization completed!")
            
        except Exception as e:
            self.is_processing = False
            self.start_time = None
            logger.error(f"Error in process_plugins: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

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
        self.update_time_estimates()  # Start time updates
        
        # Update button states
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Reset progress and time displays
        self.total_progress.set(0)
        self.current_progress.set(0)
        self.current_file.set("")
        self.elapsed_time.set("00:00:00")
        self.estimated_time.set("--:--:--")
        self.completion_time.set("--:--:--")
        
        # Start processing in a separate thread
        threading.Thread(target=self.process_plugins, daemon=True).start()

    def stop_processing(self):
        self.is_processing = False
        self.start_time = None
        
        # Reset displays
        self.elapsed_time.set("00:00:00")
        self.estimated_time.set("--:--:--")
        self.completion_time.set("--:--:--")
        self.current_file.set("")
        
        # Update button states
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def _configure_logging(self):
        queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)

    def consume_logs(self):
        while True:
            try:
                record, level = self.log_queue.get_nowait()
                self.update_log(record, level)
            except queue.Empty:
                break
        self.root.after(100, self.consume_logs)

    def create_directory_section(self):
        dir_frame = ttk.LabelFrame(self.main_container, text="Directory Settings", padding=10)
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        # Source Directory
        ttk.Label(dir_frame, text="Source Directory:").pack(anchor=tk.W)
        source_frame = ttk.Frame(dir_frame)
        source_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(source_frame, textvariable=self.source_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(source_frame, text="Browse", command=lambda: self.browse_directory('source')).pack(side=tk.LEFT, padx=(5, 0))

        # Destination Directory
        ttk.Label(dir_frame, text="Destination Directory:").pack(anchor=tk.W)
        dest_frame = ttk.Frame(dir_frame)
        dest_frame.pack(fill=tk.X)
        ttk.Entry(dest_frame, textvariable=self.target_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dest_frame, text="Browse", command=lambda: self.browse_directory('dest')).pack(side=tk.LEFT, padx=(5, 0))

    def create_progress_section(self):
        progress_frame = ttk.LabelFrame(self.main_container, text="Progress", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        # Current file frame
        current_frame = ttk.Frame(progress_frame)
        current_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(current_frame, text="Current File:").pack(side=tk.LEFT)
        ttk.Label(current_frame, textvariable=self.current_file).pack(side=tk.LEFT, padx=(5, 0))

        # Current batch progress
        batch_frame = ttk.Frame(progress_frame)
        batch_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(batch_frame, text="Current Batch:").pack(side=tk.LEFT)
        ttk.Progressbar(batch_frame, variable=self.current_progress, maximum=100).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Label(batch_frame, textvariable=self.current_progress, width=5).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(batch_frame, text="%").pack(side=tk.LEFT)

        # Total progress
        total_frame = ttk.Frame(progress_frame)
        total_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(total_frame, text="Total Progress:").pack(side=tk.LEFT)
        ttk.Progressbar(total_frame, variable=self.total_progress, maximum=100).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Label(total_frame, textvariable=self.total_progress, width=5).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(total_frame, text="%").pack(side=tk.LEFT)

        # Time information frame
        time_frame = ttk.Frame(progress_frame)
        time_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Running time
        running_frame = ttk.Frame(time_frame)
        running_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(running_frame, text="Running Time:").pack(side=tk.LEFT)
        ttk.Label(running_frame, textvariable=self.elapsed_time).pack(side=tk.LEFT, padx=(5, 0))
        
        # Estimated time remaining
        estimate_frame = ttk.Frame(time_frame)
        estimate_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(estimate_frame, text="Time Remaining:").pack(side=tk.LEFT)
        ttk.Label(estimate_frame, textvariable=self.estimated_time).pack(side=tk.LEFT, padx=(5, 0))
        
        # Estimated completion time
        completion_frame = ttk.Frame(time_frame)
        completion_frame.pack(fill=tk.X)
        ttk.Label(completion_frame, text="Completion Time:").pack(side=tk.LEFT)
        ttk.Label(completion_frame, textvariable=self.completion_time).pack(side=tk.LEFT, padx=(5, 0))

    def update_time_estimates(self):
        if not self.is_processing:
            return
        
        if self.start_time is None:
            return
            
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        self.elapsed_time.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Calculate estimated time remaining
        progress = self.total_progress.get()
        if progress > 0:
            total_estimated = elapsed / (progress / 100)
            remaining = total_estimated - elapsed
            
            # Only update if we have a reasonable estimate
            if remaining > 0:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                seconds = int(remaining % 60)
                self.estimated_time.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Calculate completion time
                completion_time = datetime.now() + timedelta(seconds=remaining)
                self.completion_time.set(completion_time.strftime("%H:%M:%S"))
        
        # Schedule next update
        if self.is_processing:
            self.root.after(1000, self.update_time_estimates)

    def create_control_section(self):
        control_frame = ttk.LabelFrame(self.main_container, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Create button frame
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)

        # Start button
        self.start_button = ttk.Button(
            button_frame, 
            text="Start Processing", 
            command=self.start_processing,
            style='Action.TButton'
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Stop button
        self.stop_button = ttk.Button(
            button_frame, 
            text="Stop Processing", 
            command=self.stop_processing,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def browse_directory(self, dir_type):
        directory = filedialog.askdirectory()
        if directory:
            if dir_type == 'source':
                self.source_dir.set(directory)
            else:
                self.target_dir.set(directory)

if __name__ == "__main__":
    root = tk.Tk()
    app = PluginCategorizerGUI(root)
    root.mainloop()
