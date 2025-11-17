import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .settings_frame import SettingsFrame
from .preview_frame import PreviewFrame
from ..locales import TRANSLATIONS, LANGUAGE_NAMES
import os
import json
import mediapipe as mp
import re
import cv2
import subprocess
import queue
import numpy as np
from src.version import VERSION
from ..utils.theme import ThemeManager

class MainWindow(ttk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        
        # Initialize theme manager first
        self.theme_manager = ThemeManager(root)
        
        # Set config paths
        self.old_config_dir = os.path.expanduser('~/.config/vcam-bg')
        self.old_config_file = os.path.join(self.old_config_dir, 'config.json')
        self.config_dir = os.path.expanduser('~/.config/vidmask')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        
        # Migrate old config if exists
        self.migrate_config()
        
        # Initialize variables
        self.create_variables()
        
        # Create widgets and menus
        self.create_frames()
        self.create_menu()
        self.create_bindings()
        
        # Load and apply settings last
        self.load_settings()
        self.apply_loaded_settings()
        
        # Configure root window
        self.root.minsize(800, 600)
        self.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Load camera devices with delayed retry for v4l2loopback initialization
        self.settings_frame.load_camera_devices()

        # Schedule a retry after 500ms to catch devices that weren't ready initially
        self.root.after(500, self._retry_device_detection)

        print("GUI created")

    def _retry_device_detection(self):
        """Retry device detection after initial load to catch late-initializing devices"""
        try:
            # Save current selections
            current_input = self.settings_frame.input_device.get()
            current_output = self.settings_frame.output_device.get()

            # Reload devices
            self.settings_frame.load_camera_devices()

            # Restore selections if they still exist
            if current_input and current_input in self.settings_frame.input_combo['values']:
                self.settings_frame.input_device.set(current_input)
            if current_output and current_output in self.settings_frame.output_combo['values']:
                self.settings_frame.output_device.set(current_output)

            print("Device detection retry completed")
        except Exception as e:
            print(f"Error during device detection retry: {e}")

    def create_frames(self):
        """Create main application frames"""
        # Settings frame (left side)
        self.settings_frame = SettingsFrame(self)
        self.settings_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Preview frame (right side)
        self.preview_frame = PreviewFrame(self)
        self.preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        self.file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr('file'), menu=self.file_menu)
        self.file_menu.add_command(label=self.tr('import_settings'), command=self.import_settings, accelerator='Ctrl+I')
        self.file_menu.add_command(label=self.tr('export_settings'), command=self.export_settings, accelerator='Ctrl+E')
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.tr('save_settings'), command=self.save_settings, accelerator='Ctrl+S')
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.tr('reset_settings'), command=self.reset_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.tr('exit'), command=self.root.quit, accelerator='Ctrl+Q')
        
        # View menu
        self.view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr('view'), menu=self.view_menu)
        
        # Language submenu
        self.language_menu = tk.Menu(self.view_menu, tearoff=0)
        self.view_menu.add_cascade(label=self.tr('language'), menu=self.language_menu)
        
        # Dynamically add language options from available translations
        for lang_code in sorted(TRANSLATIONS.keys()):
            self.language_menu.add_radiobutton(
                label=LANGUAGE_NAMES.get(lang_code, lang_code),
                value=lang_code,
                variable=self.language,
                command=self.change_language
            )
        
        # Theme submenu
        self.theme_menu = tk.Menu(self.view_menu, tearoff=0)
        self.view_menu.add_cascade(label=self.tr('theme'), menu=self.theme_menu)
        
        # Add theme options
        for theme_option in ['system', 'gtk', 'light', 'dark']:
            self.theme_menu.add_radiobutton(
                label=self.tr(theme_option),
                value=theme_option,
                variable=self.theme,
                command=lambda t=theme_option: self.theme_manager.set_theme(t)
            )
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr('help'), menu=help_menu)
        help_menu.add_command(label=self.tr('about'), command=self.show_about)

    def tr(self, key):
        """Get translated string"""
        return TRANSLATIONS[self.language.get()].get(key, key)

    def update_title(self):
        """Update window title"""
        self.root.title(self.tr('title'))

    def change_language(self):
        """Change application language"""
        # Update window title
        self.update_title()
        
        # Update menu labels
        self.create_menu()
        
        # Update frame labels
        self.settings_frame.update_labels()
        self.preview_frame.update_labels()

    def reset_settings(self):
        """Reset all settings to default values"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default?"):
            # Stop camera if running
            if self.preview_frame.is_running:
                self.preview_frame.toggle_camera()
            
            # Reset settings to defaults
            self.settings_frame.reset_to_defaults()
            messagebox.showinfo("Settings Reset", "All settings have been reset to default values")

    def show_about(self):
        """Show about dialog"""
        text = self.tr('about_text').format(version=VERSION)
        messagebox.showinfo(self.tr('about_title'), text)

    def migrate_config(self):
        """Migrate config from old path to new path if needed"""
        try:
            if os.path.exists(self.old_config_file) and not os.path.exists(self.config_file):
                print(f"Migrating config from {self.old_config_file} to {self.config_file}")
                # Create new config directory
                os.makedirs(self.config_dir, exist_ok=True)
                # Copy config file
                import shutil
                shutil.copy2(self.old_config_file, self.config_file)
                # Don't delete old config yet - keep as backup
                print("Config migration successful")
        except Exception as e:
            print(f"Error migrating config: {e}")

    def load_settings(self):
        """Load settings from config file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    
                    # Update variables with saved settings
                    self.fps.set(settings.get('fps', 20.0))
                    self.scale.set(float(settings.get('scale', 1.0)))
                    self.smooth_kernel.set(settings.get('smooth_kernel', 21))
                    self.smooth_sigma.set(settings.get('smooth_sigma', 10.0))
                    self.input_device.set(settings.get('input_device', ''))
                    self.output_device.set(settings.get('output_device', '/dev/video2'))
                    self.background_path.set(settings.get('background_path', ''))
                    self.show_preview.set(settings.get('show_preview', True))
                    self.resolution.set(settings.get('resolution', '1280x720'))
                    self.language.set(settings.get('language', 'en'))
                    self.theme.set(settings.get('theme', 'system'))
                    
                    # Position settings
                    self.x_offset.set(float(settings.get('x_offset', 0.5)))
                    self.y_offset.set(float(settings.get('y_offset', 0.5)))
                    self.flip_h.set(settings.get('flip_h', False))
                    self.flip_v.set(settings.get('flip_v', False))
                    
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save current settings to config file"""
        try:
            settings = {
                'input_device': self.settings_frame.input_device.get(),
                'output_device': self.settings_frame.output_device.get(),
                'background_path': self.settings_frame.background_path.get(),
                'fps': self.settings_frame.fps.get(),
                'scale': self.settings_frame.scale.get(),
                'show_preview': self.show_preview.get(),
                'smooth_kernel': self.settings_frame.smooth_kernel.get(),
                'smooth_sigma': self.settings_frame.smooth_sigma.get(),
                'resolution': self.settings_frame.resolution.get(),
                'x_offset': self.settings_frame.x_offset.get(),
                'y_offset': self.settings_frame.y_offset.get(),
                'flip_h': self.settings_frame.flip_h.get(),
                'flip_v': self.settings_frame.flip_v.get(),
                'language': self.language.get(),
                'theme': self.theme.get()
            }
            
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
                
        except Exception as e:
            print(f"Error saving settings: {e}")

    def export_settings(self):
        """Export settings to a user-specified file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                settings = {
                    'input_device': self.settings_frame.input_device.get(),
                    'output_device': self.settings_frame.output_device.get(),
                    'background_path': self.settings_frame.background_path.get(),
                    'fps': self.settings_frame.fps.get(),
                    'scale': self.settings_frame.scale.get(),
                    'show_preview': self.preview_frame.show_preview.get(),
                    'smooth_kernel': self.settings_frame.smooth_kernel.get(),
                    'smooth_sigma': self.settings_frame.smooth_sigma.get(),
                    'resolution': self.settings_frame.resolution.get(),
                    'x_offset': self.settings_frame.x_offset.get(),
                    'y_offset': self.settings_frame.y_offset.get(),
                    'flip_h': self.settings_frame.flip_h.get(),
                    'flip_v': self.settings_frame.flip_v.get(),
                    # Add theme and language settings
                    'language': self.language.get(),
                    'theme': self.theme.get()
                }
                with open(filename, 'w') as f:
                    json.dump(settings, f, indent=4)
                messagebox.showinfo("Success", "Settings exported successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export settings: {e}")

    def import_settings(self):
        """Import settings from a user-specified file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    settings = json.load(f)
                
                # Update all settings
                self.settings_frame.input_device.set(settings.get('input_device', ''))
                self.settings_frame.output_device.set(settings.get('output_device', '/dev/video2'))
                self.settings_frame.background_path.set(settings.get('background_path', ''))
                self.settings_frame.fps.set(settings.get('fps', 20.0))
                self.settings_frame.scale.set(settings.get('scale', 1.0))
                self.preview_frame.show_preview.set(settings.get('show_preview', True))
                self.settings_frame.smooth_kernel.set(settings.get('smooth_kernel', 21))
                self.settings_frame.smooth_sigma.set(settings.get('smooth_sigma', 10.0))
                self.settings_frame.resolution.set(settings.get('resolution', '1280x720'))
                self.language.set(settings.get('language', 'en'))
                self.theme.set(settings.get('theme', 'light'))
                self.settings_frame.x_offset.set(settings.get('x_offset', 0.5))
                self.settings_frame.y_offset.set(settings.get('y_offset', 0.5))
                self.settings_frame.flip_h.set(settings.get('flip_h', False))
                self.settings_frame.flip_v.set(settings.get('flip_v', False))
                
                # Apply imported settings
                self.apply_loaded_settings()
                messagebox.showinfo("Success", "Settings imported successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import settings: {e}")

    def apply_loaded_settings(self):
        """Apply loaded settings to GUI elements"""
        # Update language
        self.change_language()
        
        # Update theme
        self.theme_manager.set_theme(self.theme.get())
        
        # Update frames
        if hasattr(self, 'settings_frame'):
            self.settings_frame.update_values()
        if hasattr(self, 'preview_frame'):
            self.preview_frame.update_values()

    def process_camera(self):
        # Initialize MediaPipe with fixed landscape model
        mp_selfie_segmentation = mp.solutions.selfie_segmentation
        selfie_segmentation = mp_selfie_segmentation.SelfieSegmentation(model_selection=1)

        try:
            # Extract device number from path
            input_device = re.search(r"\((/dev/video\d+)\)", self.input_device.get()).group(1)
            output_device = re.search(r"\((/dev/video\d+)\)", self.output_device.get()).group(1)
            device_num = int(input_device.replace('/dev/video', ''))

            # Open camera
            cap = cv2.VideoCapture(device_num, cv2.CAP_V4L2)
            if not cap.isOpened():
                messagebox.showerror("Error", f"Could not open camera {input_device}")
                self.is_running = False
                return

            # Set initial resolution
            width, height = map(int, self.resolution_combo.get().split('x'))
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Get actual camera resolution
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if actual_width != width or actual_height != height:
                print(f"Warning: Camera using {actual_width}x{actual_height} instead of requested {width}x{height}")
                width, height = actual_width, actual_height

            # Load and store original background image
            original_background = cv2.imread(self.background_path.get())
            if original_background is None:
                messagebox.showerror("Error", "Could not load background image")
                self.is_running = False
                return
            
            # Get initial background size
            background_image = cv2.resize(original_background, (width, height))
            last_scale = self.scale.get()

            # Initialize FFmpeg process
            ffmpeg_process = None
            def create_ffmpeg_process(w, h):
                command = [
                    'ffmpeg',
                    '-f', 'rawvideo',
                    '-pix_fmt', 'bgr24',
                    '-s', f'{w}x{h}',
                    '-r', str(self.fps.get()),
                    '-i', '-',
                    '-f', 'v4l2',
                    output_device
                ]
                return subprocess.Popen(command, stdin=subprocess.PIPE)

            ffmpeg_process = create_ffmpeg_process(width, height)
            self.frame_queue = queue.Queue(maxsize=2)

            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                # Ensure frame matches target dimensions
                frame = cv2.resize(frame, (width, height))
                
                # Check if scale changed
                if last_scale != self.scale.get():
                    scaled_width = int(width * self.scale.get())
                    scaled_height = int(height * self.scale.get())
                    # Resize from original background to maintain quality
                    background_image = cv2.resize(original_background, (scaled_width, scaled_height))
                    last_scale = self.scale.get()
                    frame = cv2.resize(frame, (scaled_width, scaled_height))
                    width, height = scaled_width, scaled_height

                    # Restart FFmpeg process with new dimensions
                    if ffmpeg_process:
                        ffmpeg_process.stdin.close()
                        ffmpeg_process.wait()
                    ffmpeg_process = create_ffmpeg_process(width, height)

                # Process frame
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = selfie_segmentation.process(frame_rgb)

                try:
                    # Create and smooth mask
                    kernel_size = int(self.smooth_kernel.get())
                    if kernel_size % 2 == 0:
                        kernel_size += 1
                    kernel_tuple = (kernel_size, kernel_size)
                    
                    mask = results.segmentation_mask
                    mask = cv2.GaussianBlur(
                        mask,
                        kernel_tuple,
                        sigmaX=float(self.smooth_sigma.get()),
                        sigmaY=float(self.smooth_sigma.get())
                    )
                    mask = np.stack((mask,) * 3, axis=-1)

                    # Combine foreground and background
                    output_frame = (frame * mask + background_image * (1 - mask)).astype(np.uint8)

                    # Update preview if enabled
                    if self.show_preview.get():
                        try:
                            self.frame_queue.put_nowait(output_frame)
                        except queue.Full:
                            pass

                    # Write to FFmpeg
                    ffmpeg_process.stdin.write(output_frame.tobytes())

                except Exception as e:
                    print(f"Error processing frame: {e}")
                    continue

            # Cleanup
            cap.release()
            ffmpeg_process.stdin.close()
            ffmpeg_process.wait()
            selfie_segmentation.close()

        except Exception as e:
            messagebox.showerror("Error", f"Camera error: {str(e)}")
            self.is_running = False
            return

    def create_variables(self):
        """Initialize all variables"""
        # Theme and language
        self.theme = tk.StringVar(value='system')
        self.language = tk.StringVar(value='en')
        
        # Add trace callbacks to save settings when theme or language changes
        self.theme.trace_add('write', lambda *_: self.save_settings())
        self.language.trace_add('write', lambda *_: self.save_settings())
        
        # Settings variables
        self.fps = tk.DoubleVar(value=20.0)
        self.scale = tk.DoubleVar(value=1.0)
        self.smooth_kernel = tk.IntVar(value=21)
        self.smooth_sigma = tk.DoubleVar(value=10.0)
        self.input_device = tk.StringVar()
        self.output_device = tk.StringVar(value='/dev/video2')
        self.background_path = tk.StringVar()
        self.show_preview = tk.BooleanVar(value=True)
        self.resolution = tk.StringVar(value='1280x720')
        
        # Position controls
        self.x_offset = tk.DoubleVar(value=0.5)
        self.y_offset = tk.DoubleVar(value=0.5)
        self.flip_h = tk.BooleanVar(value=False)
        self.flip_v = tk.BooleanVar(value=False)

    def create_bindings(self):
        """Create keyboard shortcuts"""
        self.root.bind('<Control-s>', lambda e: self.save_settings())
        self.root.bind('<Control-i>', lambda e: self.import_settings())
        self.root.bind('<Control-e>', lambda e: self.export_settings())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<space>', lambda e: self.preview_frame.toggle_camera())
        self.root.bind('<r>', lambda e: self.reset_settings())
        self.root.bind('<Escape>', lambda e: self.preview_frame.stop_camera())