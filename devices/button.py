from core.logger import logger
from memory.models import MemoryCreate, LogCreate

# Keep a reference to the button object to prevent garbage collection
button = None

def setup_button(memory_manager):
    global button
    try:
        from gpiozero import Button
        
        # GPIO 17 corresponds to physical pin number 11.
        # Configure internal pull-up resistor and set debounce time to 0.1s.
        button = Button(17, pull_up=True, bounce_time=0.1)
        
        def on_press():
            logger.info("GPIO Event: Physical button pressed (GPIO17).")
            try:
                # 1. Insert log: message="Physical button pressed", level="INFO"
                memory_manager.add_log(LogCreate(
                    message="Physical button pressed",
                    level="INFO"
                ))
                
                # 2. Insert memory: title="Button Memory", content="Created from physical button", type="button", source="gpio"
                memory_manager.add_memory(MemoryCreate(
                    title="Button Memory",
                    content="Created from physical button",
                    type="button",
                    source="gpio"
                ))
            except Exception as e:
                logger.error(f"Error processing physical button event: {e}")
                
        button.when_pressed = on_press
        logger.info("Physical memory button initialized on GPIO 17 (Pin 11)")
        
    except Exception as e:
        logger.warning(
            f"Unable to load physical GPIO Button on GPIO17: {e}. "
            "Server will run in simulated/headless environment."
        )
