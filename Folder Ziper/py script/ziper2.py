import os
import zipfile
import shutil
import threading
import queue
import tkinter as tk
from tkinter import filedialog
from tkinter import scrolledtext

# A thread-safe queue for log messages
log_queue = queue.Queue()

def log_message(message):
    """Push a log message into the queue."""
    log_queue.put(message)

def zip_folder(folder_path):
    """
    Create a zip file from the contents of folder_path.
    The zip archive will be saved as folder_path+'.zip'.
    """
    zip_filename = folder_path + '.zip'
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the directory and add files with a relative path.
        for root, _, files in os.walk(folder_path):
            for file in files:
                abs_file_path = os.path.join(root, file)
                arcname = os.path.relpath(abs_file_path, start=folder_path)
                zipf.write(abs_file_path, arcname)
    return zip_filename

def process_main_folder(main_folder):
    """
    Processes the main folder by iterating through each first-level
    subfolder (B folders) and zipping each nested folder (C folders)
    inside them. After zipping, the original folder is deleted.
    """
    try:
        b_dirs = [d for d in os.listdir(main_folder)
                  if os.path.isdir(os.path.join(main_folder, d))]
        for b in b_dirs:
            b_path = os.path.join(main_folder, b)
            log_message(f"Processing folder: {b_path}")
            # List the nested folders inside the B folder.
            c_dirs = [d for d in os.listdir(b_path)
                      if os.path.isdir(os.path.join(b_path, d))]
            for c in c_dirs:
                c_path = os.path.join(b_path, c)
                log_message(f"Zipping folder: {c_path}")
                zip_folder(c_path)
                log_message(f"Created zip for: {c_path}")
                shutil.rmtree(c_path)
                log_message(f"Deleted folder: {c_path}")
        log_message("Processing complete.")
    except Exception as e:
        log_message(f"Error: {str(e)}")

def start_processing():
    """
    Start the processing of the selected folder in a separate thread.
    """
    folder = selected_folder.get()
    if not folder:
        log_message("Please select a folder first.")
        return
    log_message("Starting processing...")
    t = threading.Thread(target=process_main_folder, args=(folder,), daemon=True)
    t.start()

def select_folder():
    """
    Open a folder selection dialog and update the selected folder.
    """
    folder = filedialog.askdirectory()
    if folder:
        selected_folder.set(folder)
        log_message(f"Selected folder: {folder}")

def update_log():
    """
    Check the log queue for new messages and insert them into the text area.
    """
    try:
        while True:
            message = log_queue.get_nowait()
            log_text.insert(tk.END, message + "\n")
            log_text.see(tk.END)
    except queue.Empty:
        pass
    root.after(100, update_log)

# Create the main window
root = tk.Tk()
root.title("Folder Zipping Tool with Real-Time Logs")

# Variable to hold the selected folder path.
selected_folder = tk.StringVar()

# Create a frame for the controls.
control_frame = tk.Frame(root)
control_frame.pack(padx=10, pady=10, fill=tk.X)

# Button to select a folder.
select_btn = tk.Button(control_frame, text="Select Folder", command=select_folder)
select_btn.pack(side=tk.LEFT, padx=5)

# Label to display the selected folder path.
folder_label = tk.Label(control_frame, textvariable=selected_folder, anchor="w", width=50)
folder_label.pack(side=tk.LEFT, padx=5)

# Button to start processing.
start_btn = tk.Button(root, text="Start Processing", command=start_processing)
start_btn.pack(padx=10, pady=(0,10))

# ScrolledText widget to display real-time logs.
log_text = scrolledtext.ScrolledText(root, width=80, height=20)
log_text.pack(padx=10, pady=10)

# Begin periodic log updates.
root.after(100, update_log)

# Start the Tkinter event loop.
root.mainloop()
