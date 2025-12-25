"""
LoRA Dataset Tagger - Main Entry Point
Handles configuration constants and application initialization
"""

import tkinter as tk
from gui_app import GUI_App

# ============================================
# CONFIGURATION CONSTANTS
# ============================================

# Maximum Levenshtein distance for tag similarity suggestions
SIMILARITY_THRESHOLD = 2

# Enable recursive folder scanning for images/tags
ENABLE_RECURSIVE_SCAN = True

# Convert all tags to lowercase on save (False maintains original case)
ENFORCE_LOWERCASE = False

# Tag separator in .txt files (comma + space)
TAG_SEPARATOR = ", "

# Maximum number of undo operations to keep in history
HISTORY_MAX_DEPTH = 10

# Supported image formats
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.webp')

POSITIVE_PROMPT_BLACKLIST = [
    'BREAK', 'lazypos', 'lazyquality', 'masterpiece', 'best quality',
    'high quality', 'absurdres', 'highres'
]

# ============================================
# APPLICATION CONFIGURATION
# ============================================

class AppConfig:
    """Global configuration container"""
    SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLD
    ENABLE_RECURSIVE_SCAN = ENABLE_RECURSIVE_SCAN
    ENFORCE_LOWERCASE = ENFORCE_LOWERCASE
    TAG_SEPARATOR = TAG_SEPARATOR
    HISTORY_MAX_DEPTH = HISTORY_MAX_DEPTH
    SUPPORTED_FORMATS = SUPPORTED_FORMATS
    POSITIVE_PROMPT_BLACKLIST = POSITIVE_PROMPT_BLACKLIST

# ============================================
# MAIN EXECUTION
# ============================================

def main():
    """Initialize and run the application"""
    root = tk.Tk()
    root.title("LoRA Dataset Tagger - Bulk Editor")
    
    # Start fullscreen - cross platform
    try:
        root.state('zoomed')  # Windows
    except:
        try:
            root.attributes('-zoomed', True)  # Linux
        except:
            # Mac or fallback
            w = root.winfo_screenwidth()
            h = root.winfo_screenheight()
            root.geometry(f"{w}x{h}+0+0")
    
    # Import here to avoid issues
    from bulk_editor import BulkEditor
    from data_manager import DataManager
    
    # Create data manager
    data_manager = DataManager(AppConfig)
    
    # Ask user to select folder first
    from tkinter import filedialog, messagebox
    
    folder = filedialog.askdirectory(title="Select Dataset Folder")
    if not folder:
        messagebox.showinfo("No Folder", "No folder selected. Exiting.")
        return
    
    count = data_manager.load_data(folder)
    if count == 0:
        messagebox.showwarning("No Images", "No supported images found in the selected folder.")
        return
    
    # Open bulk editor directly
    bulk_editor = BulkEditor(root, data_manager)
    
    root.mainloop()

if __name__ == "__main__":
    main()