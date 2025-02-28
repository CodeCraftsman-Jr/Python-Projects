import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

def rename_zip_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".zip"):
                match = re.search(r"'([^']+)'", file)
                if match:
                    new_name = match.group(1) + ".zip"
                    old_path = os.path.join(root, file)
                    new_path = os.path.join(root, new_name)
                    try:
                        os.rename(old_path, new_path)
                        print(f"Renamed: {file} -> {new_name}")
                    except Exception as e:
                        print(f"Error renaming {file}: {e}")

def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        rename_zip_files(folder_selected)
        messagebox.showinfo("Success", "Renaming completed successfully!")

root = tk.Tk()
root.title("ZIP File Renamer")
root.geometry("400x200")

label = tk.Label(root, text="Select a directory to rename ZIP files:")
label.pack(pady=10)

browse_button = tk.Button(root, text="Browse", command=browse_folder)
browse_button.pack(pady=10)

exit_button = tk.Button(root, text="Exit", command=root.quit)
exit_button.pack(pady=10)

root.mainloop()
