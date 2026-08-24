<div align="center">
  <img src="logo.png" alt="VidMask Logo" width="128" height="128">
  <h1>VidMask</h1>
</div>

A privacy-focused Linux application that enables custom backgrounds in any video call, regardless of native support in the conferencing app. Compatible with Signal Desktop, Zoom, Teams, Meet, and all other video chat software. The app captures your camera feed, applies a background image, and streams the processed video to a virtual camera, which can then be selected as your video source in any conferencing app.

*Note: This application was developed with the assistance of AI LLMs.*

![Application Screenshot](app.png)

## Installation

### AppImage (Recommended)
Download the latest AppImage from the [releases page](https://github.com/sodomak/vidmask/releases):

1. Download `vidmask-x86_64.AppImage`
2. Make it executable:
   ```bash
   chmod +x vidmask-x86_64.AppImage
   ```
3. Install and load the virtual camera module (required):
   ```bash
   # For Ubuntu/Debian:
   sudo apt install v4l2loopback-dkms

   # For Fedora:
   sudo dnf install v4l2loopback

   # For Arch Linux:
   sudo pacman -S v4l2loopback-dkms

   # After installation, load the module:
   sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1

   # Optional: Make module load persistent across reboots
   echo "v4l2loopback" | sudo tee /etc/modules-load.d/v4l2loopback.conf
   echo 'options v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1' | sudo tee /etc/modprobe.d/v4l2loopback.conf
   ```
4. Run it:
   ```bash
   ./vidmask-x86_64.AppImage
   ```

> [!NOTE]
> The AppImage is self-contained and includes all required dependencies (Python, OpenCV, MediaPipe, etc.). The only system requirements are:
> - libfuse2 (required by all AppImages)
> - v4l2loopback kernel module (for virtual camera functionality)

> [!TIP]
> If the module installation commands above don't work for your distribution, check your distribution's package manager for `v4l2loopback` or `v4l2loopback-dkms` package.

## Usage

1. Select your input camera from the dropdown
2. Select virtual camera as output (/dev/video2 by default)
3. Choose a background image
4. Adjust settings as needed:

   - Model: Landscape/Portrait based on your usage
   - FPS: Higher values for smoother video
   - Scale: Adjust output resolution
   - Smoothing: Adjust edge detection sensitivity
     - Transition Width: Controls edge blur width
     - Blend Strength: Controls edge blending intensity
   - Position controls:
     - Horizontal/Vertical positioning
     - Horizontal/Vertical flip
     - Quick reset to center
   - Preview window toggle

5. Click Start to begin
6. Select "VidMask Cam" in your video conferencing software

### Keyboard Shortcuts
- Ctrl+S: Save settings
- Ctrl+I: Import settings
- Ctrl+E: Export settings
- Ctrl+Q: Quit
- Space: Toggle camera
- R: Reset settings
- Esc: Stop camera

### Configuration
Settings are automatically saved to `~/.config/vidmask/config.json`

You can export/import settings through the File menu.

## Features

- Real-time background replacement using MediaPipe segmentation
- Adjustable parameters:
  - FPS control
  - Resolution scaling
  - Gaussian blur smoothing (kernel size and sigma)
  - Preview window toggle
  - Position controls:
    - Horizontal/Vertical positioning
    - Horizontal/Vertical flip
    - Quick reset to center
- Multiple camera support:
  - Input device selection
  - Output device selection (v4l2loopback)
  - MJPG format support
  - Multiple resolution options
- User Interface:
  - Light/Dark theme
  - Multi-language support (English, Čeština)
  - Settings management:
    - Auto-save configuration
    - Import/Export settings
    - Reset to defaults
- Keyboard shortcuts:
  - Ctrl+S: Save settings
  - Ctrl+I: Import settings
  - Ctrl+E: Export settings
  - Ctrl+Q: Quit
  - Space: Toggle camera
  - R: Reset settings
  - Esc: Stop camera

## Prerequisites

### System Requirements

- Linux system with Python 3.8+
- Webcam compatible with V4L2
- Graphics acceleration recommended

### Virtual Camera Setup

1. Load v4l2loopback module:

   ```bash
   sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1
   ```

2. Make it persistent (optional):

   ```bash
   echo "v4l2loopback" | sudo tee /etc/modules-load.d/v4l2loopback.conf
   echo 'options v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1' | sudo tee /etc/modprobe.d/v4l2loopback.conf
   ```

## Building from Source

> For single file version (no translations, slightly different GUI) switch to [single-file](https://github.com/sodomak/vidmask/tree/single-file/src) branch or download [release](https://github.com/sodomak/vidmask/releases/tag/single)

### Dependencies Installation

Choose your distribution and run the appropriate install script:

```bash
# Arch Linux
./install/arch.sh

# Ubuntu/Debian
./install/debian.sh

# Fedora
./install/fedora.sh
```

This will install all required system packages:

- OpenCV (python3-opencv/python-opencv)
- MediaPipe (python3-mediapipe/python-mediapipe)
- NumPy (python3-numpy/python-numpy)
- Pillow (python3-pillow/python-pillow)
- v4l2loopback
- v4l-utils
- ffmpeg
- Tkinter
- OpenGL libraries

### Building AppImage

To build your own AppImage:

```bash
# Clone the repository
git clone https://github.com/sodomak/vidmask.git
cd vidmask

# Run the AppImage build script
./build/create-appimage.sh
```

The AppImage will be created as `vidmask-x86_64.AppImage`.

## Troubleshooting

### Common Issues

1. Virtual camera not showing up:

   ```bash
   # Check if module is loaded
   lsmod | grep v4l2loopback

   # Check available video devices
   v4l2-ctl --list-devices
   ```

2. Permission denied:

   ```bash
   # Add user to video group
   sudo usermod -a -G video $USER
   ```

3. Poor performance:

   - Lower the resolution
   - Reduce FPS
   - Adjust scale factor

## Debug Information

Run with debug output:

```bash
PYTHONPATH=src DEBUG=1 ./vidmask
```

## Contributing

### Adding a New Translation

1. Fork the repository and create a new branch:
   ```bash
   git checkout -b add-LANG-translation
   ```
   Replace `LANG` with your language code (e.g., `add-fr-translation` for French)

2. Edit `src/locales.py`:
   - Add your language to `LANGUAGE_NAMES`:
     ```python
     LANGUAGE_NAMES = {
         'en': 'English',
         'cs': 'Čeština',
         # Add your language:
         'fr': 'Français'
     }
     ```
   - Add translations to `TRANSLATIONS`:
     ```python
     TRANSLATIONS = {
         'en': {
             # existing English translations
         },
         'fr': {  # Add your language
             'title': 'Arrière-plan virtuel de caméra',
             'settings': 'Paramètres',
             # ... translate all strings from English ...
         }
     }
     ```
   
   > [!TIP]
   > - Use the English translations as a reference
   > - Ensure you translate ALL strings
   > - Keep special characters like `{0}`, `{version}` unchanged
   > - Maintain the same formatting in the `about_text`

3. Test your translation:
   ```bash
   # Run the application
   ./vidmask
   # Select your language from View > Language menu
   # Verify all UI elements are correctly translated
   ```

4. Create a Pull Request:
   - Commit your changes:
     ```bash
     git add src/locales.py
     git commit -m "Add [Language] translation"
     git push origin add-LANG-translation
     ```
   - Open a Pull Request on GitHub
   - In the PR description, mention:
     - The language you've added
     - Any special considerations for the translation
     - Your native speaker status for this language

### Translation Guidelines

- Use formal language style
- Keep technical terms consistent
- Maintain similar line lengths where possible
- Test the UI with longer text to ensure it fits
- Include all special characters and diacritics appropriate for your language

For more details on contributing, see [CONTRIBUTING.md](CONTRIBUTING.md)

## License

[MIT](https://choosealicense.com/licenses/mit/)
