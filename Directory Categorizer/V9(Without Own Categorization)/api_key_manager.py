import customtkinter as ctk
import config
from tkinter import messagebox

class APIKeyManager(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("AI APIs Key Manager")
        self.geometry("800x600")
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="🤖 AI APIs Key Manager", 
            font=("Helvetica", 24, "bold")
        )
        self.title_label.pack(pady=20)

        # Create scrollable frame for API sections
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Gemini API Section
        self.create_api_section(
            "Gemini API",
            "Google's most capable AI model for text, code, and analysis.\n" +
            "Get your API key from: https://makersuite.google.com/app/apikey",
            "GEMINI_API_KEY"
        )

        # Cohere API Section
        self.create_api_section(
            "Cohere API",
            "Cohere's powerful language AI for text generation, classification, and embeddings.\n" +
            "Get your API key from: https://dashboard.cohere.ai/api-keys",
            "COHERE_API_KEY"
        )

        # Claude API Section
        self.create_api_section(
            "Claude API (Anthropic)",
            "Anthropic's advanced AI model for complex tasks and reasoning.\n" +
            "Get your API key from: https://console.anthropic.com/account/keys",
            "CLAUDE_API_KEY"
        )

        # Anthropic API Section
        self.create_api_section(
            "Anthropic API",
            "Additional Anthropic services and capabilities.\n" +
            "Get your API key from: https://console.anthropic.com/account/keys",
            "ANTHROPIC_API_KEY"
        )

        # View Button
        self.view_button = ctk.CTkButton(
            self.main_frame,
            text="View All API Keys",
            command=self.view_api_keys,
            font=("Helvetica", 12, "bold"),
            height=40
        )
        self.view_button.pack(pady=20)

    def create_api_section(self, title, description, key_name):
        # Create frame for this API section
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.pack(fill="x", pady=10, padx=5)

        # Title
        ctk.CTkLabel(
            section_frame,
            text=title,
            font=("Helvetica", 16, "bold")
        ).pack(pady=(10, 5), padx=10, anchor="w")

        # Description
        ctk.CTkLabel(
            section_frame,
            text=description,
            font=("Helvetica", 12),
            wraplength=700,
            justify="left"
        ).pack(pady=5, padx=10, anchor="w")

        # API Key Entry
        key_entry = ctk.CTkEntry(
            section_frame,
            placeholder_text=f"Enter {title} key",
            width=500,
            show="*"
        )
        key_entry.pack(pady=5, padx=10)

        # Load existing key if any
        existing_key = config.get_api_key(key_name)
        if existing_key:
            key_entry.insert(0, existing_key)

        # Save Button
        save_button = ctk.CTkButton(
            section_frame,
            text="Save Key",
            command=lambda: self.save_api_key(key_name, key_entry.get()),
            font=("Helvetica", 12)
        )
        save_button.pack(pady=(5, 10), padx=10)

    def save_api_key(self, key_name, value):
        if not value.strip():
            messagebox.showerror("Error", f"{key_name} cannot be empty!")
            return
        
        config.set_api_key(key_name, value.strip())
        messagebox.showinfo("Success", f"{key_name} has been saved!")

    def view_api_keys(self):
        keys = config.load_config()
        if not keys:
            messagebox.showinfo("API Keys", "No API keys stored yet!")
            return
        
        # Create a new window to display keys
        self.view_window = ctk.CTkToplevel(self)  # Store as instance variable
        self.view_window.title("Stored API Keys")
        self.view_window.geometry("500x400")
        self.view_window.grab_set()  # Make the window modal
        
        # Create scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(self.view_window)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Display each key
        for key_name, key_value in keys.items():
            key_frame = ctk.CTkFrame(scroll_frame)
            key_frame.pack(fill="x", pady=5, padx=5)
            
            # API Name with custom styling
            name_label = ctk.CTkLabel(
                key_frame, 
                text=key_name,
                font=("Helvetica", 14, "bold"),
                text_color=("gray10", "gray90")
            )
            name_label.pack(anchor="w", padx=10, pady=(5,0))
            
            # Masked value with copy button
            value_frame = ctk.CTkFrame(key_frame)
            value_frame.pack(fill="x", padx=10, pady=5)
            
            masked_value = "•" * 20 + key_value[-4:]  # Show only last 4 characters
            value_label = ctk.CTkLabel(
                value_frame,
                text=masked_value,
                font=("Helvetica", 12)
            )
            value_label.pack(side="left", padx=(5,10))
            
            # Copy button
            copy_button = ctk.CTkButton(
                value_frame,
                text="Copy",
                width=60,
                height=25,
                command=lambda v=key_value: self.copy_to_clipboard(v)
            )
            copy_button.pack(side="right", padx=5)
            
        # Close button at the bottom
        close_button = ctk.CTkButton(
            self.view_window,
            text="Close",
            command=self.view_window.destroy,
            width=100
        )
        close_button.pack(pady=10)

    def copy_to_clipboard(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        messagebox.showinfo("Success", "API key copied to clipboard!")

if __name__ == "__main__":
    app = APIKeyManager()
    app.mainloop()
