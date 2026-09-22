"""Loads settings from .env. Never hardcode keys here."""
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

RUNWAYML_API_SECRET = os.getenv("RUNWAYML_API_SECRET", "")

KLING_API_KEY = os.getenv("KLING_API_KEY", "")
KLING_API_BASE = os.getenv("KLING_API_BASE", "https://api-singapore.klingai.com")
KLING_MODEL = os.getenv("KLING_MODEL", "kling-v2-5-turbo")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
