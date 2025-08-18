#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from PIL import Image, ImageDraw, ImageFont
import os
import sys
import atexit

# This is the key to making the application self-contained.
# It adds the local 'lib' directory to the Python path.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

from INA219 import INA219

# --- Constants ---
ICON_WIDTH = 96
ICON_HEIGHT = 32
CACHE_DIR = os.path.expanduser("~/.cache/pi-battery-indicator")
os.makedirs(CACHE_DIR, exist_ok=True)
ICON_PATH = os.path.join(CACHE_DIR, "battery-icon.png")

# --- Icon Generation ---
def find_font():
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/droid/DroidSans.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, 22)
    return ImageFont.load_default()

FONT = find_font()

def generate_icon(capacity, voltage, current):
    img = Image.new('RGBA', (ICON_WIDTH, ICON_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    WHITE = (255, 255, 255, 220)

    # Logic based on user feedback: negative current means charging
    is_charging = current is not None and current < -10  # Use a -10mA threshold

    # Battery Outline
    batt_x, batt_y, batt_w, batt_h = 2, 5, 28, 22
    draw.rectangle((batt_x, batt_y, batt_x + batt_w, batt_y + batt_h), outline=WHITE, width=2)
    draw.rectangle((batt_x + batt_w + 1, batt_y + 6, batt_x + batt_w + 4, batt_y + batt_h - 6), fill=WHITE)

    # Battery Fill
    if capacity is not None:
        fill_w = int((batt_w - 4) * (capacity / 100.0))
        fill_color = (255, 50, 50) if capacity <= 15 else (255, 165, 0) if capacity <= 40 else (50, 205, 50)
        if fill_w > 0:
            draw.rectangle((batt_x + 3, batt_y + 3, batt_x + 1 + fill_w, batt_y + batt_h - 3), fill=fill_color)

    # Charging Symbol
    if is_charging:
        bolt = [(batt_x + 15, batt_y + 4), (batt_x + 10, batt_y + 13), (batt_x + 14, batt_y + 13),
                (batt_x + 9, batt_y + 20), (batt_x + 13, batt_y + 11), (batt_x + 17, batt_y + 11)]
        draw.polygon(bolt, fill=(255, 255, 0))

    # Text (with more space)
    text = f"{int(capacity)}%" if capacity is not None else "ERR"
    draw.text((batt_x + batt_w + 12, 4), text, font=FONT, fill=WHITE)

    img.save(ICON_PATH, 'PNG')

# --- GTK Application ---
class BatteryTrayApp:
    def __init__(self):
        self.sensor = None
        try:
            # Initialize with the correct I2C address
            self.sensor = INA219(addr=0x41)
        except Exception as e:
            print(f"Error initializing INA219 from local lib: {e}")

        self.status_icon = Gtk.StatusIcon()
        self.status_icon.connect("popup-menu", self._create_menu)
        atexit.register(lambda: os.remove(ICON_PATH) if os.path.exists(ICON_PATH) else None)

        self.update_status()
        GLib.timeout_add_seconds(30, self.update_status)

    def update_status(self):
        if not self.sensor:
            generate_icon(None, None, None)
            self.status_icon.set_from_file(ICON_PATH)
            self.status_icon.set_tooltip_text("Error: INA219 sensor not found.")
            return True

        try:
            voltage = self.sensor.getBusVoltage_V()
            current = self.sensor.getCurrent_mA()

            # Use the exact calculation from the user's demo script
            capacity = (voltage - 9) / 3.6 * 100
            if capacity > 100: capacity = 100
            if capacity < 0: capacity = 0

            generate_icon(capacity, voltage, current)
            self.status_icon.set_from_file(ICON_PATH)

            # Corrected state logic based on user feedback
            state = "Charging" if current is not None and current < -10 else "Discharging"
            tooltip = f"Battery: {int(capacity)}% ({state})\nVoltage: {voltage:.2f}V\nCurrent: {current:.0f}mA"
            self.status_icon.set_tooltip_text(tooltip)
        except Exception as e:
            print(f"Error reading from sensor: {e}")
            generate_icon(None, None, None)
            self.status_icon.set_from_file(ICON_PATH)
            self.status_icon.set_tooltip_text("Error: Could not read from sensor.")

        return True

    def _create_menu(self, icon, button, time):
        menu = Gtk.Menu()
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        menu.append(quit_item)
        menu.show_all()
        menu.popup(None, None, None, None, button, time)

if __name__ == "__main__":
    app = BatteryTrayApp()
    Gtk.main()
