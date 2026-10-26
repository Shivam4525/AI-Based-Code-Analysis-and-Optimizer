```python
import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")
    REPORTS_FOLDER = os.path.join(PROJECT_ROOT, "reports")
    FIXED_CODE_FOLDER = os.path.join(PROJECT_ROOT, "fixed_code")

    # MySQL
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "ai_code_tester")
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))

    # JWT
    JWT_SECRET = os.environ.get("JWT_SECRET")
    JWT_EXPIRY_HOURS = 24 * 7

    # Ollama
    OLLAMA_HOST = os.environ.get(
        "OLLAMA_HOST", "http://localhost:11434"
    )
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "codellama")
    OLLAMA_TIMEOUT = 400

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")


def ensure_folders():
    for folder in [
        Config.UPLOAD_FOLDER,
        Config.REPORTS_FOLDER,
        Config.FIXED_CODE_FOLDER,
    ]:
        os.makedirs(folder, exist_ok=True)
```