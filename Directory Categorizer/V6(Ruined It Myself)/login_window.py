import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

class LoginWindow:
    """Login window for the plugin categorizer."""
    
    def __init__(self, root, on_success_callback):
        self.root = root
        self.root.title("Login")
        self.root.geometry("300x200")
        
        # Center the window
        self.center_window()
        
        # Store callback
        self.on_success = on_success_callback
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Username field
        ttk.Label(main_frame, text="Username:").pack(fill=tk.X, pady=(0, 5))
        self.username = ttk.Entry(main_frame)
        self.username.pack(fill=tk.X, pady=(0, 10))
        
        # Password field
        ttk.Label(main_frame, text="Password:").pack(fill=tk.X, pady=(0, 5))
        self.password = ttk.Entry(main_frame, show="*")
        self.password.pack(fill=tk.X, pady=(0, 20))
        
        # Login button
        ttk.Button(main_frame, text="Login", command=self.login).pack(pady=10)
        
        # Load credentials
        self.load_credentials()
        
        # Bind Enter key to login
        self.root.bind('<Return>', lambda e: self.login())

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def load_credentials(self):
        """Load saved credentials if they exist."""
        try:
            if os.path.exists('credentials.json'):
                with open('credentials.json', 'r') as f:
                    creds = json.load(f)
                    self.username.insert(0, creds.get('username', ''))
                    # Don't load password for security reasons
        except Exception as e:
            print(f"Error loading credentials: {e}")

    def save_credentials(self, username):
        """Save credentials for next login."""
        try:
            with open('credentials.json', 'w') as f:
                json.dump({'username': username}, f)
        except Exception as e:
            print(f"Error saving credentials: {e}")

    def login(self):
        """Handle login attempt."""
        username = self.username.get()
        password = self.password.get()
        
        # Add your authentication logic here
        # For now, we'll use a simple check
        if username and password:  # Replace with proper authentication
            self.save_credentials(username)
            self.root.destroy()
            self.on_success()
        else:
            messagebox.showerror("Error", "Please enter both username and password")
