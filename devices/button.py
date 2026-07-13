"""
devices/button.py

DRY GPIO Button handler for Octizen.
Handles any number of buttons via the BUTTONS config list.
All presses route through EventManager — zero code duplication.

Pin factory: lgpio (required on Pi Zero 2W / newer kernels).
Install:  sudo apt install -y liblgpio-dev
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
        "    sudo apt install -y liblgpio-dev\n"
        "    source .venv/bin/activate\n"
        "    pip install lgpio\n"
        "\n"
        "  Then run again: python3 main.py\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

# ── Button config ─────────────────────────────────────────────────────────────
# Add new buttons here. Zero code changes elsewhere.
BUTTONS = [
    {"pin": 17, "name": "main", "bounce_time": 0.2},
    # Future:
    # {"pin": 27, "name": "wifi", "bounce_time": 0.3},
]


class ButtonManager:
    """
    Manages all GPIO buttons. Config-driven, DRY.
    Adding a new button = add one dict to BUTTONS.
    """

    def __init__(self, event_manager):
        """
        Args:
            event_manager: core.event_manager.EventManager instance
        """
        self._event_manager = event_manager
        self._buttons = {}

        for config in BUTTONS:
            pin = config["pin"]
            name = config["name"]
            bounce = config["bounce_time"]

            btn = Button(pin, pull_up=True, bounce_time=bounce)
            btn.when_pressed = lambda p=pin, n=name: self._handle_press(p, n)
            self._buttons[name] = btn

            logger.info(f"[Button] Registered: {name} → GPIO {pin}")

    def start(self):
        """Block forever, listening for button presses."""
        names = ", ".join(self._buttons.keys())
        logger.info(f"[Button] Listening on: {names}")
        pause()

    def _handle_press(self, pin: int, name: str):
        """
        Single handler for ALL buttons — never duplicated.
        Routes through EventManager middleware.
        """
        self._event_manager.emit("button.pressed", {"pin": pin, "name": name})
