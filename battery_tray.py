#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

import struct
import smbus2
import time
import os

# --- I2C Communication Functions ---
# These functions are responsible for talking to the UPS hardware.

def read_voltage(bus):
    """Reads the battery voltage from the I2C bus."""
    try:
        address = 0x36
        read = bus.read_word_data(address, 2)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        voltage = swapped * 1.25 / 1000 / 16
        return voltage
    except Exception as e:
        # This will catch errors like the device not being found
        print(f"Error reading voltage: {e}")
        return None

def read_capacity(bus):
    """Reads the battery capacity from the I2C bus."""
    try:
        address = 0x36
        read = bus.read_word_data(address, 4)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        capacity = swapped / 256
        return min(100.0, capacity) # Ensure capacity doesn't exceed 100%
    except Exception as e:
        print(f"Error reading capacity: {e}")
        return None

# --- GTK Tray Application ---

class BatteryTrayApp:
    def __init__(self):
        # Initialize the smbus for I2C communication.
        # This is done once to avoid re-opening the bus every time.
        try:
            self.bus = smbus2.SMBus(1)
        except FileNotFoundError:
            # This error is critical and means I2C is likely not enabled
            self.bus = None

        # Create the status icon itself.
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_visible(True)
        self.status_icon.connect("popup-menu", self.on_popup_menu)

        # Start the main update loop.
        # GLib.timeout_add_seconds is the GTK-friendly way to do background tasks.
        # It will call self.update_status every 30 seconds.
        GLib.timeout_add_seconds(30, self.update_status)
        # Call it once immediately to set the initial state
        self.update_status()

    def get_icon_name(self, capacity, voltage):
        """Determines which icon to show based on the battery level."""
        # The icon names follow the standard Freedesktop icon theme specification.
        # This makes them likely to work on any standard Linux desktop.
        # The '-symbolic' suffix is used for modern, monochrome tray icons.

        # A voltage > 4.2 suggests it's charging (or fully charged and plugged in)
        is_charging = voltage > 4.2

        if capacity is None:
            return "dialog-error-symbolic" # Error icon

        if capacity >= 95:
            return "battery-full-charged-symbolic" if is_charging else "battery-full-symbolic"
        elif capacity >= 75:
            return "battery-good-charging-symbolic" if is_charging else "battery-good-symbolic"
        elif capacity >= 40:
            return "battery-medium-charging-symbolic" if is_charging else "battery-medium-symbolic"
        elif capacity >= 15:
            return "battery-low-charging-symbolic" if is_charging else "battery-low-symbolic"
        else:
            return "battery-caution-charging-symbolic" if is_charging else "battery-caution-symbolic"

    def update_status(self):
        """The main update function, called periodically."""
        if self.bus is None:
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            self.status_icon.set_tooltip_text("Battery Monitor Error\nI2C bus not found. Is it enabled in raspi-config?")
            return True # Keep the timer running

        voltage = read_voltage(self.bus)
        capacity = read_capacity(self.bus)

        if voltage is None or capacity is None:
            icon_name = "dialog-error-symbolic"
            tooltip = "Battery Monitor Error\nFailed to read from UPS. Check connection."
        else:
            icon_name = self.get_icon_name(capacity, voltage)
            tooltip = f"Battery: {int(capacity)}%\nVoltage: {voltage:.2f}V"

        self.status_icon.set_from_icon_name(icon_name)
        self.status_icon.set_tooltip_text(tooltip)

        # This 'True' is important! It tells GLib to keep running this timer.
        return True

    def on_popup_menu(self, icon, button, time):
        """Creates a right-click menu with a 'Quit' option."""
        menu = Gtk.Menu()
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        menu.append(quit_item)
        menu.show_all()
        menu.popup(None, None, None, None, button, time)

if __name__ == "__main__":
    app = BatteryTrayApp()
    # This starts the GTK event loop, which waits for user input and runs timers.
    Gtk.main()
