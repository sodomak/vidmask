#!/bin/bash

# Exit on error
set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Download AppImage builder first (move this section up, before any AppDir operations)
if [ ! -f "$SCRIPT_DIR/appimagetool-x86_64.AppImage" ]; then
    wget -O "$SCRIPT_DIR/appimagetool-x86_64.AppImage" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$SCRIPT_DIR/appimagetool-x86_64.AppImage"
fi

# Download and compile Python 3.11
PYTHON_VERSION="3.11.8"
if [ ! -d "$SCRIPT_DIR/Python-$PYTHON_VERSION" ]; then
    wget "https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz"
    tar xzf "Python-$PYTHON_VERSION.tgz"
    cd "Python-$PYTHON_VERSION"
    ./configure --prefix="$SCRIPT_DIR/AppDir/usr" --enable-shared --with-system-ffi \
        --enable-optimizations \
        --with-ensurepip=install \
        --with-system-expat \
        --enable-loadable-sqlite-extensions \
        --with-tcltk-includes=/usr/include/tcl \
        --with-tcltk-libs=/usr/lib/x86_64-linux-gnu
    make -j$(nproc)
    make install
    cd ..
    rm -f "Python-$PYTHON_VERSION.tgz"
fi

# Use the compiled Python
PYTHON_EXEC="$SCRIPT_DIR/AppDir/usr/bin/python3"
export LD_LIBRARY_PATH="$SCRIPT_DIR/AppDir/usr/lib:$LD_LIBRARY_PATH"

# Create and activate virtual environment using the compiled Python
rm -rf "$SCRIPT_DIR/venv"  # Clean up any existing venv
"$PYTHON_EXEC" -m venv --clear "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"

# Verify we're using the correct Python version in the virtual environment
VENV_PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "$VENV_PYTHON_VERSION" != "${PYTHON_VERSION%.*}" ]; then
    echo "Error: Virtual environment Python version ($VENV_PYTHON_VERSION) doesn't match expected version ($PYTHON_VERSION)"
    deactivate
    rm -rf "$SCRIPT_DIR/venv"
    exit 1
fi

# Upgrade pip first
"$SCRIPT_DIR/venv/bin/python" -m pip install --upgrade pip

# Install dependencies in virtual environment with specific versions
"$SCRIPT_DIR/venv/bin/python" -m pip install \
    opencv-python-headless==4.8.1.78 \
    mediapipe==0.10.9 \
    numpy==1.24.3 \
    pillow==10.2.0

# Create AppDir structure
mkdir -p "$SCRIPT_DIR/AppDir/usr/bin"
mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/python${PYTHON_VERSION%.*}/site-packages"
mkdir -p "$SCRIPT_DIR/AppDir/usr/share/applications"
mkdir -p "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/256x256/apps"

# Generate icons in multiple sizes using magick instead of convert
for size in 16 32 48 64 128 256 512; do
    mkdir -p "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/${size}x${size}/apps"
    magick "$PROJECT_DIR/app.png" -resize ${size}x${size} \
        "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/${size}x${size}/apps/vidmask.png"
done

# Copy largest icon to AppDir root for AppImage builder
cp "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/512x512/apps/vidmask.png" "$SCRIPT_DIR/AppDir/vidmask.png"

# Copy virtual environment packages to AppDir
cp -r "$SCRIPT_DIR/venv/lib/python${PYTHON_VERSION%.*}/site-packages"/* "$SCRIPT_DIR/AppDir/usr/lib/python${PYTHON_VERSION%.*}/site-packages/"

# Copy application files
cp -r "$PROJECT_DIR/src" "$SCRIPT_DIR/AppDir/usr/lib/python${PYTHON_VERSION%.*}/site-packages/"

# Create launcher script
cat > "$SCRIPT_DIR/AppDir/usr/bin/vidmask" << EOF
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PYTHONPATH="$HERE/../lib/python$PYTHON_VERSION/site-packages:$PYTHONPATH"
exec python3 "$HERE/../lib/python$PYTHON_VERSION/site-packages/src/main.py" "$@"
EOF

chmod +x "$SCRIPT_DIR/AppDir/usr/bin/vidmask"

# Get version from version.py
VERSION=$(grep -oP 'VERSION = "\K[^"]+' "${SCRIPT_DIR}/../src/version.py")

# Create desktop entry with correct categories and icon path
cat > "$SCRIPT_DIR/AppDir/vidmask.desktop" << EOF
[Desktop Entry]
Type=Application
Name=VidMask
GenericName=VidMask
Comment=Privacy-focused virtual camera with background replacement
Exec=vidmask
Icon=vidmask
Terminal=false
Categories=AudioVideo;Video;
Keywords=camera;background;virtual;video;conference;meeting;blur;privacy;
StartupNotify=true
StartupWMClass=VidMask
X-AppImage-Version=${VERSION}
X-AppImage-BuildDate=$(date -u +%Y-%m-%d)
X-AppImage-Arch=x86_64
X-AppImage-Name=VidMask
X-AppImage-Description=Privacy-focused virtual camera with background replacement
X-AppImage-URL=https://github.com/sodomak/vidmask
X-AppImage-License=MIT
X-AppImage-Author=sodomak
EOF

# Copy desktop file to applications directory
cp "$SCRIPT_DIR/AppDir/vidmask.desktop" "$SCRIPT_DIR/AppDir/usr/share/applications/"

# Remove all old metadata files
rm -f "$SCRIPT_DIR/AppDir/usr/share/metainfo/vcam-bg.appdata.xml"
rm -f "$SCRIPT_DIR/AppDir/usr/share/metainfo/io.github.sodomak.vcam-bg.appdata.xml"

# Create AppStream metadata with fixes
mkdir -p "$SCRIPT_DIR/AppDir/usr/share/metainfo"
cat > "$SCRIPT_DIR/AppDir/usr/share/metainfo/io.github.sodomak.vidmask.metainfo.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>io.github.sodomak.vidmask</id>
  <metadata_license>MIT</metadata_license>
  <project_license>MIT</project_license>
  <name>VidMask</name>
  <summary>Privacy-focused virtual camera with background replacement</summary>
  <description>
    <p>
      A privacy-focused Linux application that enables custom backgrounds in any video call.
      Compatible with Signal Desktop, Zoom, Teams, Meet, and all other video chat software.
    </p>
    <p>Features:</p>
    <ul>
      <li>Real-time background replacement using MediaPipe</li>
      <li>Multiple camera support with MJPG format</li>
      <li>Adjustable FPS and resolution scaling</li>
      <li>Edge smoothing with Gaussian blur</li>
      <li>Light/Dark theme</li>
      <li>Multi-language support (English, Čeština)</li>
    </ul>
  </description>
  <launchable type="desktop-id">vidmask.desktop</launchable>
  <url type="homepage">https://github.com/sodomak/vidmask</url>
  <provides>
    <binary>vidmask</binary>
  </provides>
  <developer id="io.github.sodomak">
    <name>sodomak</name>
    <url>https://github.com/sodomak</url>
  </developer>
  <releases>
    <release version="${VERSION}" date="$(date -I)"/>
  </releases>
  <content_rating type="oars-1.1">
    <content_attribute id="social-info">mild</content_attribute>
  </content_rating>
  <categories>
    <category>AudioVideo</category>
    <category>Video</category>
  </categories>
</component>
EOF

# Function to find and copy Tcl/Tk libraries based on system
copy_tcltk_libs() {
    local lib_paths=(
        "/usr/lib"                     # Arch Linux
        "/usr/lib/x86_64-linux-gnu"    # Ubuntu/Debian
        "/usr/lib64"                   # Fedora/CentOS
    )
    
    local found=0
    for lib_path in "${lib_paths[@]}"; do
        echo "Checking for Tcl/Tk libraries in $lib_path"
        if [ -f "$lib_path/libtk.so" ] || [ -f "$lib_path/libtcl.so" ]; then
            echo "Found Tcl/Tk libraries in $lib_path"
            # Copy all Tcl/Tk related libraries
            cp -L "$lib_path"/libtk* "$SCRIPT_DIR/AppDir/usr/lib/" 2>/dev/null || true
            cp -L "$lib_path"/libtcl* "$SCRIPT_DIR/AppDir/usr/lib/" 2>/dev/null || true
            
            # Check and copy tcl directories one by one
            for d in "$lib_path"/tcl*; do
                if [ -d "$d" ]; then
                    echo "Copying Tcl directory: $d"
                    cp -r "$d" "$SCRIPT_DIR/AppDir/usr/lib/"
                fi
            done
            
            # Check and copy tk directories one by one
            for d in "$lib_path"/tk*; do
                if [ -d "$d" ]; then
                    echo "Copying Tk directory: $d"
                    cp -r "$d" "$SCRIPT_DIR/AppDir/usr/lib/"
                fi
            done
            
            # Verify the libraries were copied
            if [ -f "$SCRIPT_DIR/AppDir/usr/lib/libtk.so" ] && [ -f "$SCRIPT_DIR/AppDir/usr/lib/libtcl.so" ]; then
                echo "Successfully copied Tcl/Tk libraries"
                found=1
                break
            else
                echo "Warning: Tcl/Tk libraries were not properly copied"
            fi
        fi
    done
    
    if [ $found -eq 0 ]; then
        echo "Error: Could not find Tcl/Tk libraries"
        echo "Available libraries in /usr/lib:"
        ls -la /usr/lib/libtk* /usr/lib/libtcl* 2>/dev/null || true
        echo "Available libraries in /usr/lib/x86_64-linux-gnu:"
        ls -la /usr/lib/x86_64-linux-gnu/libtk* /usr/lib/x86_64-linux-gnu/libtcl* 2>/dev/null || true
        exit 1
    fi
}

# Copy binaries and their dependencies
copy_binary_and_deps() {
    local binary="$1"
    local target_dir="$2"
    
    # Find the binary using 'which'
    local binary_path=$(which "$binary" 2>/dev/null)
    if [ -z "$binary_path" ]; then
        echo "Warning: $binary not found, skipping..."
        return
    fi
    
    echo "Copying binary: $binary_path"
    # Copy the binary itself
    cp -L "$binary_path" "$target_dir/"
    
    # Get list of dependencies and copy them if not already present
    echo "Copying dependencies for $binary_path"
    ldd "$binary_path" | grep "=> /" | awk '{print $3}' | while read lib; do
        if [ ! -f "$SCRIPT_DIR/AppDir/usr/lib/$(basename "$lib")" ]; then
            echo "Copying dependency: $lib"
            cp -L "$lib" "$SCRIPT_DIR/AppDir/usr/lib/"
        fi
    done
}

# Copy binaries and their dependencies
copy_binary_and_deps "$(which v4l2-ctl)" "$SCRIPT_DIR/AppDir/usr/bin"
copy_binary_and_deps "$(which ffmpeg)" "$SCRIPT_DIR/AppDir/usr/bin"
copy_binary_and_deps "$(which ffprobe)" "$SCRIPT_DIR/AppDir/usr/bin"

# Create AppImage
export ARCH=x86_64
"$SCRIPT_DIR/appimagetool-x86_64.AppImage" "$SCRIPT_DIR/AppDir" "vidmask-x86_64.AppImage"

echo "AppImage created: vidmask-x86_64.AppImage"

# Deactivate virtual environment
deactivate

# Clean up
rm -rf "$SCRIPT_DIR/venv"

# Create AppRun script with debug output and error checking
cat > "$SCRIPT_DIR/AppDir/AppRun" << 'EOF'
#!/bin/bash

# Exit on error
set -e

# Get the directory containing this script
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

# Set environment variables
export PATH="$HERE/usr/bin:$PATH"
export PYTHONPATH="$HERE/usr/lib/python3.11/site-packages:$PYTHONPATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
export PYTHONHOME="$HERE/usr"
export TCL_LIBRARY="$HERE/usr/lib/tcl8.6"
export TK_LIBRARY="$HERE/usr/lib/tk8.6"

# Debug output if VERBOSE is set
if [ "${VERBOSE:-0}" = "1" ]; then
    echo "AppRun location: $SELF"
    echo "App directory: $HERE"
    echo "Environment:"
    env | grep -E '^(PYTHON|LD_LIBRARY|PATH|TCL|TK)'
    echo "Directory contents:"
    ls -la "$HERE/usr/bin"
    ls -la "$HERE/usr/lib/python3.11"
fi

# Execute the application
exec "$HERE/usr/bin/python3" "$HERE/usr/lib/python3.11/site-packages/src/main.py" "$@"
EOF

chmod +x "$SCRIPT_DIR/AppDir/AppRun"

# Copy additional required libraries
mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/tcl8.6"
mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/tk8.6"
cp -r /usr/lib/tcl8.6/* "$SCRIPT_DIR/AppDir/usr/lib/tcl8.6/"
cp -r /usr/lib/tk8.6/* "$SCRIPT_DIR/AppDir/usr/lib/tk8.6/"