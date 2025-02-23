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
import concurrent.futures

class DependencyChecker:
    """Check and install required dependencies."""
    
    REQUIRED_PACKAGES = [
        'google-generativeai',
        'requests',
        'google-search-results',
        'openai',
        'cohere',
        'anthropic'
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Checking Dependencies")
        self.root.geometry("400x300")
        
        # Message queue for thread-safe UI updates
        self.msg_queue = queue.Queue()
        
        # Center the window
        self.center_window()
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Initializing...", wraplength=350)
        self.status_label.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate', length=300)
        self.progress.pack(pady=20)
        
        # Details text
        self.details_text = tk.Text(main_frame, height=8, width=40)
        self.details_text.pack(pady=20)
        
        # Start message processing
        self.root.after(100, self.process_messages)
        
        # Start dependency check in a separate thread
        threading.Thread(target=self.check_dependencies, daemon=True).start()

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def update_ui(self, **kwargs):
        """Thread-safe UI updates."""
        self.msg_queue.put(kwargs)

    def process_messages(self):
        """Process messages from the queue and update UI."""
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                if 'status' in msg:
                    self.status_label.config(text=msg['status'])
                if 'progress' in msg:
                    self.progress['value'] = msg['progress']
                if 'details' in msg:
                    self.details_text.insert(tk.END, msg['details'] + '\n')
                    self.details_text.see(tk.END)
                if 'complete' in msg:
                    self.root.after(1000, self.root.destroy)
                    return
                if 'error' in msg:
                    messagebox.showerror("Error", msg['error'])
                    self.root.destroy()
                    return
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.root.after(100, self.process_messages)

    def check_package(self, package):
        """Check if a package is installed."""
        try:
            pkg_resources.get_distribution(package)
            return True
        except pkg_resources.DistributionNotFound:
            return False

    def install_package(self, package):
        """Install a single package."""
        try:
            # Use a timeout to prevent hanging
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=subprocess.STARTUPINFO() if os.name == 'nt' else None
            )
            
            try:
                stdout, stderr = process.communicate(timeout=60)  # 60 second timeout
                if process.returncode == 0:
                    return True, f"Successfully installed {package}"
                else:
                    return False, f"Failed to install {package}: {stderr.decode()}"
            except subprocess.TimeoutExpired:
                process.kill()
                return False, f"Installation of {package} timed out"
                
        except Exception as e:
            return False, f"Error installing {package}: {str(e)}"

    def check_dependencies(self):
        """Check and install required dependencies."""
        try:
            # First check all packages
            missing_packages = []
            total_packages = len(self.REQUIRED_PACKAGES)
            progress_step = 50 / total_packages  # Use first 50% for checking
            
            for i, package in enumerate(self.REQUIRED_PACKAGES):
                self.update_ui(
                    status=f"Checking {package}...",
                    progress=i * progress_step,
                    details=f"Checking {package}..."
                )
                
                if not self.check_package(package):
                    missing_packages.append(package)
                    self.update_ui(details=f"{package} not found.")
                else:
                    version = pkg_resources.get_distribution(package).version
                    self.update_ui(details=f"{package} is installed (version {version}).")
            
            # If no missing packages, we're done
            if not missing_packages:
                self.update_ui(
                    status="All dependencies are installed!",
                    progress=100,
                    details="Setup complete!",
                    complete=True
                )
                return
            
            # Install missing packages
            self.update_ui(status="Installing missing packages...")
            progress_step = 50 / len(missing_packages)  # Use remaining 50% for installation
            current_progress = 50
            
            # Install packages with a thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_package = {
                    executor.submit(self.install_package, package): package 
                    for package in missing_packages
                }
                
                for future in concurrent.futures.as_completed(future_to_package):
                    package = future_to_package[future]
                    success, message = future.result()
                    
                    if not success:
                        self.update_ui(error=message)
                        return
                    
                    self.update_ui(
                        details=message,
                        progress=current_progress + progress_step
                    )
                    current_progress += progress_step
            
            self.update_ui(
                status="All dependencies installed successfully!",
                progress=100,
                details="Setup complete!",
                complete=True
            )
            
        except Exception as e:
            self.update_ui(error=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DependencyChecker(root)
    root.mainloop()
