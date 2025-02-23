import os
import subprocess
import sys
import time
from datetime import datetime
from tqdm import tqdm
import shutil

def cleanup_git_locks(folder_path):
    """Clean up git lock files if they exist."""
    git_dir = os.path.join(folder_path, '.git')
    if not os.path.exists(git_dir):
        return
    
    lock_files = [
        os.path.join(git_dir, 'index.lock'),
        os.path.join(git_dir, 'HEAD.lock'),
        os.path.join(git_dir, 'config.lock'),
        os.path.join(git_dir, 'refs', 'heads', 'master.lock'),
        os.path.join(git_dir, 'refs', 'heads', 'main.lock')
    ]
    
    for lock_file in lock_files:
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
                print(f" Removed lock file: {lock_file}")
        except Exception as e:
            print(f" Warning: Could not remove lock file {lock_file}: {str(e)}")

def run_git_command(command, cwd=None):
    try:
        result = subprocess.run(command, cwd=cwd, shell=True, check=True,
                              capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def get_all_files(folder_path):
    """Get all files in the folder recursively."""
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.startswith('.git'):  # Skip .git files
                all_files.append(os.path.join(root, file))
    return all_files

def format_size(size):
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

def setup_git_repository(folder_path, files, pbar=None):
    # Clean up any existing git locks
    cleanup_git_locks(folder_path)

    # Initialize git if not already initialized
    if not os.path.exists(os.path.join(folder_path, '.git')):
        print(f"\n Initializing git in: {folder_path}")
        success, output = run_git_command('git init', folder_path)
        if not success:
            print(f" Failed to initialize git in {folder_path}: {output}")
            return False
        print(" Git initialized successfully")

    # Create progress bars for different stages
    with tqdm(total=len(files), desc=" Adding files  ", position=1, leave=False) as add_pbar, \
         tqdm(total=len(files), desc=" Committing   ", position=2, leave=False) as commit_pbar:
        
        # Process each file
        for file in files:
            rel_path = os.path.relpath(file, folder_path)
            file_size = os.path.getsize(file)
            
            # Show current file details
            print(f"\n Processing: {rel_path} ({format_size(file_size)})")
            
            # Clean up locks before each operation
            cleanup_git_locks(folder_path)
            
            # Add the file
            success, output = run_git_command(f'git add "{rel_path}"', folder_path)
            if not success:
                print(f" Failed to add file {rel_path}: {output}")
                continue
            add_pbar.update(1)
            print(f" Added: {rel_path}")

            # Clean up locks before commit
            cleanup_git_locks(folder_path)

            # Commit the file
            commit_message = f"Add {rel_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            success, output = run_git_command(f'git commit -m "{commit_message}"', folder_path)
            if not success and "nothing to commit" not in output.lower():
                print(f" Failed to commit file {rel_path}: {output}")
                continue
            commit_pbar.update(1)
            print(f" Committed: {rel_path}")

    if pbar:
        pbar.update(1)
    
    return True

def push_to_remote(folder_path, remote_url):
    """Push the repository to remote."""
    print(f"\n Pushing to remote: {remote_url}")
    
    # Clean up any existing git locks
    cleanup_git_locks(folder_path)

    # Add remote if URL is provided and remote doesn't exist
    success, output = run_git_command('git remote -v', folder_path)
    if 'origin' not in output:
        print(" Adding remote origin...")
        success, output = run_git_command(f'git remote add origin {remote_url}', folder_path)
        if not success:
            print(f" Failed to add remote in {folder_path}: {output}")
            return False
        print(" Remote added successfully")

    # Clean up locks before push
    cleanup_git_locks(folder_path)

    # Push to remote with progress bar
    with tqdm(total=1, desc=" Pushing     ", position=1, leave=False) as push_pbar:
        success, output = run_git_command('git push -u origin master', folder_path)
        if not success:
            print(f" Failed to push in {folder_path}: {output}")
            return False
        push_pbar.update(1)
    
    print(" Push completed successfully")
    return True

def process_folders(root_path, github_url, start_from=None, delay=5):
    # Get all folders
    print(f"\n Scanning directories in: {root_path}")
    folders = [f.path for f in os.scandir(root_path) if f.is_dir()]
    folders.sort()  # Sort folders for consistent ordering
    print(f" Found {len(folders)} folders")
    
    # Create or load progress file
    progress_file = os.path.join(root_path, 'git_upload_progress.txt')
    completed_folders = set()
    
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            completed_folders = set(f.read().splitlines())
        print(f" Found {len(completed_folders)} previously completed folders")
    
    # If start_from is specified, filter folders
    if start_from:
        try:
            start_index = folders.index(start_from)
            folders = folders[start_index:]
            print(f" Starting from folder: {start_from}")
        except ValueError:
            print(f" Warning: Start folder '{start_from}' not found. Processing all folders.")
    
    # Main progress bar for folders
    with tqdm(total=len(folders), desc=" Total Progress", position=0) as pbar:
        for folder in folders:
            if folder in completed_folders:
                print(f"\n Skipping completed folder: {folder}")
                pbar.update(1)
                continue
                
            folder_name = os.path.basename(folder)
            print(f"\n\n{'='*80}")
            print(f" Processing folder: {folder_name}")
            print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            # Clean up any existing git locks before starting
            cleanup_git_locks(folder)
            
            # Get all files in the folder
            files = get_all_files(folder)
            if not files:
                print(f" No files found in {folder_name}, skipping...")
                pbar.update(1)
                continue
            
            print(f" Found {len(files)} files to process")

            # Setup git and commit files
            if setup_git_repository(folder, files, pbar):
                # Push to remote
                if push_to_remote(folder, github_url):
                    print(f"\n Successfully processed folder: {folder_name}")
                    # Record progress
                    with open(progress_file, 'a') as f:
                        f.write(f"{folder}\n")
                    
                    if folders.index(folder) < len(folders) - 1:
                        print(f"\n Waiting {delay} seconds before next folder...")
                        time.sleep(delay)
                else:
                    print(f"\n Failed to push {folder_name} to remote")
                    print("\n To resume, run:")
                    print(f"python gitpostbatch.py \"{root_path}\" \"{github_url}\" \"{folder}\"")
                    break
            else:
                print(f"\n Failed to process {folder_name}")
                print("\n To resume, run:")
                print(f"python gitpostbatch.py \"{root_path}\" \"{github_url}\" \"{folder}\"")
                break

def main():
    if len(sys.argv) < 3:
        print("Usage: python gitpostbatch.py <root_folder> <github_repo_url> [start_from_folder]")
        sys.exit(1)

    root_folder = sys.argv[1]
    github_url = sys.argv[2]
    start_from = sys.argv[3] if len(sys.argv) > 3 else None

    if not os.path.exists(root_folder):
        print(f"Error: Folder {root_folder} does not exist!")
        sys.exit(1)

    print("\n Starting Git Batch Upload Process")
    print(f" Root Folder: {root_folder}")
    print(f" GitHub URL: {github_url}")
    if start_from:
        print(f" Starting from: {start_from}")
    print("\n")

    process_folders(root_folder, github_url, start_from)
    print("\n Process completed!")

if __name__ == "__main__":
    main()