# CLAUDE.md — VidMask AI Assistant Guide

## Project Overview

**VidMask** is a privacy-focused Linux desktop application that provides real-time background replacement for video calls. It creates a virtual camera device (`/dev/video2` by default) and outputs the composited video stream using FFmpeg.

- **Language:** Python 3.11
- **GUI framework:** Tkinter / ttk
- **CV/ML stack:** OpenCV, MediaPipe (SelfieSegmentation), NumPy, Pillow
- **Virtual camera:** v4l2loopback kernel module + FFmpeg
- **Distribution:** AppImage (self-contained, x86_64 Linux)
- **Current version:** `src/version.py` → `VERSION = "0.2.26"`
- **Config path:** `~/.config/vidmask/config.json` (migrated from `~/.config/vcam-bg/`)

---

## Repository Layout

```
vidmask/
├── src/
│   ├── main.py              # Entry point — creates Tk root, starts MainWindow
│   ├── version.py           # Single source of truth for version string
│   ├── config.py            # Config class (JSON load/save, ~/.config/vidmask/)
│   ├── locales.py           # All UI strings; TRANSLATIONS dict + LANGUAGE_NAMES
│   ├── core/
│   │   ├── camera.py        # Camera: v4l2 device discovery, capture, resolution/FPS
│   │   └── processor.py     # Processor: MediaPipe segmentation + Gaussian mask blending
│   ├── gui/
│   │   ├── main_window.py   # MainWindow(ttk.Frame): top-level layout, menus, settings I/O
│   │   ├── settings_frame.py# SettingsFrame(ttk.LabelFrame): all controls on the left panel
│   │   └── preview_frame.py # PreviewFrame(ttk.LabelFrame): camera loop thread + preview
│   └── utils/
│       └── theme.py         # ThemeManager: light/dark/system/gtk theme detection & apply
├── build/
│   ├── create-appimage.sh   # Full AppImage build (compiles Python 3.11, bundles deps)
│   └── install-deps.sh      # System-level build dependency installer
├── install/
│   ├── arch.sh              # Arch Linux installer
│   ├── debian.sh            # Debian/Ubuntu installer (downloads AppImage from releases)
│   └── fedora.sh            # Fedora installer
├── scripts/
│   ├── bump_version.py      # Bumps src/version.py: major | minor | patch
│   ├── release.py           # Release helper
│   └── create_release.sh    # Shell wrapper for releases
├── .github/workflows/
│   └── release.yml          # CI: builds AppImage on tag push, creates GitHub Release
├── setup.sh                 # Distro-detection wrapper → runs install/*.sh + modprobe
├── .cursorrules.example     # Project conventions for Cursor IDE
├── CONTRIBUTING.md
├── SECURITY.md
├── KNOWN_ISSUES.md
└── README.md
```

---

## Architecture

### Data Flow

```
Physical camera (/dev/videoN, MJPG)
        │
        ▼
  cv2.VideoCapture
        │  raw BGR frames
        ▼
  MediaPipe SelfieSegmentation (model_selection=1 — landscape)
        │  segmentation_mask (float32, 0–1)
        ▼
  GaussianBlur (kernel odd, sigma configurable)
        │  smoothed alpha mask
        ▼
  Composite: frame * mask + background * (1 - mask)
        │  output_frame (uint8 BGR)
        ├──► FFmpeg stdin (rawvideo → v4l2loopback /dev/videoM)
        └──► frame_queue → Tkinter preview label (via root.after())
```

### Threading Model

- **Main thread:** Tkinter event loop (all GUI updates must happen here).
- **Camera thread:** `PreviewFrame.camera_loop()` runs in a daemon thread started by `toggle_camera()`. It reads frames, runs segmentation, writes to FFmpeg, and puts frames into `self.frame_queue` (maxsize=2, drops on full).
- **Preview updates:** `PreviewFrame.update_preview()` polls `frame_queue` and reschedules itself via `root.after(delay_ms)` at FPS-appropriate intervals. All Tkinter widget updates occur here (main thread).
- **Theme monitor:** `ThemeManager.check_system_theme()` polls every 5 s via `root.after(5000, ...)` when theme is set to `"system"`.

---

## Key Conventions

### Python Style

- **snake_case** for all files, functions, and variables.
- No external test framework is set up; manual testing is the current practice.
- All source lives under `src/` and is imported as the `src` package.
- Type hints used in `core/` modules; GUI code uses bare Tkinter variables.

### Version Management

The single source of truth is `src/version.py`:
```python
VERSION = "0.2.26"
```

To bump the version:
```bash
python scripts/bump_version.py patch   # 0.2.26 → 0.2.27
python scripts/bump_version.py minor   # 0.2.26 → 0.3.0
python scripts/bump_version.py major   # 0.2.26 → 1.0.0
```

Never edit `src/version.py` manually; always use `bump_version.py`.

### Settings / Config

Settings are persisted to `~/.config/vidmask/config.json` as a flat JSON object. The `MainWindow.save_settings()` / `load_settings()` methods handle serialization. Settings also auto-save on variable trace (scale, flip, language, theme).

Key setting keys (used in JSON and throughout the codebase):
`input_device`, `output_device`, `background_path`, `fps`, `scale`, `show_preview`, `smooth_kernel`, `smooth_sigma`, `resolution`, `x_offset`, `y_offset`, `flip_h`, `flip_v`, `language`, `theme`

Old config at `~/.config/vcam-bg/config.json` is migrated automatically on first run via `MainWindow.migrate_config()`.

### Internationalization

All UI strings are in `src/locales.py`. Structure:

```python
LANGUAGE_NAMES = {'en': 'English', 'cs': 'Čeština', ...}
TRANSLATIONS = {
    'en': {'key': 'value', ...},
    'cs': {'key': 'translated', ...},
    ...
}
```

**Currently supported languages:** English (`en`), Czech (`cs`), German (`de`), Spanish (`es`), Polish (`pl`), Romanian (`ro`), Ukrainian (`uk`).

To add a new translation key: add it to **every** language dict in `TRANSLATIONS`. The `MainWindow.tr(key)` helper looks up the current language.

To add a new language: add its code to `LANGUAGE_NAMES` and a complete dict to `TRANSLATIONS`; the language menu is built dynamically from `sorted(TRANSLATIONS.keys())`.

### Theme System

`ThemeManager` (instantiated in `MainWindow.__init__`) supports four modes:
- `"system"` — auto-detects via `gsettings` (GTK theme name / color-scheme), polls every 5 s
- `"gtk"` — reads GTK theme explicitly via `gsettings`
- `"light"` / `"dark"` — explicit override

Base ttk theme priority: `clam` → `alt` → `default`. Dark colors: bg `#2e2e2e`, fg `#ffffff`. Light colors: bg `#f0f0f0`, fg `#000000`.

### Camera / Device Handling

- **Input devices:** physical webcams discovered via `v4l2-ctl --list-devices`, filtered to exclude `v4l2loopback` devices. Stored as display strings like `"Camera Name (/dev/videoN)"`.
- **Output device:** a `v4l2loopback` virtual camera, default `/dev/video2` with label `"Virtual Camera"`.
- **GSTREAMER** is offered as a fallback input option (uses `cv2.VideoCapture(0)`).
- Kernel module must be loaded before the app starts: `sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="Virtual Camera" exclusive_caps=1`.

### Processing Parameters (defaults)

| Parameter | Default | Range | Notes |
|---|---|---|---|
| FPS | 20.0 | 1–60 | Passed to FFmpeg `-r` |
| Scale | 1.0 | 0.1–2.0 | Scales frame AND background |
| Resolution | 1280x720 | 640x480–1920x1080 | MJPG cap |
| smooth_kernel | 21 | 3–51 (odd) | GaussianBlur kernel; forced odd |
| smooth_sigma | 10.0 | 0.1–20.0 | GaussianBlur sigmaX/Y |
| x_offset | 0.5 | 0–1 | Horizontal person position |
| y_offset | 0.5 | 0–1 | Vertical person position |

**Important:** `smooth_kernel` must always be an odd integer. Both `Processor.set_smoothing()` and the camera loops enforce `kernel += 1 if kernel % 2 == 0`.

---

## Development Workflow

### Running Locally

```bash
# Install system dependencies (first time)
./setup.sh          # or install/<distro>.sh manually

# Load virtual camera module
sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="Virtual Camera" exclusive_caps=1

# Run the app from repo root
python src/main.py
```

Python path note: `src/main.py` appends the project root to `sys.path` so `from src.gui.main_window import MainWindow` resolves correctly.

### Building the AppImage

```bash
cd build
./create-appimage.sh
# Output: vidmask-x86_64.AppImage (in repo root)
```

The build script:
1. Downloads and compiles **Python 3.11.8** with shared library + Tcl/Tk support
2. Installs `opencv-python-headless==4.8.1.78`, `mediapipe==0.10.9`, `numpy==1.24.3`, `pillow==10.2.0` into the AppDir
3. Bundles `v4l2-ctl`, `ffmpeg`, `ffprobe` and their shared library dependencies
4. Copies Tcl/Tk 8.6 libraries and init files
5. Packages with `appimagetool-x86_64.AppImage`

**Note on LD_LIBRARY_PATH:** The AppRun script sets `LD_LIBRARY_PATH` only for the Python process (via `env ...`), not globally, to avoid conflicts with bundled system tools.

### Release Process

1. Bump version: `python scripts/bump_version.py patch`
2. Commit: `git commit -m "Release version X.Y.Z"`
3. Tag: `git tag vX.Y.Z`
4. Push tag: `git push origin vX.Y.Z`
5. GitHub Actions (`.github/workflows/release.yml`) builds the AppImage on `ubuntu-22.04` and publishes a GitHub Release automatically.

CI enforces that the tag version matches `src/version.py` — they must be in sync.

---

## GUI Component Relationships

```
MainWindow (ttk.Frame, packs into Tk root)
├── ThemeManager          — constructed first, before any widgets
├── SettingsFrame         — left panel (fixed width, fills Y)
│   ├── input_combo       — v4l2 webcam selector
│   ├── output_combo      — v4l2loopback selector
│   ├── bg_button/preview — background image picker + thumbnail
│   ├── resolution_combo  — 640x480 / 800x600 / 1280x720 / 1920x1080
│   ├── fps_entry (Scale) — 1–60
│   ├── scale_entry       — 0.1–2.0
│   ├── smooth_frame      — kernel (3–51) + sigma (0.1–20)
│   └── position_frame    — x_offset, y_offset, flip_h, flip_v
└── PreviewFrame          — right panel (expands)
    ├── preview_label     — displays composited frames
    ├── preview_check     — show/hide preview toggle
    └── start_button      — Start Camera / Stop Camera
```

`MainWindow` owns the master `tk.Variable` instances (`self.fps`, `self.scale`, etc.). `SettingsFrame` has its own parallel variables that are synced via `update_values()` / `apply_loaded_settings()`. When saving, `MainWindow.save_settings()` reads from `self.settings_frame.*`.

Keyboard shortcuts (bound in `MainWindow.create_bindings`):
- `Ctrl+S` — save settings
- `Ctrl+I` — import settings
- `Ctrl+E` — export settings
- `Ctrl+Q` — quit
- `Space` — toggle camera
- `r` — reset settings
- `Escape` — stop camera

---

## Critical Files — Do Not Break

| File | Why critical |
|---|---|
| `src/version.py` | Version string used by CI tag validation, About dialog, AppStream metadata |
| `src/locales.py` | Every language must have every key; missing keys silently fall back to the key name |
| `build/create-appimage.sh` | AppImage packaging; very sensitive to Python library path handling (past segfault issues) |
| `.github/workflows/release.yml` | Tag must match `src/version.py` exactly or CI fails |

---

## Known Issues / Gotchas

- **AppImage segfault:** The build script sets `LD_LIBRARY_PATH` narrowly to avoid conflicts between the bundled Python `libpython3.11.so` and system libraries. Do not use `export LD_LIBRARY_PATH` globally in AppRun.
- **Kernel size must be odd:** Any code path that reads `smooth_kernel` must apply `if kernel % 2 == 0: kernel += 1` before passing to `cv2.GaussianBlur`.
- **FFmpeg restart on FPS change:** When `fps` changes during a running session, the camera loop closes the current FFmpeg process and reopens it. This is intentional.
- **Config migration:** `~/.config/vcam-bg/config.json` (old name) is copied to `~/.config/vidmask/config.json` on first run but not deleted (kept as backup).
- **`process_camera` in MainWindow:** `MainWindow.process_camera()` is legacy code and is no longer called — the active implementation is `PreviewFrame.camera_loop()`.
- **No automated tests:** There is currently no test suite. All validation is manual.
