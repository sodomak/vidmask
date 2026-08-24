#!/bin/bash

# Exit on error
set -e

# Parse arguments
MAKE_PERSISTENT=0
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--persistent)
            MAKE_PERSISTENT=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-p|--persistent]"
            echo "  -p, --persistent    Make v4l2loopback module load persistent across reboots"
            exit 1
            ;;
    esac
done

echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y v4l2loopback-dkms libfuse2

echo "Loading v4l2loopback module..."
sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1

if [ $MAKE_PERSISTENT -eq 1 ]; then
    echo "Making module load persistent..."
    echo "v4l2loopback" | sudo tee /etc/modules-load.d/v4l2loopback.conf
    echo 'options v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1' | sudo tee /etc/modprobe.d/v4l2loopback.conf
fi

# Download latest release
echo "Downloading latest release..."
LATEST_URL=$(curl -s https://api.github.com/repos/sodomak/vidmask/releases/latest | grep "browser_download_url.*AppImage" | cut -d '"' -f 4)
if [ -z "$LATEST_URL" ]; then
    echo "Error: Could not find latest release URL"
    exit 1
fi

wget -O vidmask-x86_64.AppImage "$LATEST_URL"
chmod +x vidmask-x86_64.AppImage

echo "Installation complete!"
echo "To run the application:"
echo "  ./vidmask-x86_64.AppImage"
