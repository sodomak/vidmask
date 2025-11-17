#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Starting application...")

def main():
    root = tk.Tk()

    # Set window title
    root.title("VidMask")

    # Set WM_CLASS properly for proper identification in launchers
    # WM_CLASS has two components: instance name and class name
    # This ensures the app shows as "VidMask" instead of "Tk" in the dash
    root.wm_class("VidMask")

    root.minsize(800, 600)
    
    # Create main window
    from src.gui.main_window import MainWindow
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main() 