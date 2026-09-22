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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1-mini")
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.6-luna")

# --- Licensing (RAD Media Solutions internal - see product_video/licensing.py) ---
# Set only in a client's .env: the key RAD Media Solutions issued them.
LICENSE_KEY = os.getenv("HERO_STUDIO_LICENSE_KEY", "")
# Set only in the maintainer's own .env: a GitHub token with `gist` scope.
# Its presence is what makes an install the admin install - never ship this.
RAD_ADMIN_TOKEN = os.getenv("RAD_ADMIN_TOKEN", "")
# Raw URL of the licenses.json gist. Baked in below once created; overridable.
LICENSE_GIST_URL = os.getenv("LICENSE_GIST_URL", "")

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
