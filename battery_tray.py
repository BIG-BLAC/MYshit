#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from PIL import Image, ImageDraw, ImageFont
import struct
import smbus2
import os
import atexit

# --- Constants ---
ICON_WIDTH = 64
ICON_HEIGHT = 24
# Use a path in the user's cache directory for better practice
CACHE_DIR = os.path.expanduser("~/.cache/pi-battery-indicator")
os.makedirs(CACHE_DIR, exist_ok=True)
ICON_PATH = os.path.join(CACHE_DIR, "battery-icon.png")

# --- I2C Communication Functions ---
def read_voltage(bus):
    try:
        address = 0x41
        read = bus.read_word_data(address, 2)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        return swapped * 1.25 / 1000 / 16
    except Exception:
        return None

def read_capacity(bus):
    try:
        address = 0x41
        read = bus.read_word_data(address, 4)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        return min(100.0, swapped / 256)
    except Exception:
        return None

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
            return ImageFont.truetype(path, 14)
    return ImageFont.load_default()

FONT = find_font()

def generate_icon(capacity, voltage):
    img = Image.new('RGBA', (ICON_WIDTH, ICON_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    WHITE = (255, 255, 255, 220)

    is_charging = voltage is not None and voltage > 4.2

    # Battery Outline
    batt_x, batt_y, batt_w, batt_h = 1, 4, 20, 16
    draw.rectangle((batt_x, batt_y, batt_x + batt_w, batt_y + batt_h), outline=WHITE, width=1)
    draw.rectangle((batt_x + batt_w + 1, batt_y + 4, batt_x + batt_w + 3, batt_y + batt_h - 4), fill=WHITE)

    # Battery Fill
    if capacity is not None:
        fill_w = int((batt_w - 2) * (capacity / 100.0))
        fill_color = (255, 50, 50) if capacity <= 15 else (255, 165, 0) if capacity <= 40 else (50, 205, 50)
        if fill_w > 0:
            draw.rectangle((batt_x + 2, batt_y + 2, batt_x + fill_w, batt_y + batt_h - 2), fill=fill_color)

    # Charging Symbol
    if is_charging:
        bolt = [(batt_x + 11, batt_y + 2), (batt_x + 7, batt_y + 9), (batt_x + 10, batt_y + 9),
                (batt_x + 6, batt_y + 14), (batt_x + 10, batt_y + 7), (batt_x + 13, batt_y + 7)]
        draw.polygon(bolt, fill=(255, 255, 0))

    # Text
    text = f"{int(capacity)}%" if capacity is not None else "ERR"
    draw.text((batt_x + batt_w + 8, 4), text, font=FONT, fill=WHITE)

    img.save(ICON_PATH, 'PNG')

# --- GTK Application ---
class BatteryTrayApp:
    def __init__(self):
        try:
            self.bus = smbus2.SMBus(1)
        except FileNotFoundError:
            self.bus = None

        self.status_icon = Gtk.StatusIcon()
        self.status_icon.connect("popup-menu", self._create_menu)
        atexit.register(lambda: os.remove(ICON_PATH) if os.path.exists(ICON_PATH) else None)

        self.update_status()
        GLib.timeout_add_seconds(30, self.update_status)

    def update_status(self):
        voltage = read_voltage(self.bus) if self.bus else None
        capacity = read_capacity(self.bus) if self.bus else None

        generate_icon(capacity, voltage)
        self.status_icon.set_from_file(ICON_PATH)

        if capacity is None:
            tooltip = "Error: Could not read from UPS."
        else:
            state = "Charging" if voltage > 4.2 else "Discharging"
            tooltip = f"Battery: {int(capacity)}% ({state})\nVoltage: {voltage:.2f}V"
        self.status_icon.set_tooltip_text(tooltip)

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
