import tkinter as tk
from tkinter import ttk, messagebox
import hashlib

class LoginWindow:
    def __init__(self, window, on_success):
        self.window = window
        self.on_success = on_success
        
        self.window.title("Login")
        self.window.geometry("300x150")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)  # Handle window close button
        
        # Center the window
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 300) // 2
        y = (screen_height - 150) // 2
        self.window.geometry(f"300x150+{x}+{y}")
        
        # Username
        tk.Label(self.window, text="Username:").pack(pady=5)
        self.username = tk.Entry(self.window)
        self.username.pack()
        
        # Password
        tk.Label(self.window, text="Password:").pack(pady=5)
        self.password = tk.Entry(self.window, show="*")
        self.password.pack()
        
        # Login button
        tk.Button(self.window, text="Login", command=self.login).pack(pady=10)
        
        # Bind Enter key to login
        self.window.bind('<Return>', lambda e: self.login())
        
        # Focus on username field
        self.username.focus()
    
    def login(self):
        if self.username.get() == "swag" and self.password.get() == "swag":
            self.window.destroy()  # Destroy login window
            self.on_success()  # Launch main application
        else:
            messagebox.showerror("Error", "Invalid username or password")
            self.password.delete(0, tk.END)  # Clear password field
    
    def on_close(self):
        """Handle window close button click"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.window.quit()
            self.window.destroy()
