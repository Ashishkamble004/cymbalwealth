"""
Wealth Management Platform — Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Database
    DB_URL: str = os.getenv("DB_URL", "postgresql://wealthuser:changeme@localhost:5432/wealthdb")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_TEXT_MODEL: str = "gemini-2.0-flash"
    GEMINI_VOICE_MODEL: str = "gemini-2.5-flash-preview-native-audio"

    # GCP
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_REGION: str = os.getenv("GCP_REGION", "asia-south1")

    # Cloud Storage
    GCS_KYC_BUCKET: str = os.getenv("GCS_KYC_BUCKET", "kyc-documents")
    GCS_VOICE_BUCKET: str = os.getenv("GCS_VOICE_BUCKET", "voice-transcripts")

    # Application
    BANK_NAME: str = os.getenv("BANK_NAME", "Prestige Private Bank")

    # CORS
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",")


settings = Settings()
