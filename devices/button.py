"""
devices/button.py

GPIO Button handler for Octizen.
Pin: GPIO 17 (BCM) = Physical Pin 11

Calls on_press callback on every debounced button press.
"""

from gpiozero import Button
from signal import pause
from core.logger import logger

BUTTON_PIN = 17   # BCM numbering = Physical Pin 11


class ButtonManager:
    def __init__(self, on_press=None):
        """
        Args:
            on_press: optional callable(pin: int) called on every press
        """
        self.button = Button(
            BUTTON_PIN,
            pull_up=True,
            bounce_time=0.2,
        )
        self._on_press = on_press

    def start(self):
        """Attach callback and block (runs forever via pause())."""
        logger.info(f"[Button] Listening on GPIO {BUTTON_PIN} (Physical Pin 11)...")
        self.button.when_pressed = self._handle_press
        pause()

    def _handle_press(self):
        logger.info(f"[Button] 🔘 Button pressed on pin {BUTTON_PIN}")
        print(f"🔘 Button Pressed (GPIO {BUTTON_PIN})")

        if self._on_press:
            self._on_press(pin=BUTTON_PIN)
