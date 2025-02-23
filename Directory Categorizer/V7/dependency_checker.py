import subprocess
import sys
import pkg_resources
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import logging
from datetime import datetime
import queue

class DependencyChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Dependency Checker")
        self.root.geometry("600x500")
        
        # Message queue for thread-safe UI updates
        self.message_queue = queue.Queue()
        
        # Setup logging
        self.setup_logging()
        
        # Get the directory where the script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.requirements_path = os.path.join(self.script_dir, 'requirements.txt')
        
        # Center the window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 500) // 2
        self.root.geometry(f"600x500+{x}+{y}")
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = ttk.Label(self.main_frame, text="Initializing dependency checker...", 
                                    font=('Helvetica', 10, 'bold'))
        self.status_label.pack(fill=tk.X, pady=(0, 10))
        
        # Current operation label
        self.operation_label = ttk.Label(self.main_frame, text="")
        self.operation_label.pack(fill=tk.X, pady=(0, 5))
        
        # Progress frame
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Progress", padding=10)
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Overall progress
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(self.progress_frame, mode='determinate', 
                                      variable=self.progress_var)
        self.progress.pack(fill=tk.X, pady=(0, 5))
        
        # Progress percentage
        self.progress_label = ttk.Label(self.progress_frame, text="0%")
        self.progress_label.pack(side=tk.RIGHT)
        
        # Create log frame
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Logs", padding=10)
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Log text with scrollbar
        self.log_text = tk.Text(self.log_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", 
                                command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons frame
        self.buttons_frame = ttk.Frame(self.main_frame)
        self.buttons_frame.pack(fill=tk.X)
        
        # Install button (hidden initially)
        self.install_button = ttk.Button(self.buttons_frame, text="Install Missing Dependencies", 
                                       command=self.install_dependencies)
        
        # Continue button (hidden initially)
        self.continue_button = ttk.Button(self.buttons_frame, text="Continue", 
                                        command=self.root.destroy)
        
        # Save logs button
        self.save_logs_button = ttk.Button(self.buttons_frame, text="Save Logs", 
                                         command=self.save_logs)
        self.save_logs_button.pack(side=tk.RIGHT)
        
        # Start checking dependencies
        self.root.after(100, self.check_dependencies)
        
        # Start processing messages from queue
        self.process_messages()
    
    def process_messages(self):
        """Process messages from the queue and update UI."""
        try:
            while True:
                message = self.message_queue.get_nowait()
                message_type = message.get('type', '')
                
                if message_type == 'log':
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.log_text.insert(tk.END, f"{timestamp} - {message['text']}\n")
                    self.log_text.see(tk.END)
                elif message_type == 'progress':
                    self.progress_var.set(message['value'])
                    self.progress_label.config(text=f"{int(message['value'])}%")
                elif message_type == 'operation':
                    self.operation_label.config(text=message['text'])
                elif message_type == 'status':
                    self.status_label.config(text=message['text'])
                elif message_type == 'error':
                    messagebox.showerror("Error", message['text'])
                elif message_type == 'installation_complete':
                    if message.get('success', False):
                        self._installation_success()
                    else:
                        self._installation_failed(message.get('error', 'Unknown error'))
                
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.root.after(100, self.process_messages)
    
    def queue_message(self, **kwargs):
        """Add a message to the queue."""
        self.message_queue.put(kwargs)
    
    def log_message(self, message, level=logging.INFO):
        """Log a message to both file and UI."""
        logging.log(level, message)
        self.queue_message(type='log', text=message)
    
    def update_progress(self, value, operation=""):
        """Update progress bar and labels."""
        self.queue_message(type='progress', value=value)
        if operation:
            self.queue_message(type='operation', text=operation)
    
    def check_dependencies(self):
        """Check if all required dependencies are installed."""
        self.queue_message(type='log', text="Starting dependency check...")
        self.queue_message(type='progress', value=0)
        self.queue_message(type='operation', text="Checking dependencies...")
        
        try:
            # Read requirements from file
            with open(self.requirements_path, 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            self.queue_message(type='log', text=f"Found {len(requirements)} requirements to check")
            self.queue_message(type='progress', value=10)
            
            missing_packages = []
            for i, requirement in enumerate(requirements):
                progress = 10 + ((i + 1) * 80 // len(requirements))
                self.queue_message(type='progress', value=progress)
                self.queue_message(type='operation', text=f"Checking {requirement}...")
                
                package_name = requirement.split('>=')[0].split('==')[0].strip()
                try:
                    pkg_resources.require(requirement)
                    self.queue_message(type='log', text=f"✓ {requirement} is installed")
                except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
                    self.queue_message(type='log', text=f"✗ {requirement} is missing or version mismatch")
                    missing_packages.append(requirement)
            
            if missing_packages:
                self.queue_message(type='progress', value=100)
                self.queue_message(type='operation', text="Dependencies check complete - some missing")
                self.queue_message(type='log', text=f"Missing dependencies: {', '.join(missing_packages)}")
                self.queue_message(type='status', text="Some dependencies need to be installed")
                self.install_button.config(state='normal')
                self.continue_button.config(state='disabled')
            else:
                self.queue_message(type='progress', value=100)
                self.queue_message(type='operation', text="Dependencies check complete - all installed")
                self.queue_message(type='log', text="All dependencies are properly installed")
                self.queue_message(type='status', text="All dependencies are installed!")
                self.install_button.pack_forget()
                self.continue_button.config(state='normal')
                self.continue_button.pack(side=tk.LEFT)
                # Close the window after a short delay if all dependencies are installed
                self.root.after(1000, self.root.destroy)
        
        except Exception as e:
            self.queue_message(type='log', text=f"Error checking dependencies: {str(e)}")
            self.queue_message(type='error', text=f"Failed to check dependencies: {str(e)}")
            self.install_button.config(state='normal')
            self.continue_button.config(state='disabled')
    
    def install_dependencies(self):
        """Install missing dependencies using pip."""
        self.install_button.config(state='disabled')
        self.continue_button.config(state='disabled')
        self.queue_message(type='progress', value=0)
        self.queue_message(type='operation', text="Preparing to install dependencies...")
        self.queue_message(type='log', text="Starting dependency installation...")
        
        def run_install():
            try:
                # First upgrade pip itself
                self.queue_message(type='log', text="Upgrading pip...")
                self.queue_message(type='progress', value=10)
                self.queue_message(type='operation', text="Upgrading pip...")
                
                upgrade_process = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                    capture_output=True,
                    text=True
                )
                
                if upgrade_process.returncode != 0:
                    self.queue_message(type='log', text="Warning: Failed to upgrade pip")
                else:
                    self.queue_message(type='log', text="Pip upgraded successfully")
                
                # Now install requirements
                self.queue_message(type='log', text="Installing required packages...")
                self.queue_message(type='progress', value=20)
                self.queue_message(type='operation', text="Installing packages...")
                
                process = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", "-r", self.requirements_path, "--verbose"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # Track installation progress
                total_packages = 0
                installed_packages = 0
                
                with open(self.requirements_path, 'r') as f:
                    total_packages = len([line for line in f if line.strip() and not line.startswith('#')])
                
                # Read output in real-time
                for line in iter(process.stdout.readline, ''):
                    self.queue_message(type='log', text=line.strip())
                    
                    # Update progress based on pip output
                    if "Collecting" in line:
                        self.queue_message(type='progress', value=30)
                        self.queue_message(type='operation', text=f"Collecting {line.split()[1]}...")
                    elif "Downloading" in line:
                        self.queue_message(type='progress', value=50)
                        self.queue_message(type='operation', text="Downloading packages...")
                    elif "Installing" in line:
                        installed_packages += 1
                        progress = 50 + (installed_packages * 40 // total_packages)
                        self.queue_message(type='progress', value=progress)
                        self.queue_message(type='operation', 
                                        text=f"Installing package {installed_packages} of {total_packages}...")
                
                # Check for errors
                process.wait()
                if process.returncode != 0:
                    error = process.stderr.read()
                    raise Exception(f"Pip install failed: {error}")
                
                # Signal success through queue
                self.queue_message(type='installation_complete', success=True)
                
            except Exception as e:
                error_msg = str(e)
                self.queue_message(type='log', text=f"Installation error: {error_msg}")
                self.queue_message(type='error', text=f"Failed to install dependencies. Check the logs for details.\n\nError: {error_msg}")
                # Signal failure through queue
                self.queue_message(type='installation_complete', success=False, error=error_msg)
        
        # Run installation in a separate thread
        threading.Thread(target=run_install, daemon=True).start()
    
    def _installation_success(self):
        """Called when installation succeeds."""
        self.queue_message(type='progress', value=100)
        self.queue_message(type='operation', text="Installation completed successfully")
        self.queue_message(type='log', text="All dependencies installed successfully")
        self.queue_message(type='status', text="Dependencies installed successfully!")
        self.install_button.pack_forget()
        self.continue_button.config(state='normal')
        self.continue_button.pack(side=tk.LEFT)
        
    def _installation_failed(self, error):
        """Called when installation fails."""
        self.queue_message(type='progress', value=100)
        self.queue_message(type='operation', text="Installation failed")
        self.queue_message(type='log', text=f"Installation failed: {error}")
        self.queue_message(type='status', text="Failed to install dependencies!")
        self.install_button.config(state='normal')
        self.continue_button.config(state='normal')
        messagebox.showerror("Installation Error", 
                           f"Failed to install dependencies. Check the logs for details.\n\nError: {error}")
    
    def save_logs(self):
        """Save the current logs to a file."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = os.path.join(self.script_dir, f'dependency_check_{timestamp}.log')
            
            with open(save_path, 'w') as f:
                f.write(self.log_text.get(1.0, tk.END))
            
            self.log_message(f"Logs saved to: {save_path}")
            messagebox.showinfo("Success", f"Logs saved to:\n{save_path}")
        except Exception as e:
            self.log_message(f"Error saving logs: {str(e)}", logging.ERROR)
            messagebox.showerror("Error", f"Failed to save logs: {str(e)}")

    def setup_logging(self):
        """Setup logging configuration."""
        self.log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                    'dependency_checker.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = DependencyChecker(root)
    root.mainloop()
