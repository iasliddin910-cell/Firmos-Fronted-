"""
OmniAgent X - Configuration Settings
=====================================
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4"  # Most powerful model
OPENAI_TEMPERATURE = 0.7
OPENAI_MAX_TOKENS = 4000

# UI Configuration
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
THEME = "dark-blue"
COLOR_SCHEME = {
    "bg": "#0D1117",
    "panel": "#161B22",
    "accent": "#7C3AED",
    "text": "#E4E4E7",
    "success": "#10B981",
    "error": "#EF4444",
    "warning": "#F59E0B"
}

# Tools Configuration
BROWSER_HEADLESS = False  # Set True for background browsing
SANDBOX_MODE = True  # Safe code execution
MAX_CODE_EXECUTION_TIME = 30  # seconds

# File Access
ALLOWED_EXTENSIONS = [".py", ".js", ".txt", ".json", ".html", ".css", ".md", ".csv", ".xml"]
BLOCKED_PATHS = ["/etc", "/system", "/boot", "/root"]  # Security

# Memory
MAX_HISTORY_MESSAGES = 50
SESSION_FILE = DATA_DIR / "session_history.json"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = DATA_DIR / "agent.log"