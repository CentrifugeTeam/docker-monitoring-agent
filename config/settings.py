import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
  DOCKER_SOCKET = os.getenv("DOCKER_SOCKET")
  API_URL = os.getenv("API_URL")
  API_KEY = os.getenv("API_KEY")
  INTERVAL = int(os.getenv("INTERVAL_SECONDS", 60))

settings = Settings()
