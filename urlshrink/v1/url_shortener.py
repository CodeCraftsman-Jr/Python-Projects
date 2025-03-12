import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyshorteners
from urllib.parse import urlparse, quote
import json
import os
import requests
from datetime import datetime

class GenericShortener:
    def __init__(self, api_key, api_url_template):
        self.api_key = api_key
        self.api_url_template = api_url_template

    def short(self, url):
        encoded_url = quote(url)
        api_url = self.api_url_template.format(api_key=self.api_key, url=encoded_url)
        response = requests.get(api_url)
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get("status") == "success" or result.get("shortenedUrl"):
                    return result.get("shortenedUrl") or result.get("short_url")
                else:
                    raise Exception(result.get("message", "Unknown error"))
            except json.JSONDecodeError:
                # Try plain text response
                if response.text and response.text.startswith('http'):
                    return response.text.strip()
                raise Exception("Invalid response from server")
        raise Exception(f"Failed to shorten URL: {response.status_code}")

class BitlyShortener:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def short(self, url):
        api_url = "https://api-ssl.bitly.com/v4/shorten"
        payload = {"long_url": url}
        response = requests.post(api_url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return response.json()["link"]
        raise Exception(f"Failed to shorten URL: {response.status_code}")

class URLShortenerGUI:
    AVAILABLE_SHORTENERS = {
        "TinyURL": {
            "name": "TinyURL",
            "description": "Fast and reliable URL shortening service",
            "website": "https://tinyurl.com",
            "api_template": "https://api.tinyurl.com/create?api_token={api_key}&url={url}"
        },
        "GPLinks": {
            "name": "GPLinks",
            "description": "Earn money by shortening URLs",
            "website": "https://gplinks.in",
            "api_template": "https://api.gplinks.com/api?api={api_key}&url={url}"
        },
        "UpiShrink": {
            "name": "UpiShrink",
            "description": "URL shortener with UPI payment integration",
            "website": "https://upishrink.com",
            "api_template": "https://upishrink.com/api?api={api_key}&url={url}"
        },
        "ShortXLinks": {
            "name": "ShortXLinks",
            "description": "Earn by sharing shortened links",
            "website": "https://shortxlinks.com",
            "api_template": "https://shortxlinks.com/api?api={api_key}&url={url}"
        },
        "ShrinkForEarn": {
            "name": "ShrinkForEarn",
            "description": "Make money by shortening URLs",
            "website": "https://shrinkforearn.in",
            "api_template": "https://shrinkforearn.in/api?api={api_key}&url={url}"
        },
        "Bitly": {
            "name": "Bitly",
            "description": "Professional URL shortening service",
            "website": "https://bitly.com",
            "api_template": "https://api-ssl.bitly.com/v4/shorten"  # Using custom implementation
        }
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Platform URL Shortener")
        self.root.geometry("900x700")
        
        self.config_file = "shortener_config.json"
        self.shortener_configs = self.load_configs()
        self.logs = []
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create all tabs
        self.create_shortening_tab()
        self.create_settings_tab()
        self.create_accounts_tab()
        self.create_api_test_tab()
        self.create_logs_tab()

    def create_shortening_tab(self):
        shorten_frame = ttk.Frame(self.notebook)
        self.notebook.add(shorten_frame, text="Shorten URL")
        
        # URL Input
        url_frame = ttk.Frame(shorten_frame, padding="10")
        url_frame.pack(fill=tk.X)
        
        ttk.Label(url_frame, text="Enter URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Shorten Button
        ttk.Button(url_frame, text="Shorten URL", command=self.shorten_url).pack(side=tk.LEFT, padx=5)
        
        # Results Area
        result_frame = ttk.LabelFrame(shorten_frame, text="Shortened URLs", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, height=15, width=60)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Status Label
        self.status_label = ttk.Label(shorten_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

    def create_settings_tab(self):
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")

        # Title and Add Custom Shortener button
        header_frame = ttk.Frame(settings_frame)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        
        title_label = ttk.Label(header_frame, text="Available URL Shorteners", font=("Helvetica", 12, "bold"))
        title_label.pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="Add Custom Shortener", command=self.show_add_custom_shortener).pack(side=tk.RIGHT)

        # Scrollable frame for shorteners
        canvas = tk.Canvas(settings_frame)
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create a frame for each shortener service
        for service_id, service_info in self.AVAILABLE_SHORTENERS.items():
            service_frame = ttk.Frame(scrollable_frame)
            service_frame.pack(fill=tk.X, padx=20, pady=5)
            
            # Service info on the left
            info_frame = ttk.Frame(service_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            name_label = ttk.Label(info_frame, text=service_info["name"], font=("Helvetica", 10, "bold"))
            name_label.pack(anchor=tk.W)
            
            desc_label = ttk.Label(info_frame, text=service_info["description"])
            desc_label.pack(anchor=tk.W)
            
            website_label = ttk.Label(info_frame, text=f"Website: {service_info['website']}", foreground="blue", cursor="hand2")
            website_label.pack(anchor=tk.W)
            
            # Status indicator
            status_frame = ttk.Frame(service_frame)
            status_frame.pack(side=tk.RIGHT)
            
            status_label = ttk.Label(status_frame, text="●", font=("Helvetica", 12))
            if service_id in self.shortener_configs:
                status_label.config(foreground="green")
                status_text = ttk.Label(status_frame, text="Configured", foreground="green")
            else:
                status_label.config(foreground="red")
                status_text = ttk.Label(status_frame, text="Not Configured", foreground="red")
            status_label.pack(side=tk.LEFT, padx=(0, 2))
            status_text.pack(side=tk.LEFT, padx=(0, 5))
            
            # Configure button
            config_btn = ttk.Button(
                service_frame, 
                text="Configure",
                command=lambda s=service_id: self.show_configure_dialog(s)
            )
            config_btn.pack(side=tk.RIGHT, padx=5)

            ttk.Separator(scrollable_frame, orient="horizontal").pack(fill=tk.X, padx=20, pady=10)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_accounts_tab(self):
        accounts_frame = ttk.Frame(self.notebook)
        self.notebook.add(accounts_frame, text="My Accounts")

        # Create a frame for the account list
        list_frame = ttk.LabelFrame(accounts_frame, text="My URL Shortener Accounts", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create headers
        headers_frame = ttk.Frame(list_frame)
        headers_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(headers_frame, text="Service", width=20, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(headers_frame, text="API Key", width=30, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(headers_frame, text="Referral Link", width=40, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(headers_frame, text="Actions", width=20, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)

        # Create scrollable frame for accounts
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.accounts_frame = ttk.Frame(canvas)

        self.accounts_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.accounts_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Load accounts
        self.refresh_accounts_list()

    def create_api_test_tab(self):
        test_frame = ttk.Frame(self.notebook)
        self.notebook.add(test_frame, text="API Testing")

        # Test form
        form_frame = ttk.LabelFrame(test_frame, text="Test URL Shortener", padding=20)
        form_frame.pack(fill=tk.X, padx=20, pady=10)

        # Service selection
        ttk.Label(form_frame, text="Select Service:").pack(anchor=tk.W)
        self.test_service = ttk.Combobox(form_frame, values=list(self.AVAILABLE_SHORTENERS.keys()), state="readonly")
        self.test_service.pack(fill=tk.X, pady=(0, 10))

        # Test URL
        ttk.Label(form_frame, text="Test URL:").pack(anchor=tk.W)
        self.test_url = ttk.Entry(form_frame)
        self.test_url.insert(0, "https://www.example.com")
        self.test_url.pack(fill=tk.X, pady=(0, 10))

        # Test button
        ttk.Button(form_frame, text="Run Test", command=self.run_api_test).pack(anchor=tk.W)

        # Results
        result_frame = ttk.LabelFrame(test_frame, text="Test Results", padding=20)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.test_result = scrolledtext.ScrolledText(result_frame, height=10)
        self.test_result.pack(fill=tk.BOTH, expand=True)

    def create_logs_tab(self):
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")

        # Controls
        controls_frame = ttk.Frame(logs_frame)
        controls_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(controls_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.RIGHT)
        ttk.Button(controls_frame, text="Export Logs", command=self.export_logs).pack(side=tk.RIGHT, padx=5)

        # Logs display
        self.logs_display = ttk.Treeview(logs_frame, columns=("Time", "Service", "Action", "Status", "Details"), show="headings")
        self.logs_display.heading("Time", text="Time")
        self.logs_display.heading("Service", text="Service")
        self.logs_display.heading("Action", text="Action")
        self.logs_display.heading("Status", text="Status")
        self.logs_display.heading("Details", text="Details")

        self.logs_display.column("Time", width=150)
        self.logs_display.column("Service", width=100)
        self.logs_display.column("Action", width=100)
        self.logs_display.column("Status", width=100)
        self.logs_display.column("Details", width=400)

        scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.logs_display.yview)
        self.logs_display.configure(yscrollcommand=scrollbar.set)

        self.logs_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0), pady=(0, 20))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 20), padx=(0, 20))

    def refresh_accounts_list(self):
        # Clear existing accounts
        for widget in self.accounts_frame.winfo_children():
            widget.destroy()

        # Add each configured account
        for service, config in self.shortener_configs.items():
            account_frame = ttk.Frame(self.accounts_frame)
            account_frame.pack(fill=tk.X, pady=2)

            # Service name
            ttk.Label(account_frame, text=service, width=20).pack(side=tk.LEFT)

            # API Key (masked)
            api_key = config.get("api_key", "")
            masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "*" * len(api_key)
            api_label = ttk.Label(account_frame, text=masked_key, width=30)
            api_label.pack(side=tk.LEFT)

            # Referral link
            referral_link = config.get("referral", "Not set")
            ref_label = ttk.Label(account_frame, text=referral_link, width=40)
            ref_label.pack(side=tk.LEFT)

            # Action buttons frame
            action_frame = ttk.Frame(account_frame)
            action_frame.pack(side=tk.LEFT)

            def create_edit_command(service_name):
                return lambda: self.show_configure_dialog(service_name, refresh_accounts=True)

            def create_delete_command(service_name):
                return lambda: self.delete_account(service_name)

            ttk.Button(action_frame, text="Edit", command=create_edit_command(service), width=8).pack(side=tk.LEFT, padx=2)
            ttk.Button(action_frame, text="Delete", command=create_delete_command(service), width=8).pack(side=tk.LEFT, padx=2)

            ttk.Separator(self.accounts_frame, orient="horizontal").pack(fill=tk.X, pady=5)

    def delete_account(self, service):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the {service} account?"):
            if service in self.shortener_configs:
                del self.shortener_configs[service]
                self.save_configs()
                self.refresh_accounts_list()
                self.refresh_settings_tab()
                self.add_log(service, "Delete Account", "Success", f"Deleted {service} account configuration")
                messagebox.showinfo("Success", f"{service} account has been deleted")

    def show_add_custom_shortener(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Custom Shortener")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        form_frame = ttk.Frame(dialog, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Shortener details
        ttk.Label(form_frame, text="Name:").pack(anchor=tk.W)
        name_entry = ttk.Entry(form_frame, width=50)
        name_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(form_frame, text="Description:").pack(anchor=tk.W)
        desc_entry = ttk.Entry(form_frame, width=50)
        desc_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(form_frame, text="Website:").pack(anchor=tk.W)
        website_entry = ttk.Entry(form_frame, width=50)
        website_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(form_frame, text="API URL Template:").pack(anchor=tk.W)
        ttk.Label(form_frame, text="Use {api_key} and {url} as placeholders", font=("Helvetica", 8)).pack(anchor=tk.W)
        api_template_entry = ttk.Entry(form_frame, width=50)
        api_template_entry.pack(fill=tk.X, pady=(0, 20))

        def save_custom_shortener():
            name = name_entry.get().strip()
            desc = desc_entry.get().strip()
            website = website_entry.get().strip()
            api_template = api_template_entry.get().strip()

            if not all([name, desc, website, api_template]):
                messagebox.showwarning("Warning", "Please fill in all fields")
                return

            if name in self.AVAILABLE_SHORTENERS:
                messagebox.showerror("Error", "A shortener with this name already exists")
                return

            self.AVAILABLE_SHORTENERS[name] = {
                "name": name,
                "description": desc,
                "website": website,
                "api_template": api_template
            }

            self.add_log(name, "Add Custom Shortener", "Success", "Custom shortener added successfully")
            dialog.destroy()
            self.refresh_settings_tab()

        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="Save", command=save_custom_shortener).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

    def run_api_test(self):
        service = self.test_service.get()
        test_url = self.test_url.get().strip()

        if not service:
            messagebox.showwarning("Warning", "Please select a service")
            return

        if not test_url:
            messagebox.showwarning("Warning", "Please enter a test URL")
            return

        if service not in self.shortener_configs:
            messagebox.showwarning("Warning", "Service not configured. Please configure it in Settings tab first.")
            return

        self.test_result.delete(1.0, tk.END)
        self.test_result.insert(tk.END, f"Testing {service}...\n\n")

        try:
            config = self.shortener_configs[service]
            service_info = self.AVAILABLE_SHORTENERS[service]
            
            if service == "GPLinks":
                shortener = GenericShortener(config["api_key"], service_info["api_template"])
            else:
                s = pyshorteners.Shortener(api_key=config["api_key"])
                shortener = s.tinyurl
            
            short_url = shortener.short(test_url)
            
            # Format the result
            self.test_result.insert(tk.END, f" Test Successful!\n")
            self.test_result.insert(tk.END, f"Original URL: {test_url}\n")
            self.test_result.insert(tk.END, f"Shortened URL: {short_url}\n")

            self.add_log(service, "API Test", "Success", f"URL shortened successfully")
        except Exception as e:
            self.test_result.insert(tk.END, f" Test Failed!\n")
            self.test_result.insert(tk.END, f"Error: {str(e)}\n")
            self.add_log(service, "API Test", "Failed", str(e))

    def add_log(self, service, action, status, details):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append({
            "time": timestamp,
            "service": service,
            "action": action,
            "status": status,
            "details": details
        })
        self.logs_display.insert("", 0, values=(timestamp, service, action, status, details))

    def clear_logs(self):
        if messagebox.askyesno("Clear Logs", "Are you sure you want to clear all logs?"):
            self.logs = []
            for item in self.logs_display.get_children():
                self.logs_display.delete(item)

    def export_logs(self):
        try:
            with open("url_shortener_logs.json", "w") as f:
                json.dump(self.logs, f, indent=2)
            messagebox.showinfo("Success", "Logs exported to url_shortener_logs.json")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export logs: {str(e)}")

    def load_configs(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_configs(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.shortener_configs, f)

    def shorten_url(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.config(text="Please enter a URL")
            return
            
        if not self.is_valid_url(url):
            self.status_label.config(text="Please enter a valid URL")
            return
            
        self.result_text.delete(1.0, tk.END)
        self.status_label.config(text="Processing...")
        self.root.update()
        
        try:
            # Initialize Bitly for referral links
            bitly_config = self.shortener_configs.get("Bitly")
            if bitly_config:
                bitly = BitlyShortener(bitly_config["api_key"])
            else:
                bitly = None
        except Exception as e:
            bitly = None
        
        results = []
        for name, config in self.shortener_configs.items():
            if name == "Bitly":  # Skip Bitly as it's used for referral links
                continue
                
            try:
                service = config.get("service", name)
                service_info = self.AVAILABLE_SHORTENERS[service]
                
                if service == "GPLinks":
                    shortener = GenericShortener(config["api_key"], service_info["api_template"])
                else:
                    s = pyshorteners.Shortener(api_key=config["api_key"])
                    shortener = s.tinyurl
                
                short_url = shortener.short(url)
                
                # Format the result
                results.append(f"{service} = {short_url}")
                
                # If there's a referral link and Bitly is configured
                if config.get("referral"):
                    if bitly:
                        try:
                            short_referral = bitly.short(config["referral"])
                            results.append(f"Earn: {short_referral}")
                        except:
                            results.append(f"Earn: {config['referral']}")
                    else:
                        results.append(f"Earn: {config['referral']}")
                
                results.append("")  # Add blank line between services
                
            except Exception as e:
                results.append(f"{name}: Error - {str(e)}")
                results.append("")
        
        if not results:
            results.append("No URL shorteners configured. Please add configurations in the Settings tab.")
        
        self.result_text.insert(tk.END, "\n".join(results))
        self.status_label.config(text="URLs shortened successfully!")

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def show_configure_dialog(self, service, refresh_accounts=False):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Configure {service}")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Configuration form
        form_frame = ttk.Frame(dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(form_frame, text=f"Configure {service}", font=("Helvetica", 12, "bold")).pack(pady=(0, 20))
        
        # API Key
        ttk.Label(form_frame, text="API Key:").pack(anchor=tk.W)
        api_key_entry = ttk.Entry(form_frame, width=50)
        api_key_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Referral Link
        ttk.Label(form_frame, text="Referral Link (Optional):").pack(anchor=tk.W)
        referral_entry = ttk.Entry(form_frame, width=50)
        referral_entry.pack(fill=tk.X, pady=(0, 20))
        
        # Load existing configuration
        existing_config = self.shortener_configs.get(service, {})
        if existing_config:
            api_key_entry.insert(0, existing_config.get("api_key", ""))
            referral_entry.insert(0, existing_config.get("referral", ""))
        
        def save_config():
            api_key = api_key_entry.get().strip()
            referral = referral_entry.get().strip()
            
            if not api_key:
                messagebox.showwarning("Warning", "Please enter an API key")
                return
            
            # Test the configuration
            try:
                test_url = "https://www.example.com"
                if service == "GPLinks":
                    shortener = GenericShortener(api_key, self.AVAILABLE_SHORTENERS[service]["api_template"])
                else:
                    s = pyshorteners.Shortener(api_key=api_key)
                    shortener = s.tinyurl
                
                short_url = shortener.short(test_url)
                
                # Save configuration
                self.shortener_configs[service] = {
                    "api_key": api_key,
                    "service": service,
                    "referral": referral
                }
                self.save_configs()
                
                # Refresh relevant UI elements
                if refresh_accounts:
                    self.refresh_accounts_list()
                self.refresh_settings_tab()
                
                self.add_log(service, "Configure", "Success", "Configuration saved and tested successfully")
                messagebox.showinfo("Success", "Configuration saved and tested successfully!")
                dialog.destroy()
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to test configuration: {str(e)}")
        
        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="Save", command=save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

    def refresh_settings_tab(self):
        # Find and destroy the Settings tab
        for index, child in enumerate(self.notebook.tabs()):
            if self.notebook.tab(child, "text") == "Settings":
                self.notebook.forget(index)
                break
        
        # Recreate the Settings tab
        self.create_settings_tab()

if __name__ == "__main__":
    root = tk.Tk()
    app = URLShortenerGUI(root)
    root.mainloop()
