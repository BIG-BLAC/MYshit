#!/bin/bash

# --- Battery Tray Icon Installer (Final, Self-Contained Version) ---

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

APP_DIR="/opt/pi-battery-indicator"
AUTOSTART_DIR="$HOME_DIR/.config/autostart"
NEEDS_REBOOT=false

echo "--- Battery Tray Installer for user: $REAL_USER ---"

# 2. Clean up old versions (just in case)
echo ">>> Step 1: Removing old versions..."
systemctl stop battery-notifier.service >/dev/null 2>&1
systemctl disable battery-notifier.service >/dev/null 2>&1
rm -f /etc/systemd/system/battery-notifier.service
rm -f /usr/local/bin/battery_notifier.py
rm -f /usr/local/bin/battery_tray.py
rm -rf /opt/pi-battery-indicator
systemctl daemon-reload
echo "Cleanup complete."

# 3. Enable I2C interface on Raspberry Pi
CONFIG_FILE="/boot/firmware/config.txt"
if [ -f "$CONFIG_FILE" ] && ! grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
  echo ">>> Step 2: Enabling I2C interface..."
  echo "" >> "$CONFIG_FILE"
  echo "# Added by pi-battery-indicator installer" >> "$CONFIG_FILE"
  echo "dtparam=i2c_arm=on" >> "$CONFIG_FILE"
  NEEDS_REBOOT=true
else
  echo ">>> Step 2: I2C interface already enabled."
fi

# 4. Add the user to the 'i2c' group for hardware access
if ! groups "$REAL_USER" | grep -q "\bi2c\b"; then
  echo ">>> Step 3: Adding user '$REAL_USER' to the 'i2c' group..."
  usermod -aG i2c "$REAL_USER"
  NEEDS_REBOOT=true
else
  echo ">>> Step 3: User '$REAL_USER' is already in the 'i2c' group."
fi

# 5. Install required system packages (no more pip!)
echo ">>> Step 4: Installing required system packages..."
apt-get update > /dev/null
apt-get install -y python3-smbus python3-pil python3-gi gir1.2-gtk-3.0
echo "System packages installed."

# 6. Install the application files
echo ">>> Step 5: Installing application to $APP_DIR..."
mkdir -p "$APP_DIR"
cp -r lib "$APP_DIR/"
cp battery_tray.py "$APP_DIR/"
chmod +x "$APP_DIR/battery_tray.py"

# Create a symlink so the command can be run from anywhere
ln -sf "$APP_DIR/battery_tray.py" /usr/local/bin/battery_tray

# 7. Install the autostart desktop entry
echo ">>> Step 6: Installing autostart entry..."
mkdir -p "$AUTOSTART_DIR"
# Make sure the .desktop file executes the symlink
sed -i 's|Exec=.*|Exec=/usr/local/bin/battery_tray|' battery-tray.desktop
install -m 644 battery-tray.desktop "$AUTOSTART_DIR/battery-tray.desktop"
chown -R "$REAL_USER:$REAL_USER" "$HOME_DIR/.config"

echo "Application installed successfully."

# 8. Final instructions
echo
echo "--- Installation Finished ---"
if [ "$NEEDS_REBOOT" = true ]; then
  echo -e "\033[1;31mIMPORTANT: A REBOOT IS REQUIRED for I2C changes to take effect.\033[0m"
  echo -e "Please run '\033[1msudo reboot\033[0m' now."
else
  echo "Installation complete. Please LOG OUT and LOG BACK IN for the tray icon to appear."
fi
echo "---------------------------"
