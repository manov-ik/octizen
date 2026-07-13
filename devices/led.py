"""
devices/led.py

LED status indicator manager for Octizen.
Pin: GPIO 18 (BCM) = Physical Pin 12

Usage:
    led = LEDManager()
    led.on()
    led.off()
    led.blink(on_time=0.5, off_time=0.5)
"""

from gpiozero import LED, Device
from core.logger import logger

LED_PIN = 18  # GPIO 18 / Physical Pin 12


class LEDManager:
    """
    Manages the status LED state.
    Steady ON when connected. Blinks or stays OFF otherwise.
    """

    def __init__(self):
        try:
            self.led = LED(LED_PIN)
            logger.info(f"[LED] Initialized status indicator on GPIO {LED_PIN}")
        except Exception as e:
            logger.error(f"[LED] Failed to initialize status LED: {e}")
            self.led = None

    def on(self) -> None:
        """Turn LED steady ON (stops any active background blink thread first)."""
        if self.led:
            try:
                self.led.off()  # cancel any active blink threads
                self.led.on()   # turn steady ON
            except Exception as e:
                logger.error(f"[LED] Error turning on: {e}")

    def off(self) -> None:
        """Turn LED OFF."""
        if self.led:
            try:
                self.led.off()
            except Exception as e:
                logger.error(f"[LED] Error turning off: {e}")

    def blink(self, on_time: float = 0.5, off_time: float = 0.5, n: int | None = None) -> None:
        """
        Blink the LED.
        
        Args:
            on_time: seconds on
            off_time: seconds off
            n: number of times to blink (None = blink forever in background)
        """
        if self.led:
            try:
                self.led.blink(on_time=on_time, off_time=off_time, n=n, background=True)
            except Exception as e:
                logger.error(f"[LED] Error starting blink pattern: {e}")
