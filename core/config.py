import logging
import os

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("transfer.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Reward Transfer Service"
    DEBUG: bool = os.getenv("DEBUG")
    API_V1_STR: str = "/api/v1"

settings = Settings()
