"""
devices/button.py

DRY GPIO Button handler for Octizen.
Handles any number of buttons via the BUTTONS config list.
All events route through EventManager — zero code duplication.

Supported events:
    button.click         — single click
    button.double_click  — two clicks within MULTI_CLICK_WINDOW
    button.triple_click  — three clicks within MULTI_CLICK_WINDOW
    button.hold          — held longer than hold_time

Pin factory: lgpio (required on Pi Zero 2W / newer kernels).
Install:  sudo apt install -y liblgpio-dev
          pip install lgpio
"""

from gpiozero import Button, Device
from signal import pause
from threading import Timer
from core.logger import logger

# ── Pin factory: force lgpio ──────────────────────────────────────────────────
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
    {"pin": 17, "name": "main", "bounce_time": 0.05, "hold_time": 1.0},
    # Future:
    # {"pin": 27, "name": "wifi", "bounce_time": 0.3, "hold_time": 1.0},
]

# Time window (seconds) to wait for additional clicks before resolving
MULTI_CLICK_WINDOW = 0.5


class ButtonManager:
    """
    Manages all GPIO buttons. Config-driven, DRY.
    Detects: single click, double click, triple click, hold.
    Adding a new button = add one dict to BUTTONS.
    """

    def __init__(self, event_manager):
        """
        Args:
            event_manager: core.event_manager.EventManager instance
        """
        self._event_manager = event_manager
        self._buttons = {}

        # Per-button tracking state
        self._click_counts = {}   # pin → click count
        self._click_timers = {}   # pin → Timer
        self._held_flags = {}     # pin → bool (was this press a hold?)

        for config in BUTTONS:
            pin = config["pin"]
            name = config["name"]
            bounce = config["bounce_time"]
            hold = config.get("hold_time", 1.0)

            btn = Button(
                pin,
                pull_up=True,
                bounce_time=bounce,
                hold_time=hold,
            )

            # Init tracking state
            self._click_counts[pin] = 0
            self._held_flags[pin] = False

            # Wire all three callbacks — same handler for all buttons (DRY)
            btn.when_pressed = lambda p=pin, n=name: self._on_press(p, n)
            btn.when_released = lambda p=pin, n=name: self._on_release(p, n)
            btn.when_held = lambda p=pin, n=name: self._on_hold(p, n)

            self._buttons[name] = btn
            logger.info(f"[Button] Registered: {name} → GPIO {pin} (hold={hold}s)")

    def start(self):
        """Start listening for button events (non-blocking)."""
        names = ", ".join(self._buttons.keys())
        logger.info(f"[Button] Setup complete. Active listeners: {names}")

    # ------------------------------------------------------------------
    # Callbacks — one set for ALL buttons (DRY)
    # ------------------------------------------------------------------

    def _on_press(self, pin: int, name: str):
        """Called immediately when any button is pressed."""
        self._held_flags[pin] = False

    def _on_hold(self, pin: int, name: str):
        """Called when any button is held longer than hold_time."""
        self._held_flags[pin] = True

        # Cancel any pending click timer — this is a hold, not a click
        timer = self._click_timers.get(pin)
        if timer:
            timer.cancel()
            self._click_counts[pin] = 0

        self._event_manager.emit("button.hold", {"pin": pin, "name": name})

    def _on_release(self, pin: int, name: str):
        """Called when any button is released."""
        # If this release follows a hold, ignore it
        if self._held_flags[pin]:
            self._held_flags[pin] = False
            return

        # Count this click
        self._click_counts[pin] = self._click_counts.get(pin, 0) + 1

        # Cancel existing timer (user might click again)
        timer = self._click_timers.get(pin)
        if timer:
            timer.cancel()

        # Start a new timer — when it expires, resolve the click count
        self._click_timers[pin] = Timer(
            MULTI_CLICK_WINDOW,
            self._resolve_clicks,
            args=(pin, name),
        )
        self._click_timers[pin].start()

    def _resolve_clicks(self, pin: int, name: str):
        """
        Called after MULTI_CLICK_WINDOW with no new clicks.
        Emits the appropriate event based on click count.
        """
        count = self._click_counts.get(pin, 0)
        self._click_counts[pin] = 0

        event_map = {
            1: "button.click",
            2: "button.double_click",
            3: "button.triple_click",
        }

        event_name = event_map.get(count, f"button.click_x{count}")
        self._event_manager.emit(event_name, {"pin": pin, "name": name})
