import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "WhatsApp AI Chatbot"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"

    # AI Provider Settings
    # Supports 'gemini' or 'openai'
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # WhatsApp Provider (Evolution API / Z-API / Generic HTTP Webhook)
    WHATSAPP_PROVIDER: str = "evolution"
    WHATSAPP_API_URL: str = "http://localhost:8080"
    WHATSAPP_API_KEY: Optional[str] = None
    WHATSAPP_INSTANCE_NAME: str = "main_instance"

    # Bot Behavior Settings
    MAX_HISTORY_MESSAGES: int = 6
    HUMAN_TAKEOVER_KEYWORD: str = "#humano"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
