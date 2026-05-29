import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'medextract_ai.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 25 * 1024 * 1024))
    UPLOAD_ORIGINAL_FOLDER = Path(
        os.getenv("UPLOAD_ORIGINAL_FOLDER", BASE_DIR / "uploads" / "original")
    )
    UPLOAD_PROCESSED_FOLDER = Path(
        os.getenv("UPLOAD_PROCESSED_FOLDER", "/tmp/medextract-processed")
    )
    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")
    OPENROUTER_VISION_MODEL = os.getenv(
        "OPENROUTER_VISION_MODEL", "qwen/qwen3-vl-32b-instruct"
    )
    OPENROUTER_BASE_URL = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "")
    OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "MedExtract AI")

    OCR_LANG = os.getenv("OCR_LANG", "en")
    OCR_USE_GPU = os.getenv("OCR_USE_GPU", "false").lower() == "true"
    CV_BILL_EXTRACTION_ENABLED = (
        os.getenv("CV_BILL_EXTRACTION_ENABLED", "true").lower() == "true"
    )
    AI_EXTRACTION_ENABLED = os.getenv("AI_EXTRACTION_ENABLED", "false").lower() == "true"
    AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.72"))
    AI_MAX_VISION_PAGES = int(os.getenv("AI_MAX_VISION_PAGES", "3"))
    AI_VISION_MAX_WIDTH = int(os.getenv("AI_VISION_MAX_WIDTH", "1400"))
    ENABLE_BACKGROUND_WORKER = (
        os.getenv("ENABLE_BACKGROUND_WORKER", "true").lower() == "true"
    )
    BACKGROUND_WORKER_POLL_SECONDS = float(
        os.getenv("BACKGROUND_WORKER_POLL_SECONDS", "5")
    )
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    OPENROUTER_API_KEY = ""
    AI_EXTRACTION_ENABLED = False
    ENABLE_BACKGROUND_WORKER = False


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
