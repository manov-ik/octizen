"""
devices/button.py

Architecture:
  GPIO interrupt (gpiozero thread)  →  puts event in queue  →  returns immediately
  Worker thread (dedicated Python thread)  →  reads queue  →  writes to SQLite

The GPIO callback must be extremely fast (never block). All DB work happens in the
worker thread, which owns its own SQLite connection and is never interrupted.
"""

import queue
import threading
from core.logger import logger
from memory.models import MemoryCreate, LogCreate

# ── Module-level state ────────────────────────────────────────────────────────
_button         = None          # gpiozero Button object (keeps it from GC)
_event_queue    = queue.Queue() # thread-safe handoff: GPIO → worker
_worker_started = False
_setup_lock     = threading.Lock()


# ── Worker thread ─────────────────────────────────────────────────────────────
def _worker(memory_manager):
    """Runs in a dedicated daemon thread.
    Reads button-press events from the queue and writes to SQLite.
    All database calls happen here — never on the GPIO interrupt thread."""
    logger.info("Button worker thread started.")
    while True:
        try:
            # Block until an event arrives (or timeout to stay alive)
            _event_queue.get(timeout=2)
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Button worker queue error: {e}", exc_info=True)
            continue

        # We have an event — write to DB
        logger.info("Button worker: processing press event.")
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
            logger.info("Button worker: log + memory written to DB successfully.")
        except Exception as e:
            logger.error(f"Button worker: DB write failed — {e}", exc_info=True)


# ── Public API ────────────────────────────────────────────────────────────────
def trigger_press():
    """Enqueue a button-press event. Safe to call from any thread or the API."""
    _event_queue.put("press")
    logger.info("Button press event queued.")


def setup_button(memory_manager):
    """Call once at application startup (inside FastAPI lifespan).
    Starts the worker thread and, if running on a Raspberry Pi, attaches
    the gpiozero GPIO17 listener."""
    global _button, _worker_started

    with _setup_lock:
        if _worker_started:
            logger.warning("setup_button() called twice — ignoring.")
            return

        # Always start the worker thread (needed for the API trigger too)
        t = threading.Thread(
            target=_worker,
            args=(memory_manager,),
            daemon=True,       # dies with the main process
            name="button-worker"
        )
        t.start()
        _worker_started = True
        logger.info("Button worker thread started.")

        # Try to attach hardware GPIO
        try:
            from gpiozero import Button

            # pull_up=True  → internal pull-up; wire button between GPIO17 and GND
            # bounce_time   → 100 ms debounce; one press = one queue entry
            _button = Button(17, pull_up=True, bounce_time=0.1)

            # GPIO callback: ONLY enqueues — never touches DB directly
            _button.when_pressed = trigger_press

            logger.info(
                "Physical button ready on GPIO 17 (Pin 11) | "
                "pull-up ON | debounce 100 ms"
            )

        except Exception as e:
            # On non-Pi hosts gpiozero raises RuntimeError (no pin factory).
            # The worker is still running so the API trigger endpoint works.
            logger.warning(
                f"GPIO not available ({type(e).__name__}: {e}). "
                "Physical button disabled — use POST /api/button-press to test."
            )
