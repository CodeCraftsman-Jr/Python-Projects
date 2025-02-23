import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import customtkinter as ctk
from github import Github
import json
import os
import shutil
from datetime import datetime
import subprocess
import threading
from tqdm import tqdm
import webbrowser
import re
import time
import tempfile

class GitUploaderGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("GitHub Folder Uploader")
        self.window.geometry("1200x800")
        ctk.set_appearance_mode("dark")
        
        self.github_instance = None
        self.user = None
        self.selected_directory = None
        self.selected_repo = None
        
        self.create_gui()
        self.load_saved_token()

    def create_gui(self):
        # Create main container
        self.main_container = ctk.CTkFrame(self.window)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel for authentication and directory selection
        self.left_panel = ctk.CTkFrame(self.main_container, width=300)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Authentication section
        self.auth_frame = ctk.CTkFrame(self.left_panel)
        self.auth_frame.pack(fill=tk.X, padx=5, pady=5)

        # Add help text and button for token creation
        self.help_frame = ctk.CTkFrame(self.auth_frame)
        self.help_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.help_label = ctk.CTkLabel(self.help_frame, 
            text="You need a GitHub Personal Access Token to login.",
            wraplength=250)
        self.help_label.pack(pady=2)
        
        self.create_token_button = ctk.CTkButton(
            self.help_frame, 
            text="Create New Token", 
            command=self.open_token_page,
            height=25)
        self.create_token_button.pack(pady=2)

        self.token_label = ctk.CTkLabel(self.auth_frame, text="Personal Access Token:")
        self.token_label.pack(pady=5)

        self.token_entry = ctk.CTkEntry(self.auth_frame, show="*")
        self.token_entry.pack(fill=tk.X, padx=5, pady=5)

        self.show_token_var = tk.BooleanVar(value=False)
        self.show_token_checkbox = ctk.CTkCheckBox(
            self.auth_frame, 
            text="Show token", 
            variable=self.show_token_var,
            command=self.toggle_token_visibility)
        self.show_token_checkbox.pack(pady=2)

        self.login_button = ctk.CTkButton(self.auth_frame, text="Login", command=self.login)
        self.login_button.pack(pady=5)

        self.logout_button = ctk.CTkButton(self.auth_frame, text="Logout", command=self.logout, state="disabled")
        self.logout_button.pack(pady=5)

        # Remember token checkbox
        self.remember_var = tk.BooleanVar(value=True)
        self.remember_checkbox = ctk.CTkCheckBox(
            self.auth_frame, 
            text="Remember token", 
            variable=self.remember_var)
        self.remember_checkbox.pack(pady=5)

        # Directory selection section
        self.dir_frame = ctk.CTkFrame(self.left_panel)
        self.dir_frame.pack(fill=tk.X, padx=5, pady=5)

        self.select_dir_button = ctk.CTkButton(self.dir_frame, text="Select Directory", command=self.select_directory)
        self.select_dir_button.pack(pady=5)

        self.dir_label = ctk.CTkLabel(self.dir_frame, text="No directory selected", wraplength=280)
        self.dir_label.pack(pady=5)

        # Repository section
        self.repo_frame = ctk.CTkFrame(self.left_panel)
        self.repo_frame.pack(fill=tk.X, padx=5, pady=5)

        self.repo_label = ctk.CTkLabel(self.repo_frame, text="Repository:")
        self.repo_label.pack(pady=5)

        self.repo_combobox = ctk.CTkComboBox(self.repo_frame, values=[""])
        self.repo_combobox.pack(fill=tk.X, padx=5, pady=5)

        self.new_repo_button = ctk.CTkButton(self.repo_frame, text="Create New Repo", command=self.create_new_repo)
        self.new_repo_button.pack(pady=5)

        # Upload button
        self.upload_button = ctk.CTkButton(self.left_panel, text="Start Upload", command=self.start_upload)
        self.upload_button.pack(pady=20)

        # Right panel for logs
        self.right_panel = ctk.CTkFrame(self.main_container)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Detailed log
        self.log_label = ctk.CTkLabel(self.right_panel, text="Detailed Log")
        self.log_label.pack(pady=5)

        self.log_text = scrolledtext.ScrolledText(self.right_panel, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Summary log
        self.summary_label = ctk.CTkLabel(self.right_panel, text="Summary")
        self.summary_label.pack(pady=5)

        self.summary_text = scrolledtext.ScrolledText(self.right_panel, height=10)
        self.summary_text.pack(fill=tk.BOTH, padx=5, pady=5)

    def open_token_page(self):
        webbrowser.open("https://github.com/settings/tokens/new?scopes=repo&description=Git+Uploader+GUI")
        messagebox.showinfo("Token Creation Help", 
            "1. Log in to GitHub if needed\n"
            "2. Set an expiration date\n"
            "3. Make sure 'repo' permission is checked\n"
            "4. Click 'Generate token'\n"
            "5. Copy the token and paste it here")

    def toggle_token_visibility(self):
        if self.show_token_var.get():
            self.token_entry.configure(show="")
        else:
            self.token_entry.configure(show="*")

    def save_token(self, token):
        if self.remember_var.get():
            try:
                token_file = os.path.join(os.path.dirname(__file__), 'github_token.json')
                with open(token_file, 'w') as f:
                    json.dump({'token': token}, f)
            except Exception as e:
                messagebox.showwarning("Warning", f"Failed to save token: {str(e)}")

    def load_saved_token(self):
        try:
            token_file = os.path.join(os.path.dirname(__file__), 'github_token.json')
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    data = json.load(f)
                    self.token_entry.insert(0, data.get('token', ''))
        except Exception as e:
            messagebox.showwarning("Warning", f"Failed to load saved token: {str(e)}")

    def login(self):
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showerror("Login Error", "Please enter your Personal Access Token")
            return
            
        try:
            self.github_instance = Github(token)
            self.user = self.github_instance.get_user()
            # Test the connection
            test = self.user.login
            
            if self.remember_var.get():
                self.save_token(token)
            
            self.login_button.configure(state="disabled")
            self.logout_button.configure(state="normal")
            self.update_repo_list()
            self.log_message("Successfully logged in as " + self.user.login)
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                error_msg = ("Invalid token. Please make sure you:\n"
                           "1. Created a new token with 'repo' permission\n"
                           "2. Copied the entire token\n"
                           "3. Token hasn't expired\n"
                           "\nClick 'Create New Token' to generate a new one.")
            elif "403" in error_msg:
                error_msg = "Access denied. Please make sure your token has 'repo' permission."
            messagebox.showerror("Login Error", error_msg)
            self.github_instance = None
            self.user = None

    def logout(self):
        self.github_instance = None
        self.user = None
        self.token_entry.delete(0, tk.END)
        self.login_button.configure(state="normal")
        self.logout_button.configure(state="disabled")
        self.repo_combobox.configure(values=[""])
        self.log_message("Logged out successfully")
        
        if not self.remember_var.get():
            try:
                token_file = os.path.join(os.path.dirname(__file__), 'github_token.json')
                os.remove(token_file)
            except FileNotFoundError:
                pass

    def select_directory(self):
        self.selected_directory = filedialog.askdirectory()
        if self.selected_directory:
            self.dir_label.configure(text=self.selected_directory)
            self.log_message(f"Selected directory: {self.selected_directory}")

    def update_repo_list(self):
        if self.user:
            repos = [repo.name for repo in self.user.get_repos()]
            self.repo_combobox.configure(values=repos)

    def create_new_repo(self):
        if not self.github_instance:
            messagebox.showerror("Error", "Please login first")
            return

        repo_name = simpledialog.askstring("New Repository", "Enter repository name:")
        if repo_name:
            try:
                self.user.create_repo(repo_name)
                self.update_repo_list()
                self.repo_combobox.set(repo_name)
                self.log_message(f"Created new repository: {repo_name}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def log_message(self, message, is_summary=False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        if is_summary:
            self.summary_text.insert(tk.END, log_entry)
            self.summary_text.see(tk.END)

    def handle_git_error(self, error_output, folder_path):
        """Handle common git errors and try to fix them"""
        try:
            if "remote origin already exists" in error_output:
                self.log_message("Fixing remote origin issue...")
                self.run_git_command('git remote remove origin', folder_path)
                return True
            elif "not a git repository" in error_output:
                self.log_message("Reinitializing git repository...")
                self.remove_git_directories(folder_path)
                success, _ = self.run_git_command('git init', folder_path)
                return success
            elif "repository rule violations" in error_output:
                self.log_message("Branch is protected, will create pull request instead...")
                return True
            elif "failed to push" in error_output or "rejected" in error_output:
                self.log_message("Push failed, trying to force push...")
                success, _ = self.run_git_command('git push -u origin main --force', folder_path)
                return success
            elif "branch 'main' already exists" in error_output:
                self.log_message("Branch exists, switching to main...")
                self.run_git_command('git checkout main', folder_path)
                return True
            elif "does not have a commit checked out" in error_output:
                self.log_message("Fixing commit checkout issue...")
                self.run_git_command('git checkout --orphan temp', folder_path)
                self.run_git_command('git add .', folder_path)
                self.run_git_command('git commit -m "Initial commit"', folder_path)
                self.run_git_command('git branch -D main', folder_path)
                self.run_git_command('git branch -m main', folder_path)
                return True
            return False
        except Exception as e:
            self.log_message(f"Error in error handler: {str(e)}")
            return False

    def safe_git_command(self, command, folder_path, max_retries=3):
        """Execute git command with retries and error handling"""
        for attempt in range(max_retries):
            success, output = self.run_git_command(command, folder_path)
            if success:
                return True, output
            
            self.log_message(f"Command failed (attempt {attempt + 1}/{max_retries}): {output}")
            
            # Try to handle the error
            if self.handle_git_error(output.lower(), folder_path):
                # If error was handled, retry the original command
                continue
            elif attempt < max_retries - 1:
                # Wait before retrying
                time.sleep(2)
                continue
            
            return False, output
        
        return False, "Max retries exceeded"

    def run_git_command(self, command, cwd=None):
        try:
            # Add a timeout of 60 seconds
            result = subprocess.run(
                command, 
                cwd=cwd, 
                shell=True, 
                check=True,
                capture_output=True, 
                text=True,
                timeout=60  # 60 second timeout
            )
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 60 seconds"
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    def remove_git_directories(self, start_path):
        """Recursively remove all .git directories"""
        for root, dirs, _ in os.walk(start_path, topdown=True):
            if '.git' in dirs:
                git_path = os.path.join(root, '.git')
                try:
                    shutil.rmtree(git_path)
                    self.log_message(f"Removed git directory from: {root}")
                except Exception as e:
                    self.log_message(f"Failed to remove .git from {root}: {str(e)}")
                dirs.remove('.git')

    def create_pull_request(self, repo_name, branch_name):
        """Create a pull request for the uploaded changes"""
        try:
            repo = self.user.get_repo(repo_name)
            
            # Create pull request
            title = f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            body = "Automated upload via Git Uploader GUI"
            pr = repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base='main'  # or 'master' depending on the default branch
            )
            self.log_message(f"Created pull request: {pr.html_url}")
            return True
        except Exception as e:
            self.log_message(f"Failed to create pull request: {str(e)}")
            return False

    def create_unique_repo_name(self, base_name):
        """Create a unique repository name by adding timestamp and counter if needed."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        repo_name = f"{base_name}_{timestamp}"
        counter = 1
        
        while True:
            try:
                # Try to get repo - if it exists, we need a new name
                self.user.get_repo(repo_name)
                # If we get here, repo exists - try next counter
                repo_name = f"{base_name}_{timestamp}_{counter}"
                counter += 1
            except:
                # Repo doesn't exist - this name is good
                return repo_name

    def upload_folder(self, folder_path, repo_name):
        try:
            # Get the token for authentication
            token = self.token_entry.get().strip()
            
            # Try to get existing repo first
            try:
                repo = self.user.get_repo(repo_name)
                # If repo exists and has protection rules, create a new repo with a unique name
                if "repository rule violations" in str(repo.get_branch("main")):
                    repo_name = self.create_unique_repo_name(repo_name)
                    self.log_message(f"Repository has protection rules. Creating new repository: {repo_name}")
                    repo = self.user.create_repo(repo_name)
            except:
                self.log_message("Creating new repository...")
                try:
                    repo = self.user.create_repo(repo_name)
                except Exception as e:
                    if "name already exists" in str(e):
                        repo_name = self.create_unique_repo_name(repo_name)
                        self.log_message(f"Repository name taken. Creating with new name: {repo_name}")
                        repo = self.user.create_repo(repo_name)
                    else:
                        raise e

            repo_url = f"https://{token}@github.com/{self.user.login}/{repo_name}.git"
            
            # Remove all .git directories recursively
            self.log_message("Removing any existing git repositories...")
            self.remove_git_directories(folder_path)

            # Initialize fresh git repository
            self.log_message("Initializing fresh git repository...")
            success, output = self.safe_git_command('git init', folder_path)
            if not success:
                self.log_message(f"Failed to initialize git: {output}", True)
                return False

            # Configure git
            self.safe_git_command(f'git config user.name "{self.user.login}"', folder_path)
            self.safe_git_command('git config user.email "noreply@github.com"', folder_path)

            # Check current branch and switch to main if needed
            success, current_branch = self.safe_git_command('git branch --show-current', folder_path)
            if success:
                if current_branch.strip() == '':
                    # No branches yet, create main
                    success, output = self.safe_git_command('git checkout -b main', folder_path)
                    if not success:
                        self.log_message(f"Failed to create main branch: {output}", True)
                        return False
                elif current_branch.strip() != 'main':
                    # Try to switch to main if it exists
                    success, _ = self.safe_git_command('git checkout main', folder_path)
                    if not success:
                        # Main doesn't exist, create it
                        success, output = self.safe_git_command('git checkout -b main', folder_path)
                        if not success:
                            self.log_message(f"Failed to create main branch: {output}", True)
                            return False

            # Add files one directory at a time
            self.log_message("Adding files...")
            files_added = False
            
            for root, dirs, files in os.walk(folder_path):
                if '.git' in dirs:
                    dirs.remove('.git')
                
                try:
                    # Add files in current directory
                    rel_path = os.path.relpath(root, folder_path)
                    if rel_path != '.':
                        success, output = self.safe_git_command(f'git add "{rel_path}"', folder_path)
                        if success:
                            files_added = True
                    
                    # Add individual files in current directory
                    for file in files:
                        file_path = os.path.relpath(os.path.join(root, file), folder_path)
                        try:
                            # Skip if file is too large (> 100MB)
                            size = os.path.getsize(os.path.join(root, file))
                            if size > 100 * 1024 * 1024:  # 100MB
                                self.log_message(f"Skipping large file ({size/1024/1024:.1f}MB): {file_path}", True)
                                continue
                            
                            success, output = self.safe_git_command(f'git add "{file_path}"', folder_path)
                            if success:
                                files_added = True
                                self.log_message(f"Added: {file_path}")
                        except Exception as e:
                            self.log_message(f"Error processing {file_path}: {str(e)}")
                            continue
                except Exception as e:
                    self.log_message(f"Error processing directory {rel_path}: {str(e)}")
                    continue

            if not files_added:
                self.log_message("No files were added to the repository", True)
                return False

            # Commit files
            self.log_message("Committing files...")
            commit_message = f"Upload {os.path.basename(folder_path)} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            success, output = self.safe_git_command(f'git commit -m "{commit_message}"', folder_path)
            if not success and "nothing to commit" not in output.lower():
                self.log_message(f"Failed to commit: {output}", True)
                return False

            # Set up remote
            self.safe_git_command('git remote remove origin', folder_path)
            success, _ = self.safe_git_command(f'git remote add origin {repo_url}', folder_path)

            # Push to GitHub
            self.log_message("Pushing to GitHub...")
            success, output = self.safe_git_command('git push -u origin main', folder_path)
            if not success:
                self.log_message(f"Failed to push: {output}", True)
                return False

            self.log_message(f"Successfully uploaded to GitHub! Repository: {repo_name}", True)
            webbrowser.open(f"https://github.com/{self.user.login}/{repo_name}")
            return True
            
        except Exception as e:
            self.log_message(f"Error during upload: {str(e)}", True)
            return False

    def start_upload(self):
        if not all([self.github_instance, self.selected_directory, self.repo_combobox.get()]):
            messagebox.showerror("Error", "Please make sure you're logged in, a directory is selected, and a repository is chosen")
            return
            
        # Start the upload process in a separate thread
        threading.Thread(target=self.upload_folder, 
                       args=(self.selected_directory, self.repo_combobox.get()), 
                       daemon=True).start()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = GitUploaderGUI()
    app.run()
