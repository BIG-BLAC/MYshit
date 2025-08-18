#!/usr/bin/env python3
#This python script is only suitable for UPS Shield X1200, X1201 and X1202

import struct
import smbus2
import time
import subprocess
import os

# To get the USERNAME for the notify-send command
for name in os.listdir('/home'):
    if os.path.isdir(os.path.join('/home', name)):
        USERNAME = name
        break
else:
    USERNAME = "root"

def read_voltage(bus):
    """Reads the battery voltage from the I2C bus."""
    address = 0x36
    try:
        read = bus.read_word_data(address, 2)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        voltage = swapped * 1.25 / 1000 / 16
        return voltage
    except Exception as e:
        print(f"Error reading voltage: {e}")
        return None

def read_capacity(bus):
    """Reads the battery capacity from the I2C bus."""
    address = 0x36
    try:
        read = bus.read_word_data(address, 4)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        capacity = swapped / 256
        return capacity
    except Exception as e:
        print(f"Error reading capacity: {e}")
        return None

def send_notification(title, message, urgency="normal"):
    """Sends a desktop notification."""
    try:
        subprocess.run(['sudo', '-u', USERNAME, 'DISPLAY=:0', 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus', 'notify-send', '-u', urgency, title, message])
    except Exception as e:
        print(f"Error sending notification: {e}")

def main():
    """Main function to monitor battery and send notifications."""
    try:
        bus = smbus2.SMBus(1)
    except Exception as e:
        print(f"Error initializing I2C bus: {e}")
        send_notification("Battery Monitor Error", "Could not initialize I2C bus. Is the UPS connected and I2C enabled?")
        return

    send_notification("Battery Monitor", "Starting battery monitoring service.")

    last_notified_level = -1

    while True:
        voltage = read_voltage(bus)
        capacity = read_capacity(bus)

        if voltage is None or capacity is None:
            send_notification("Battery Monitor Error", "Failed to read from UPS.", urgency="critical")
            time.sleep(60)
            continue

        # We only notify if the capacity has changed to avoid spamming notifications
        if int(capacity) != last_notified_level:
            send_notification("Battery Status", f"Battery: {int(capacity)}%", urgency="low")
            last_notified_level = int(capacity)

        if capacity == 100:
            send_notification("Battery Status", "Battery FULL", urgency="low")
        elif capacity < 20:
            send_notification("Battery Warning", f"Battery Low: {int(capacity)}%", urgency="normal")

        # Set battery low voltage to shut down
        if voltage < 3.20:
            send_notification("Battery CRITICAL", "Battery voltage is critically low! Shutdown in 5 seconds.", urgency="critical")
            time.sleep(5)
            # Uncomment the following line to enable automatic shutdown
            # subprocess.run(["sudo", "nohup", "shutdown", "-h", "now"])

        time.sleep(30)

if __name__ == "__main__":
    main()
