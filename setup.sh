#!/bin/bash

# Detect distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo "Cannot detect Linux distribution"
    exit 1
fi

# Run appropriate install script
case $OS in
    "Arch Linux")
        ./install/arch.sh
        ;;
    "Ubuntu"|"Debian GNU/Linux")
        ./install/debian.sh
        ;;
    "Fedora Linux")
        ./install/fedora.sh
        ;;
    *)
        echo "Unsupported distribution: $OS"
        echo "Please install dependencies manually"
        exit 1
        ;;
esac

# Setup v4l2loopback
sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1

# Make v4l2loopback persistent (double-quote card_label so spaces survive kernel param parsing)
echo "v4l2loopback" | sudo tee /etc/modules-load.d/v4l2loopback.conf
echo 'options v4l2loopback devices=1 video_nr=2 card_label="VidMask Cam" exclusive_caps=1' | sudo tee /etc/modprobe.d/v4l2loopback.conf

# Add user to video group
sudo usermod -a -G video $USER

echo "Setup complete! Please log out and back in for group changes to take effect."
