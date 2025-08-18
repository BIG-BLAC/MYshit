#!/bin/bash

# --- Battery Tray Icon Installer ---
# This script configures the system and installs the tray icon application.

# 1. Check if running with sudo
if [ "$EUID" -ne 0 ] || [ -z "$SUDO_USER" ]; then
  echo "Error: Please run this script with sudo."
  echo "Usage: sudo ./install.sh"
  exit 1
fi

# Get the real user's home directory
REAL_USER=$SUDO_USER
HOME_DIR=$(getent passwd "$REAL_USER" | cut -d: -f6)

if [ -z "$HOME_DIR" ]; then
    echo "Error: Could not find home directory for user '$REAL_USER'."
    exit 1
fi

AUTOSTART_DIR="$HOME_DIR/.config/autostart"
NEEDS_REBOOT=false

echo "--- Battery Tray Installer for user: $REAL_USER ---"

# 2. Clean up the old systemd service version
echo ">>> Step 1: Removing old battery_notifier service (if it exists)..."
systemctl stop battery-notifier.service >/dev/null 2>&1
systemctl disable battery-notifier.service >/dev/null 2>&1
rm -f /etc/systemd/system/battery-notifier.service
rm -f /usr/local/bin/battery_notifier.py
systemctl daemon-reload
echo "Cleanup complete."

# 3. Enable I2C interface on Raspberry Pi
CONFIG_FILE="/boot/firmware/config.txt"
if [ -f "$CONFIG_FILE" ] && ! grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
  echo ">>> Step 2: Enabling I2C interface in $CONFIG_FILE..."
  # Add a newline just in case the file doesn't end with one
  echo "" >> "$CONFIG_FILE"
  echo "# --- Added by Battery Tray Installer ---" >> "$CONFIG_FILE"
  echo "dtparam=i2c_arm=on" >> "$CONFIG_FILE"
  NEEDS_REBOOT=true
  echo "I2C has been enabled."
else
  echo ">>> Step 2: I2C interface already enabled. Skipping."
fi

# 4. Add the user to the 'i2c' group for hardware access
if ! groups "$REAL_USER" | grep -q "\bi2c\b"; then
  echo ">>> Step 3: Adding user '$REAL_USER' to the 'i2c' group for permissions..."
  usermod -aG i2c "$REAL_USER"
  NEEDS_REBOOT=true
  echo "User added to i2c group."
else
  echo ">>> Step 3: User '$REAL_USER' is already in the 'i2c' group. Skipping."
fi

# 5. Install required packages
echo ">>> Step 4: Installing required system packages..."
apt-get update > /dev/null
apt-get install -y python3-gi gir1.2-gtk-3.0 python3-smbus2 python3-pil python3-pip
echo "System packages installed."

echo ">>> Step 5: Force-reinstalling Python libraries for a clean slate..."
pip3 install --upgrade pip
pip3 uninstall -y adafruit-blinka adafruit-circuitpython-ina219 adafruit-pureio adafruit-circuitpython-busdevice adafruit-circuitpython-register
pip3 install --force-reinstall adafruit-blinka adafruit-circuitpython-ina219
echo "Python libraries reinstalled."

# 6. Install the application files
echo ">>> Step 6: Installing application files..."

# Check if files exist
if [ ! -f "battery_tray.py" ] || [ ! -f "battery-tray.desktop" ]; then
    echo "Error: 'battery_tray.py' or 'battery-tray.desktop' not found in this directory."
    exit 1
fi

# Install script to a binary path
install -m 755 battery_tray.py /usr/local/bin/battery_tray.py

# Create autostart directory and install the desktop file
mkdir -p "$AUTOSTART_DIR"
install -m 644 battery-tray.desktop "$AUTOSTART_DIR/battery-tray.desktop"

# Set correct ownership for the user's config directory
chown -R "$REAL_USER:$REAL_USER" "$HOME_DIR/.config"

echo "Application installed successfully."

# 7. Final instructions
echo
echo "--- Installation Finished ---"

if [ "$NEEDS_REBOOT" = true ]; then
  echo -e "\033[1;31mIMPORTANT: A REBOOT IS REQUIRED.\033[0m"
  echo "The I2C interface has been enabled and/or your user was added to the 'i2c' group."
  echo "These changes only take effect after a reboot."
  echo
  echo -e "Please run '\033[1msudo reboot\033[0m' now."
else
  echo "You can now log out and log back in to see the battery icon."
  echo "Alternatively, you can start it manually for the current session by running:"
  echo "battery_tray.py &"
fi
echo "---------------------------"
