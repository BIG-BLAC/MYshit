#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from PIL import Image, ImageDraw, ImageFont
import os
import sys
import atexit

# This is the key to making the application self-contained.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))
from INA219 import INA219

# --- Constants ---
# Use a path in the user's cache directory for better practice
CACHE_DIR = os.path.expanduser("~/.cache/pi-battery-indicator")
os.makedirs(CACHE_DIR, exist_ok=True)
ICON_BATT_PATH = os.path.join(CACHE_DIR, "batt-icon.png")
ICON_TEXT_PATH = os.path.join(CACHE_DIR, "text-icon.png")

# --- Battery Logic ---
def voltage_to_percent(voltage):
    MIN_VOLT, MAX_VOLT = 9.0, 12.6
    voltage = max(MIN_VOLT, min(MAX_VOLT, voltage))
    return ((voltage - MIN_VOLT) / (MAX_VOLT - MIN_VOLT)) * 100

# --- Icon Generation ---
def find_font():
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            # Using a smaller font size to prevent cropping
            return ImageFont.truetype(path.replace("Regular", "Bold"), 16)
    return ImageFont.load_default()

FONT = find_font()

def generate_battery_icon(capacity, is_charging):
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0)) # Square icon
    draw = ImageDraw.Draw(img)
    WHITE = (255, 255, 255, 220)

    # Horizontal Battery Outline
    batt_x, batt_y, batt_w, batt_h = 2, 8, 24, 16
    draw.rectangle((batt_x, batt_y, batt_x + batt_w, batt_y + batt_h), outline=WHITE, width=2)
    draw.rectangle((batt_x + batt_w + 1, batt_y + 4, batt_x + batt_w + 3, batt_y + batt_h - 4), fill=WHITE)

    # Horizontal Battery Fill (left to right)
    if capacity is not None:
        fill_w = int((batt_w - 4) * (capacity / 100.0))
        fill_color = (255, 50, 50) if capacity <= 15 else (255, 165, 0) if capacity <= 40 else (50, 205, 50)
        if fill_w > 0:
            draw.rectangle((batt_x + 3, batt_y + 3, batt_x + 3 + fill_w, batt_y + batt_h - 3), fill=fill_color)

    # Charging Symbol
    if is_charging:
        bolt = [(15, 11), (11, 16), (14, 16), (10, 21), (13, 17), (16, 17)]
        draw.polygon(bolt, fill=(50, 255, 50))

    img.save(ICON_BATT_PATH, 'PNG')

def generate_text_icon(capacity):
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0)) # Square icon
    draw = ImageDraw.Draw(img)
    WHITE = (255, 255, 255, 220)

    text = f"{int(capacity)}%" if capacity is not None else "!"

    # Use a compatible method to get text size and center it
    try:
        text_width = draw.textlength(text, font=FONT)
    except AttributeError:  # Fallback for older Pillow versions
        text_width, _ = FONT.getsize(text)

    x = (32 - text_width) / 2
    # Keep vertical alignment simple and compatible
    y = 4

    draw.text((x, y), text, font=FONT, fill=WHITE)

    img.save(ICON_TEXT_PATH, 'PNG')

# --- GTK Application ---
class BatteryTrayApp:
    def __init__(self):
        self.sensor = None
        try:
            self.sensor = INA219(addr=0x41)
        except Exception as e:
            print(f"Error initializing INA219: {e}")

        # Create two separate icons
        self.icon_batt = Gtk.StatusIcon()
        self.icon_text = Gtk.StatusIcon()
        self.icon_batt.connect("popup-menu", self._create_menu)
        self.icon_text.connect("popup-menu", self._create_menu)

        atexit.register(lambda: os.remove(ICON_BATT_PATH) if os.path.exists(ICON_BATT_PATH) else None)
        atexit.register(lambda: os.remove(ICON_TEXT_PATH) if os.path.exists(ICON_TEXT_PATH) else None)

        self.update_status()
        GLib.timeout_add_seconds(30, self.update_status)

    def update_status(self):
        voltage, current, capacity = None, None, None

        if self.sensor:
            try:
                voltage = self.sensor.getBusVoltage_V()
                current = self.sensor.getCurrent_mA()
                capacity = voltage_to_percent(voltage)
            except Exception as e:
                print(f"Error reading from sensor: {e}")

        # Use the user's specified logic: positive current is charging
        # Use a small threshold to avoid classifying idle as charging
        is_charging = current is not None and current > 10

        generate_battery_icon(capacity, is_charging)
        generate_text_icon(capacity)

        self.icon_batt.set_from_file(ICON_BATT_PATH)
        self.icon_text.set_from_file(ICON_TEXT_PATH)

        if capacity is None:
            tooltip = "Error: Could not read from sensor."
        else:
            state = "Charging" if is_charging else "Discharging"
            tooltip = f"Battery: {int(capacity)}% ({state})\nVoltage: {voltage:.2f}V\nCurrent: {current:.0f}mA"

        self.icon_batt.set_tooltip_text(tooltip)
        self.icon_text.set_tooltip_text(tooltip)

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
