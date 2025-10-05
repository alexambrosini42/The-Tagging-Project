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

# ============================================
# MAIN EXECUTION
# ============================================

def main():
    """Initialize and run the application"""
    root = tk.Tk()
    root.title("LoRA Dataset Tagger")
    
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
    
    app = GUI_App(root, AppConfig)
    
    root.mainloop()

if __name__ == "__main__":
    main()