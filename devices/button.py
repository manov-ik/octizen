import threading
from core.logger import logger
from memory.models import MemoryCreate, LogCreate

# Module-level reference — keeps the Button object alive (prevents GC)
# and guards against being called twice (e.g. accidental double-import).
_button = None
_setup_lock = threading.Lock()

def setup_button(memory_manager):
    global _button

    with _setup_lock:
        if _button is not None:
            logger.warning("Button already initialised — skipping duplicate setup.")
            return

        try:
            from gpiozero import Button

            # GPIO 17 = physical pin 11.
            # pull_up=True  → internal pull-up resistor enabled (button wires to GND).
            # bounce_time   → 100 ms hardware debounce; one press = one event.
            _button = Button(17, pull_up=True, bounce_time=0.1)

            def on_press():
                """Runs in gpiozero's background thread — database writes are safe
                because we pass check_same_thread=False in sqlite3.connect()."""
                logger.info("GPIO17 pressed — inserting log and memory.")
                try:
                    memory_manager.add_log(LogCreate(
                        message="Physical button pressed",
                        level="INFO"
                    ))
                    memory_manager.add_memory(MemoryCreate(
                        title="Button Memory",
                        content="Created from physical button",
                        type="button",
                        source="gpio"
                    ))
                    logger.info("GPIO17: log + memory saved successfully.")
                except Exception as e:
                    logger.error(f"GPIO17 on_press handler failed: {e}", exc_info=True)

            _button.when_pressed = on_press
            logger.info("Physical button ready — GPIO 17 (Pin 11), pull-up enabled, debounce 100 ms.")

        except Exception as e:
            # gpiozero raises RuntimeError on non-Pi hosts (no pin factory).
            # We log a clear warning and let the server start normally in
            # mock/dev mode — the button simply won't fire any events.
            logger.warning(
                f"GPIO button NOT available ({type(e).__name__}: {e}). "
                "Running in headless mode — button events disabled."
            )
            _button = None  # ensure guard stays clear on failure
