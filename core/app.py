import uvicorn
from core.logger import logger
from core.config import Config


class Octizen:
    def __init__(self):
        self.config = Config()

    def start(self):
        logger.info("Starting Octizen...")
        logger.info(f"Version: {self.config.VERSION}")
        logger.info("Octizen is ready ")
        
        # Start uvicorn server serving the FastAPI app
        uvicorn.run(
            "api.server:app",
            host=self.config.HOST,
            port=self.config.PORT,
            reload=self.config.DEBUG,
        )
