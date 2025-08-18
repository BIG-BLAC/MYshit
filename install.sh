#!/bin/bash

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo."
  exit
fi

echo "Starting installation of Battery Notifier..."

# Install dependencies
echo "Installing dependencies (python3-smbus2, libnotify-bin)..."
apt-get update
apt-get install -y python3-smbus2 libnotify-bin

# Check if files exist before proceeding
if [ ! -f "battery_notifier.py" ] || [ ! -f "battery-notifier.service" ]; then
    echo "Error: Required files 'battery_notifier.py' or 'battery-notifier.service' not found in the current directory."
    exit 1
fi

# Copy the script and service file
echo "Copying files to system directories..."
install -m 755 battery_notifier.py /usr/local/bin/battery_notifier.py
install -m 644 battery-notifier.service /etc/systemd/system/battery-notifier.service

# Reload systemd, enable and start the service
echo "Reloading systemd and starting the service..."
systemctl daemon-reload
systemctl enable battery-notifier.service
systemctl start battery-notifier.service

echo "Installation complete. The battery notifier service has been started and will run on boot."
echo "You should see a notification soon."
echo "To check the status of the service, run: systemctl status battery-notifier.service"
