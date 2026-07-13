"""
devices/button.py

GPIO Button handler for Octizen.
Pin: GPIO 17 (BCM) = Physical Pin 11

Calls on_press callback on every debounced button press.

Pin factory: lgpio (required on Pi Zero 2W / newer kernels).
Install:  sudo apt install -y python3-lgpio
          -- OR --
          pip install lgpio
"""

from gpiozero import Button, Device
from signal import pause
from core.logger import logger

# ── Pin factory: force lgpio ──────────────────────────────────────────────────
# The default NativePinFactory uses /sys/class/gpio which is removed in newer
# kernels. lgpio is the modern, kernel-compatible replacement.
try:
    from gpiozero.pins.lgpio import LGPIOFactory
    Device.pin_factory = LGPIOFactory()
    logger.info("[Button] Pin factory: lgpio ✅")
except ImportError:
    raise SystemExit(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ERROR: lgpio is not installed.\n"
        "  The NativePinFactory (/sys/class/gpio) is removed\n"
        "  on newer Pi kernels. lgpio is required.\n"
        "\n"
        "  Fix:\n"
        "    source .venv/bin/activate\n"
        "    pip install lgpio\n"
        "\n"
        "  Then run again: python3 main.py\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

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
