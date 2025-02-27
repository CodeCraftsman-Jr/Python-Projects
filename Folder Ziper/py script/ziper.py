import os
import shutil
import zipfile
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor

# Setup logging
log_file = "zipper.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def thread_safe_log(message):
    """Log message to the file and update the GUI in a thread-safe manner."""
    logging.info(message)
    # Schedule the update in the main thread
    root.after(0, lambda: (log_text.insert(tk.END, message + "\n"), log_text.see(tk.END)))

def zip_folder(folder_path, output_path):
    """Compress a folder into a zip file and delete the original folder."""
    folder_name = os.path.basename(folder_path)
    zip_filename = os.path.join(output_path, folder_name + ".zip")
    try:
        thread_safe_log(f"📦 Zipping: {folder_name} ...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root_dir, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, start=folder_path)
                    zipf.write(file_path, arcname=arcname)
        thread_safe_log(f"✅ Successfully zipped: {folder_name}")
        shutil.rmtree(folder_path)
        thread_safe_log(f"🗑️ Deleted original folder: {folder_name}")
    except Exception as e:
        thread_safe_log(f"❌ Error zipping {folder_name}: {str(e)}")

def process_folders():
    """Handles folder selection, parallel zipping, and real-time logging."""
    source_folder = filedialog.askdirectory(title="Select Source Folder")
    if not source_folder:
        return
    output_folder = filedialog.askdirectory(title="Select Destination Folder")
    if not output_folder:
        return
    folders = [os.path.join(source_folder, f) for f in os.listdir(source_folder)
               if os.path.isdir(os.path.join(source_folder, f))]
    if not folders:
        messagebox.showinfo("Info", "No folders found to zip.")
        return

    thread_safe_log(f"🚀 Starting compression of {len(folders)} folders...")

    # Process folders in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(zip_folder, folders, [output_folder] * len(folders))

    thread_safe_log("🎉 All folders processed successfully!")
    messagebox.showinfo("Success", "All folders zipped and deleted successfully!")

# GUI Setup
root = tk.Tk()
root.title("Folder Zipper with Real-Time Logs")
root.geometry("500x400")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(expand=True)

title_label = tk.Label(frame, text="Folder Zipper (Real-Time Logs)", font=("Arial", 14, "bold"))
title_label.pack(pady=5)

start_button = tk.Button(frame, text="Select Folders & Start", command=process_folders, font=("Arial", 12))
start_button.pack(pady=10)

log_text = tk.Text(frame, height=12, width=50, font=("Arial", 10))
log_text.pack(pady=5)
log_text.insert(tk.END, "Logs will appear here...\n")

scrollbar = tk.Scrollbar(frame, command=log_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
log_text.config(yscrollcommand=scrollbar.set)

root.mainloop()
