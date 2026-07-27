"""
Centralized configuration. Everything environment-specific lives here so the
rest of the app never touches os.environ directly.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # picks up a local .env file if present


class Settings:
    # --- Placeholder for your API key -------------------------------------
    # Set this in a `.env` file (see .env) or as a real environment
    # variable. Never hard-code the key here.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Using the "-latest" alias avoids pinning to a specific dated model
    # version, so the app keeps working as Google rolls new versions out.
    # Override with a specific model id in .env if you ever need to pin one.
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    # Generation controls
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.8"))

    APP_TITLE: str = "AI Interview Coach"


settings = Settings()


def api_key_configured() -> bool:
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
