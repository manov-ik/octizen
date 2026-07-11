from core.logger import logger
from memory.manager import memory_manager
from memory.models import MemoryCreate, LogCreate

class PhysicalButton:
    def __init__(self, pin: int = 17):
        self.pin = pin
        self.button = None
        self._setup()

    def _setup(self):
        try:
            from gpiozero import Button
            # Use GPIO17, pull-up resistor = True, debounce = 0.1s (100ms)
            self.button = Button(self.pin, pull_up=True, bounce_time=0.1)
            self.button.when_pressed = self._on_pressed
            logger.info(f"GPIO: Physical button initialized on GPIO {self.pin} with internal pull-up and debouncing.")
        except Exception as e:
            logger.warning(
                f"GPIO: Could not initialize physical button on GPIO {self.pin}: {e}. "
                "Running in Simulation Mode. Use the simulator endpoint to trigger button events."
            )
            self.button = None

    def _on_pressed(self):
        logger.info("GPIO Event: Button Pressed detected on GPIO17.")
        self.trigger_press()

    def trigger_press(self):
        logger.info("Triggering database inserts via Memory Manager...")
        try:
            # 1. Insert log: message="Physical button pressed", level=INFO
            log_item = memory_manager.add_log(LogCreate(
                message="Physical button pressed",
                level="INFO"
            ))
            
            # 2. Insert memory: title="Button Memory", content="Created from physical button", type="button", source="gpio"
            mem_item = memory_manager.add_memory(MemoryCreate(
                title="Button Memory",
                content="Created from physical button",
                type="button",
                source="gpio"
            ))
            
            logger.info(f"Recorded button event. Log ID: {log_item.id}, Memory ID: {mem_item.id}")
            return {"success": True, "log_id": log_item.id, "memory_id": mem_item.id}
        except Exception as e:
            logger.error(f"Error executing memory/log insertion for button press: {e}")
            raise e

# Shared instance of the physical button
physical_button = PhysicalButton()
