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

# After Python compilation, install packages directly to AppDir

echo "===== Starting post-Python-installation setup ====="

# Use the Python executable from the BUILD directory, not the installed one
# This matches what Python's Makefile does for ensurepip
PYTHON_BUILD_EXEC="$PROJECT_DIR/Python-$PYTHON_VERSION/python"

echo "Python build executable: $PYTHON_BUILD_EXEC"
echo "Checking if Python build executable exists..."
if [ ! -f "$PYTHON_BUILD_EXEC" ]; then
    echo "ERROR: Python build executable not found at $PYTHON_BUILD_EXEC"
    exit 1
fi
echo "Python build executable found!"

# Helper function to run Python from build directory
# Only set LD_LIBRARY_PATH to Python source dir, NOT AppDir/usr/lib
# This prevents library conflicts with system utilities
run_python() {
    LD_LIBRARY_PATH="$PROJECT_DIR/Python-$PYTHON_VERSION" "$PYTHON_BUILD_EXEC" "$@"
}

echo "Python source directory: $PROJECT_DIR/Python-$PYTHON_VERSION"
echo "Testing Python execution from build directory..."
# Test if Python works
if ! run_python --version; then
    echo "ERROR: Python execution failed"
    exit 1
fi
echo "Python execution test passed!"

echo "Verifying Python version..."
# Verify Python version
PYTHON_VERSION_CHECK=$(run_python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "$PYTHON_VERSION_CHECK" != "${PYTHON_VERSION%.*}" ]; then
    echo "Error: Python version ($PYTHON_VERSION_CHECK) doesn't match expected version (${PYTHON_VERSION%.*})"
    exit 1
fi
echo "Python version check passed: $PYTHON_VERSION_CHECK"

# Create site-packages directory if it doesn't exist
echo "Creating site-packages directory..."
mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/python${PYTHON_VERSION%.*}/site-packages"

# Upgrade pip first
echo "Upgrading pip..."
run_python -m pip install --upgrade pip
echo "Pip upgrade complete!"

# Install dependencies directly to AppDir (avoiding venv segfault)
echo "Installing dependencies to AppDir..."
run_python -m pip install --target="$SCRIPT_DIR/AppDir/usr/lib/python${PYTHON_VERSION%.*}/site-packages" \
    opencv-python-headless==4.8.1.78 \
    mediapipe==0.10.9 \
    numpy==1.24.3 \
    pillow==10.2.0
echo "Dependencies installation complete!"

# Create AppDir structure
mkdir -p "$SCRIPT_DIR/AppDir/usr/bin"
mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/python${PYTHON_VERSION%.*}/site-packages"
mkdir -p "$SCRIPT_DIR/AppDir/usr/share/applications"
mkdir -p "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/256x256/apps"

# First, create a separate directory for Python's shared library to avoid conflicts
mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/python-libs"
cp -a "$SCRIPT_DIR/AppDir/usr/lib/libpython"*.so* "$SCRIPT_DIR/AppDir/usr/lib/python-libs/" || true

# Create Python wrapper that sets library path only for Python
cat > "$SCRIPT_DIR/AppDir/usr/bin/python-wrapper" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
# Set LD_LIBRARY_PATH to Python libs directory only for this Python execution
# This avoids conflicts with other libraries in usr/lib
exec env LD_LIBRARY_PATH="$HERE/../lib/python-libs:$LD_LIBRARY_PATH" \
    PYTHONHOME="$HERE/.." \
    "$HERE/python3.11" "$@"
EOF

chmod +x "$SCRIPT_DIR/AppDir/usr/bin/python-wrapper"

# Create AppRun script - use absolute path to Python with controlled LD_LIBRARY_PATH
cat > "$SCRIPT_DIR/AppDir/AppRun" << 'EOF'
#!/bin/bash

SELF=$(readlink -f "$0")
HERE=${SELF%/*}

# Set environment variables (but NOT LD_LIBRARY_PATH globally)
export PATH="$HERE/usr/bin:$PATH"
export PYTHONHOME="$HERE/usr"
export PYTHONPATH="$HERE/usr/lib/python3.11/site-packages:$PYTHONPATH"

# Execute Python directly with LD_LIBRARY_PATH set only for this command
# This prevents library pollution while allowing Python to find libpython3.11.so
exec env LD_LIBRARY_PATH="$HERE/usr/lib/python-libs:$LD_LIBRARY_PATH" \
    "$HERE/usr/bin/python3.11" "$HERE/usr/lib/python3.11/site-packages/src/main.py" "$@"
EOF

chmod +x "$SCRIPT_DIR/AppDir/AppRun"

# Generate icons in multiple sizes using magick instead of convert
for size in 16 32 48 64 128 256 512; do
    mkdir -p "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/${size}x${size}/apps"
    magick "$PROJECT_DIR/app.png" -resize ${size}x${size} \
        "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/${size}x${size}/apps/vidmask.png"
done

# Copy largest icon to AppDir root for AppImage builder
cp "$SCRIPT_DIR/AppDir/usr/share/icons/hicolor/512x512/apps/vidmask.png" "$SCRIPT_DIR/AppDir/vidmask.png"

# Packages are already installed directly to AppDir, so no need to copy from venv

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
    # Create all necessary target directories
    mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/tcl8.6"
    mkdir -p "$SCRIPT_DIR/AppDir/usr/share/tcltk/tcl8.6"
    mkdir -p "$SCRIPT_DIR/AppDir/usr/lib/tk8.6"
    mkdir -p "$SCRIPT_DIR/AppDir/usr/share/tcltk/tk8.6"
    
    # First copy the libraries as before
    local lib_paths=(
        "/usr/lib"                     # Arch Linux
        "/usr/lib/x86_64-linux-gnu"    # Ubuntu/Debian
        "/usr/lib64"                   # Fedora/CentOS
    )
    
    # Add Tcl initialization paths
    local tcl_paths=(
        "/usr/share/tcltk/tcl8.6"     # Common location
        "/usr/lib/tcl8.6"             # Alternative location
        "/usr/share/tcl8.6"           # Another possible location
    )
    
    # Copy Tcl initialization files to both locations
    local tcl_files_copied=0
    for tcl_path in "${tcl_paths[@]}"; do
        if [ -d "$tcl_path" ]; then
            echo "Copying Tcl files from: $tcl_path"
            cp -r "$tcl_path"/* "$SCRIPT_DIR/AppDir/usr/share/tcltk/tcl8.6/" || true
            cp -r "$tcl_path"/* "$SCRIPT_DIR/AppDir/usr/lib/tcl8.6/" || true
            tcl_files_copied=1
        fi
    done

    # Copy Tk files if they exist
    local tk_paths=(
        "/usr/share/tcltk/tk8.6"
        "/usr/lib/tk8.6"
        "/usr/share/tk8.6"
    )
    
    for tk_path in "${tk_paths[@]}"; do
        if [ -d "$tk_path" ]; then
            echo "Copying Tk files from: $tk_path"
            cp -r "$tk_path"/* "$SCRIPT_DIR/AppDir/usr/share/tcltk/tk8.6/" || true
            cp -r "$tk_path"/* "$SCRIPT_DIR/AppDir/usr/lib/tk8.6/" || true
        fi
    done

    local found=0
    for lib_path in "${lib_paths[@]}"; do
        echo "Checking for Tcl/Tk libraries in $lib_path"
        if [ -f "$lib_path/libtk.so" ] || [ -f "$lib_path/libtcl.so" ]; then
            echo "Found Tcl/Tk libraries in $lib_path"
            # Copy all Tcl/Tk related libraries
            cp -L "$lib_path"/libtk* "$SCRIPT_DIR/AppDir/usr/lib/" 2>/dev/null || true
            cp -L "$lib_path"/libtcl* "$SCRIPT_DIR/AppDir/usr/lib/" 2>/dev/null || true
            found=1
        fi
    done
    
    # Verify all required files are present
    if [ $found -eq 0 ] || [ $tcl_files_copied -eq 0 ]; then
        echo "Error: Could not find all required Tcl/Tk files"
        echo "Checking for Tcl/Tk files in AppDir:"
        ls -la "$SCRIPT_DIR/AppDir/usr/lib/tcl8.6/"
        ls -la "$SCRIPT_DIR/AppDir/usr/share/tcltk/tcl8.6/"
        ls -la "$SCRIPT_DIR/AppDir/usr/lib/libtcl"* "$SCRIPT_DIR/AppDir/usr/lib/libtk"*
        exit 1
    fi

    # Verify init.tcl exists in both locations
    if [ ! -f "$SCRIPT_DIR/AppDir/usr/share/tcltk/tcl8.6/init.tcl" ] || \
       [ ! -f "$SCRIPT_DIR/AppDir/usr/lib/tcl8.6/init.tcl" ]; then
        echo "Error: init.tcl not found in required locations"
        exit 1
    fi

    echo "Successfully copied all Tcl/Tk files"
}

# Function to find and copy library with its dependencies
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
    
    # Additional critical libraries to copy
    local critical_libs=(
        "libffi.so.7"
        "libffi.so.8"  # Some systems might use version 8
    )

    # Copy critical libraries if they exist
    for lib in "${critical_libs[@]}"; do
        for lib_path in /usr/lib /usr/lib64 /usr/lib/x86_64-linux-gnu; do
            if [ -f "$lib_path/$lib" ]; then
                echo "Copying critical library: $lib_path/$lib"
                cp -L "$lib_path/$lib" "$SCRIPT_DIR/AppDir/usr/lib/"
                break
            fi
        done
    done
    
    # Get list of dependencies and copy them if not already present
    echo "Copying dependencies for $binary_path"
    ldd "$binary_path" | grep "=> /" | awk '{print $3}' | while read lib; do
        # Skip system libraries except for critical ones
        if echo "$lib" | grep -q "^/lib\|^/usr/lib/\(lib\(c\|gcc\|dl\|rt\|pthread\|stdc++\|m\|util\|selinux\|krb5\|gssapi\)\.so\)"; then
            # Check if it's a critical library before skipping
            local base_lib=$(basename "$lib")
            if echo "${critical_libs[@]}" | grep -q "$base_lib"; then
                echo "Including critical library: $lib"
            else
                echo "Skipping system library: $lib"
                continue
            fi
        fi
        
        if [ ! -f "$SCRIPT_DIR/AppDir/usr/lib/$(basename "$lib")" ]; then
            echo "Copying dependency: $lib"
            cp -L "$lib" "$SCRIPT_DIR/AppDir/usr/lib/"
        fi
    done
}

# Function to verify critical dependencies
verify_dependencies() {
    echo "Verifying critical dependencies..."
    local missing_deps=0

    # Check for libffi
    if [ ! -f "$SCRIPT_DIR/AppDir/usr/lib/libffi.so.7" ] && [ ! -f "$SCRIPT_DIR/AppDir/usr/lib/libffi.so.8" ]; then
        echo "Error: libffi.so.7 or libffi.so.8 not found"
        missing_deps=1
    fi

    # Check for Tcl/Tk libraries
    if [ ! -f "$SCRIPT_DIR/AppDir/usr/lib/libtcl.so" ] || [ ! -f "$SCRIPT_DIR/AppDir/usr/lib/libtk.so" ]; then
        echo "Error: Tcl/Tk libraries not found"
        missing_deps=1
    fi

    # Check for init.tcl
    if [ ! -f "$SCRIPT_DIR/AppDir/usr/share/tcltk/tcl8.6/init.tcl" ]; then
        echo "Error: init.tcl not found"
        missing_deps=1
    fi

    if [ $missing_deps -eq 1 ]; then
        echo "Critical dependencies are missing. Aborting."
        exit 1
    fi

    echo "All critical dependencies verified."
}

# Copy binaries and their dependencies
copy_binary_and_deps "$(which v4l2-ctl)" "$SCRIPT_DIR/AppDir/usr/bin"
copy_binary_and_deps "$(which ffmpeg)" "$SCRIPT_DIR/AppDir/usr/bin"
copy_binary_and_deps "$(which ffprobe)" "$SCRIPT_DIR/AppDir/usr/bin"

# Copy Tcl/Tk libraries
copy_tcltk_libs

# Verify all dependencies are present
verify_dependencies

# Create AppImage
export ARCH=x86_64
"$SCRIPT_DIR/appimagetool-x86_64.AppImage" "$SCRIPT_DIR/AppDir" "vidmask-x86_64.AppImage"

echo "AppImage created: vidmask-x86_64.AppImage"