#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AppIndicator3

import struct
import smbus2
import time
import os

# --- I2C Communication Functions ---
# These functions are responsible for talking to the UPS hardware.

def read_voltage(bus):
    """Reads the battery voltage from the I2C bus."""
    try:
        address = 0x41
        read = bus.read_word_data(address, 2)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        voltage = swapped * 1.25 / 1000 / 16
        return voltage
    except Exception as e:
        print(f"Error reading voltage: {e}")
        return None

def read_capacity(bus):
    """Reads the battery capacity from the I2C bus."""
    try:
        address = 0x41
        read = bus.read_word_data(address, 4)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        capacity = swapped / 256
        return min(100.0, capacity)
    except Exception as e:
        print(f"Error reading capacity: {e}")
        return None

# --- AppIndicator Application ---

class BatteryTrayApp:
    def __init__(self):
        # Initialize the smbus for I2C communication.
        try:
            self.bus = smbus2.SMBus(1)
        except FileNotFoundError:
            self.bus = None

        # Create the AppIndicator instance.
        self.indicator = AppIndicator3.Indicator.new(
            "kali-ups-indicator",
            "battery-missing-symbolic",
            AppIndicator3.IndicatorCategory.HARDWARE
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # AppIndicators require a menu.
        self.indicator.set_menu(self._create_menu())

        # Start the update loop.
        self.update_status()
        GLib.timeout_add_seconds(30, self.update_status)

    def _create_menu(self):
        """Creates a simple GTK menu with a 'Quit' item."""
        menu = Gtk.Menu()
        # This item will show the detailed status on hover.
        self.status_menu_item = Gtk.MenuItem(label="Status: Initializing...")
        self.status_menu_item.set_sensitive(False) # Make it not clickable
        menu.append(self.status_menu_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def get_icon_name(self, capacity, voltage):
        """Determines which icon to show based on the battery level."""
        is_charging = voltage > 4.2

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
            self.indicator.set_icon_full("dialog-error-symbolic", "Error")
            self.indicator.set_label("ERR", "")
            self.status_menu_item.set_label("Error: I2C bus not found.")
            return True

        voltage = read_voltage(self.bus)
        capacity = read_capacity(self.bus)

        if voltage is None or capacity is None:
            self.indicator.set_icon_full("dialog-error-symbolic", "Error")
            self.indicator.set_label("ERR", "")
            self.status_menu_item.set_label("Error: Failed to read from UPS.")
        else:
            icon_name = self.get_icon_name(capacity, voltage)
            label = f"{int(capacity)} %"
            self.indicator.set_icon_full(icon_name, "Battery Status")
            self.indicator.set_label(label, "")
            self.status_menu_item.set_label(f"Voltage: {voltage:.2f}V")

        return True # Keep the timer running

    def _quit(self, source):
        """Quit the application."""
        Gtk.main_quit()

if __name__ == "__main__":
    app = BatteryTrayApp()
    Gtk.main()
