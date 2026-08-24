import tkinter as tk
from tkinter import ttk, filedialog
import subprocess
import re
import os
import cv2
from PIL import Image, ImageTk

class SettingsFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text=master.tr('settings'))
        
        # Initialize variables
        self.input_device = tk.StringVar()
        self.output_device = tk.StringVar()
        self.background_path = tk.StringVar()
        self.resolution = tk.StringVar(value='1280x720')
        self.fps = tk.DoubleVar(value=20.0)
        self.scale = tk.DoubleVar(value=1.0)
        self.smooth_kernel = tk.IntVar(value=21)
        self.smooth_sigma = tk.DoubleVar(value=10.0)
        
        # Position control variables
        self.x_offset = tk.DoubleVar(value=0.5)
        self.y_offset = tk.DoubleVar(value=0.5)
        self.flip_h = tk.BooleanVar(value=False)
        self.flip_v = tk.BooleanVar(value=False)
        
        # Bind variable changes to save settings
        self.scale.trace_add('write', lambda *_: self.master.save_settings())
        self.x_offset.trace_add('write', lambda *_: self.master.save_settings())
        self.y_offset.trace_add('write', lambda *_: self.master.save_settings())
        self.flip_h.trace_add('write', lambda *_: self.master.save_settings())
        self.flip_v.trace_add('write', lambda *_: self.master.save_settings())
        
        # Create widgets after initializing variables
        self.create_widgets()

    def create_widgets(self):
        """Create all widgets in the settings frame"""
        # Input device
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        self.input_label = ttk.Label(input_frame, text=self.master.tr('input_device'))
        self.input_label.pack(side=tk.LEFT)
        self.input_combo = ttk.Combobox(input_frame, textvariable=self.input_device, state='readonly')
        self.input_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Output device
        output_frame = ttk.Frame(self)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        self.output_label = ttk.Label(output_frame, text=self.master.tr('output_device'))
        self.output_label.pack(side=tk.LEFT)
        self.output_combo = ttk.Combobox(output_frame, textvariable=self.output_device, state='readonly')
        self.output_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Background
        bg_frame = ttk.Frame(self)
        bg_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Label on the left
        self.bg_label = ttk.Label(bg_frame, text=self.master.tr('background'))
        self.bg_label.pack(side=tk.LEFT)
        
        # Preview frame between label and button
        self.bg_preview_frame = ttk.Frame(bg_frame)
        self.bg_preview_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Preview image and filename
        self.bg_preview = ttk.Label(self.bg_preview_frame)
        self.bg_preview.pack(side=tk.LEFT, padx=(5, 0))
        
        self.bg_path_label = ttk.Label(self.bg_preview_frame, text="", wraplength=150)
        self.bg_path_label.pack(side=tk.LEFT, padx=5)
        
        # Button on the right
        self.bg_button = ttk.Button(
            bg_frame,
            text=self.master.tr('select_background'),
            command=self.select_background
        )
        self.bg_button.pack(side=tk.RIGHT)

        # Resolution
        resolution_frame = ttk.Frame(self)
        resolution_frame.pack(fill=tk.X, pady=(0, 10))
        self.resolution_label = ttk.Label(resolution_frame, text=self.master.tr('resolution'))
        self.resolution_label.pack(side=tk.LEFT)
        self.resolution_combo = ttk.Combobox(
            resolution_frame,
            textvariable=self.resolution,
            values=['640x480', '800x600', '1280x720', '1920x1080'],
            state='readonly'
        )
        self.resolution_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # FPS slider
        self.fps_frame = ttk.Frame(self)
        self.fps_frame.pack(fill=tk.X, pady=(0, 10))
        self.fps_text_label = ttk.Label(self.fps_frame, text=self.master.tr('fps'))
        self.fps_text_label.pack(side=tk.LEFT)
        self.fps_label = ttk.Label(self.fps_frame, text=f"{self.fps.get():.1f}")
        self.fps_label.pack(side=tk.RIGHT)
        self.fps_entry = ttk.Scale(
            self,
            from_=1,
            to=60,
            orient=tk.HORIZONTAL,
            variable=self.fps,
            command=lambda v: self.fps_label.config(text=f"{float(v):.1f}")
        )
        self.fps_entry.pack(fill=tk.X)

        # Scale slider
        self.scale_frame = ttk.Frame(self)
        self.scale_frame.pack(fill=tk.X, pady=(0, 10))
        self.scale_text_label = ttk.Label(self.scale_frame, text=self.master.tr('scale'))
        self.scale_text_label.pack(side=tk.LEFT)
        self.scale_label = ttk.Label(self.scale_frame, text=f"{self.scale.get():.2f}")
        self.scale_label.pack(side=tk.RIGHT)
        self.scale_entry = ttk.Scale(
            self,
            from_=0.1,
            to=2.0,
            orient=tk.HORIZONTAL,
            variable=self.scale,
            command=lambda v: self.scale_label.config(text=f"{float(v):.2f}")
        )
        self.scale_entry.pack(fill=tk.X)

        # Smoothing frame
        self.smooth_frame = ttk.LabelFrame(self, text=self.master.tr('smoothing'))
        self.smooth_frame.pack(fill=tk.X, pady=(0, 10))

        # Kernel slider
        self.kernel_frame = ttk.Frame(self.smooth_frame)
        self.kernel_frame.pack(fill=tk.X, pady=(5, 5))
        self.kernel_text_label = ttk.Label(self.kernel_frame, text=self.master.tr('kernel'))
        self.kernel_text_label.pack(side=tk.LEFT)
        self.kernel_label = ttk.Label(self.kernel_frame, text=str(self.smooth_kernel.get()))
        self.kernel_label.pack(side=tk.RIGHT)
        self.kernel_entry = ttk.Scale(
            self.smooth_frame,
            from_=3,
            to=51,
            orient=tk.HORIZONTAL,
            variable=self.smooth_kernel,
            command=lambda v: self.kernel_label.config(text=str(int(float(v))))
        )
        self.kernel_entry.pack(fill=tk.X)

        # Sigma slider
        self.sigma_frame = ttk.Frame(self.smooth_frame)
        self.sigma_frame.pack(fill=tk.X, pady=(5, 5))
        self.sigma_text_label = ttk.Label(self.sigma_frame, text=self.master.tr('sigma'))
        self.sigma_text_label.pack(side=tk.LEFT)
        self.sigma_label = ttk.Label(self.sigma_frame, text=f"{self.smooth_sigma.get():.1f}")
        self.sigma_label.pack(side=tk.RIGHT)
        self.sigma_entry = ttk.Scale(
            self.smooth_frame,
            from_=0.1,
            to=20.0,
            orient=tk.HORIZONTAL,
            variable=self.smooth_sigma,
            command=lambda v: self.sigma_label.config(text=f"{float(v):.1f}")
        )
        self.sigma_entry.pack(fill=tk.X)

        # Position controls
        self.position_frame = ttk.LabelFrame(self, text=self.master.tr('position'))
        self.position_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Horizontal position slider
        self.h_pos_frame = ttk.Frame(self.position_frame)
        self.h_pos_frame.pack(fill=tk.X, pady=(5, 5))
        ttk.Label(self.h_pos_frame, text=self.master.tr('horizontal')).pack(side=tk.LEFT)
        ttk.Scale(
            self.position_frame,
            from_=0, to=1,
            variable=self.x_offset,
            orient=tk.HORIZONTAL
        ).pack(fill=tk.X, padx=5)
        
        # Vertical position slider
        self.v_pos_frame = ttk.Frame(self.position_frame)
        self.v_pos_frame.pack(fill=tk.X, pady=(5, 5))
        ttk.Label(self.v_pos_frame, text=self.master.tr('vertical')).pack(side=tk.LEFT)
        ttk.Scale(
            self.position_frame,
            from_=0, to=1,
            variable=self.y_offset,
            orient=tk.HORIZONTAL
        ).pack(fill=tk.X, padx=5)
        
        # Flip controls
        flip_frame = ttk.Frame(self.position_frame)
        flip_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(
            flip_frame,
            text=self.master.tr('flip_h'),
            variable=self.flip_h
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(
            flip_frame,
            text=self.master.tr('flip_v'),
            variable=self.flip_v
        ).pack(side=tk.LEFT, padx=5)
        
        # Reset button at the bottom
        reset_frame = ttk.Frame(self.position_frame)
        reset_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(
            reset_frame,
            text=self.master.tr('reset_position'),
            command=self.reset_position
        ).pack(side=tk.RIGHT)

    def select_background(self):
        """Open file dialog to select background image"""
        filename = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.background_path.set(filename)
            self.update_background_preview(filename)

    def update_background_preview(self, path):
        """Update background preview with the selected image"""
        try:
            # Load and resize image for preview
            image = Image.open(path)
            image.thumbnail((100, 100))  # Resize for preview
            photo = ImageTk.PhotoImage(image)
            
            # Update preview image
            self.bg_preview.configure(image=photo)
            self.bg_preview.image = photo  # Keep reference
            
            # Update path label
            filename = os.path.basename(path)
            self.bg_path_label.configure(text=filename)
            
        except Exception as e:
            print(f"Error updating background preview: {e}")
            # Clear preview if there's an error
            self.bg_preview.configure(image='')
            self.bg_path_label.configure(text='')

    def load_camera_devices(self):
        """Load available input and output devices"""
        try:
            # Input devices (webcams)
            input_devices = []
            for i in range(20):  # Check first 20 video devices
                device = f"/dev/video{i}"
                if os.path.exists(device):
                    # Check if it's a capture device
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        name = self.get_device_name(device)
                        input_devices.append(f"{name} ({device})")
                    cap.release()

            # Output devices (v4l2loopback)
            output_devices = []
            for i in range(20):  # Check first 20 video devices
                device = f"/dev/video{i}"
                if os.path.exists(device):
                    # Check if it's a v4l2loopback device
                    try:
                        result = subprocess.run(
                            ['v4l2-ctl', '--device', device, '--all'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        # Case-insensitive check for v4l2loopback
                        if 'v4l2loopback' in result.stdout.lower():
                            name = self.get_device_name(device)
                            output_devices.append(f"{name} ({device})")
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        continue

            # Update comboboxes
            self.input_combo['values'] = input_devices
            self.output_combo['values'] = output_devices

            # Set defaults if no selection
            if not self.input_device.get() and input_devices:
                self.input_device.set(input_devices[0])
            if not self.output_device.get() and output_devices:
                self.output_device.set(output_devices[0])

        except Exception as e:
            print(f"Error loading camera devices: {e}")

    def get_device_name(self, device_path):
        """Get friendly name of a video device"""
        try:
            result = subprocess.run(
                ['v4l2-ctl', '--device', device_path, '--all'],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'Card type' in line:
                    return line.split(':')[1].strip()
        except:
            pass
        return os.path.basename(device_path)

    def get_camera_resolutions(self, device_path):
        """Get supported resolutions for a camera using v4l2-ctl"""
        try:
            # Get formats and resolutions using v4l2-ctl
            cmd = ["v4l2-ctl", "--device", device_path, "--list-formats-ext"]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
            
            resolutions = set()  # Use set to avoid duplicates
            
            # Parse the output to extract resolutions
            for line in output.split('\n'):
                # Look for size entries
                size_match = re.search(r'Size:\s*(\d+)x(\d+)', line)
                if size_match:
                    width, height = size_match.groups()
                    resolutions.add(f"{width}x{height}")
                    
            # Sort resolutions by total pixels (descending)
            return sorted(
                list(resolutions),
                key=lambda x: int(x.split('x')[0]) * int(x.split('x')[1]),
                reverse=True
            )
        except Exception as e:
            print(f"Error getting camera resolutions: {e}")
            return self.common_resolutions

    def update_resolutions(self, event=None):
        """Update available resolutions for selected camera"""
        try:
            # Get device path from selected input
            device_path = re.search(r"\((/dev/video\d+)\)", self.input_device.get()).group(1)
            
            # Get supported resolutions
            available_resolutions = self.get_camera_resolutions(device_path)
            
            if not available_resolutions:
                available_resolutions = self.common_resolutions
                
            # Update combobox
            self.resolution_combo['values'] = available_resolutions
            
            # Try to keep current resolution if available
            current = self.resolution.get()
            if current in available_resolutions:
                self.resolution.set(current)
            else:
                # Default to highest resolution
                self.resolution.set(available_resolutions[0])
                    
        except Exception as e:
            print(f"Error updating resolutions: {e}")
            # Fallback to common resolutions
            self.resolution_combo['values'] = self.common_resolutions
            if not self.resolution.get() in self.common_resolutions:
                self.resolution.set(self.common_resolutions[0])

    def update_kernel_value(self, value):
        """Ensure kernel size is always odd and update label"""
        kernel_size = int(float(value))
        if kernel_size % 2 == 0:
            kernel_size += 1
        self.smooth_kernel.set(kernel_size)
        self.kernel_label.configure(text=str(kernel_size))

    def disable_runtime_controls(self):
        """Disable controls that can't be changed while camera is running"""
        for control in self.runtime_controls:
            control.configure(state='disabled')

    def enable_runtime_controls(self):
        """Enable controls after camera is stopped"""
        for control in self.runtime_controls:
            control.configure(state='readonly' if isinstance(control, ttk.Combobox) else 'normal')

    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.input_device.set('')
        self.output_device.set('/dev/video2')
        self.background_path.set('')
        self.fps.set(20.0)
        self.scale.set(1.0)
        self.resolution.set('1280x720')
        self.smooth_kernel.set(21)
        self.smooth_sigma.set(10.0)
        
        # Update labels
        self.fps_label.configure(text="20.0")
        self.scale_label.configure(text="1.0")
        self.kernel_label.configure(text="21")
        self.sigma_label.configure(text="10.0")
        
        # Reload camera devices
        self.load_camera_devices()

    def update_labels(self):
        """Update all labels when language changes"""
        self.configure(text=self.master.tr('settings'))
        self.input_label.configure(text=self.master.tr('input_device'))
        self.output_label.configure(text=self.master.tr('output_device'))
        self.bg_label.configure(text=self.master.tr('background'))
        self.bg_button.configure(text=self.master.tr('select_background'))
        self.resolution_label.configure(text=self.master.tr('resolution'))
        self.fps_text_label.configure(text=self.master.tr('fps'))
        self.scale_text_label.configure(text=self.master.tr('scale'))
        self.smooth_frame.configure(text=self.master.tr('smoothing'))
        self.kernel_text_label.configure(text=self.master.tr('kernel'))
        self.sigma_text_label.configure(text=self.master.tr('sigma'))
        
        # Position controls with correct frame names from create_widgets
        self.position_frame.configure(text=self.master.tr('position'))
        # Find labels in position control frames
        for child in self.h_pos_frame.winfo_children():
            if isinstance(child, ttk.Label):
                child.configure(text=self.master.tr('horizontal'))
        for child in self.v_pos_frame.winfo_children():
            if isinstance(child, ttk.Label):
                child.configure(text=self.master.tr('vertical'))
            
        # Update checkbuttons in position frame
        for child in self.position_frame.winfo_children():
            if isinstance(child, ttk.Checkbutton):
                if 'flip_h' in str(child):
                    child.configure(text=self.master.tr('flip_h'))
                elif 'flip_v' in str(child):
                    child.configure(text=self.master.tr('flip_v'))
        
        # Update reset button
        for child in self.position_frame.winfo_children():
            if isinstance(child, ttk.Button):
                child.configure(text=self.master.tr('reset_position'))

    def update_values(self):
        """Update all widgets with current values"""
        # Update input/output devices
        self.input_device.set(self.master.input_device.get())
        self.output_device.set(self.master.output_device.get())
        self.background_path.set(self.master.background_path.get())
        
        # Update resolution
        current_res = self.master.resolution.get()
        if current_res in self.resolution_combo['values']:
            self.resolution.set(current_res)
        else:
            self.resolution.set('1280x720')  # Default if saved resolution is not in list
        
        # Update background preview if path exists
        if self.background_path.get():
            self.update_background_preview(self.background_path.get())
        
        # Update sliders
        self.fps.set(float(self.master.fps.get()))
        self.scale.set(float(self.master.scale.get()))
        self.smooth_kernel.set(int(self.master.smooth_kernel.get()))
        self.smooth_sigma.set(float(self.master.smooth_sigma.get()))
        self.resolution.set(self.master.resolution.get())
        
        # Update position controls
        self.x_offset.set(float(self.master.x_offset.get()))
        self.y_offset.set(float(self.master.y_offset.get()))
        self.flip_h.set(self.master.flip_h.get())
        self.flip_v.set(self.master.flip_v.get())
        
        # Update labels
        self.fps_label.config(text=f"{self.fps.get():.1f}")
        self.scale_label.config(text=f"{self.scale.get():.2f}")
        self.kernel_label.config(text=str(int(self.smooth_kernel.get())))
        self.sigma_label.config(text=f"{self.smooth_sigma.get():.1f}")

    def get_output_devices(self):
        """Get list of available output devices, prioritizing v4l2loopback devices"""
        devices = []
        try:
            for i in range(10):  # Check first 10 video devices
                device_path = f"/dev/video{i}"
                if not os.path.exists(device_path):
                    continue
                    
                # Check if it's a v4l2loopback device
                try:
                    cmd = ["v4l2-ctl", "--device", device_path, "--all"]
                    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
                    if "v4l2loopback" in output.lower() or "VidMask Cam" in output or "Virtual Camera" in output:
                        name = self.get_device_name(device_path)
                        devices.append(f"{name} ({device_path})")
                    else:
                        # Skip non-v4l2loopback devices
                        continue
                except subprocess.CalledProcessError:
                    continue
                    
        except Exception as e:
            print(f"Error getting output devices: {e}")
        
        return devices

    def get_input_devices(self):
        """Get list of available input devices (webcams)"""
        devices = []
        try:
            for i in range(10):  # Check first 10 video devices
                device_path = f"/dev/video{i}"
                if not os.path.exists(device_path):
                    continue
                    
                # Check if it's a capture device
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        # Try to get device name
                        cmd = ["v4l2-ctl", "--device", device_path, "--all"]
                        try:
                            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
                            name = re.search(r"Card\s*?:\s*(.*)", output)
                            if name:
                                devices.append(f"{name.group(1)} ({device_path})")
                            else:
                                devices.append(f"Camera {i} ({device_path})")
                        except:
                            devices.append(f"Camera {i} ({device_path})")
                    cap.release()
                except:
                    continue
                    
        except Exception as e:
            print(f"Error getting input devices: {e}")
        
        return devices

    def reset_position(self):
        """Reset position controls to default values"""
        self.x_offset.set(0.5)  # Center horizontally
        self.y_offset.set(0.5)  # Center vertically
        self.flip_h.set(False)  # No horizontal flip
        self.flip_v.set(False)  # No vertical flip
