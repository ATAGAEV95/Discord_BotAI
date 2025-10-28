import os

from dotenv import load_dotenv

load_dotenv()

WEATHER_API = os.getenv("WEATHER_API")