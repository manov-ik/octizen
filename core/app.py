from core.logger import logger
from core.config import Config


class Octizen:
    def __init__(self):
        self.config = Config()

    def start(self):
        logger.info("Starting Octizen...")
        logger.info(f"Version: {self.config.VERSION}")
        logger.info("Octizen is ready ")
        
