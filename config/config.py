"""Centralized configuration management for CareerPilot Agent."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(dotenv_path=BASE_DIR / "config" / ".env", override=True)

class Config:
    # GitHub settings
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")
    GITHUB_BASE_URL = "https://api.github.com"
    
    # LLM settings
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Database settings
    DB_PATH = os.path.join(BASE_DIR, "memory", "careerpilot.db")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    
    # Cache settings
    GITHUB_CACHE_PATH = BASE_DIR / "memory" / "github_cache.json"
    GITHUB_CACHE_TTL_HOURS = int(os.getenv("GITHUB_CACHE_TTL_HOURS", "1"))
    
    # Circuit Breaker settings
    CB_FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "5"))
    CB_RECOVERY_TIMEOUT = int(os.getenv("CB_RECOVERY_TIMEOUT", "60"))
    
    # App settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        missing = []
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        if not cls.GITHUB_USERNAME:
            missing.append("GITHUB_USERNAME")
        if not cls.GROQ_API_KEY and not cls.GEMINI_API_KEY:
            missing.append("At least one of GROQ_API_KEY or GEMINI_API_KEY")
            
        if missing:
            print(f"CRITICAL: Missing configuration: {', '.join(missing)}")
            return False
        return True
