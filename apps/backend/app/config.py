"""
MeetingPilot Backend — Application Configuration
Loads all settings from environment variables via pydantic-settings.
"""

from __future__ import annotations

import json
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database (NeonDB) ---
    database_url: str

    # --- Redis ---
    redis_url: str = "redis://redis:6379/0"

    # --- Google OAuth 2.0 ---
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    # Google OAuth scopes requested during single SSO consent
    google_scopes: List[str] = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/spreadsheets",
    ]

    # --- Groq API (simulating local Ollama) ---
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"

    # --- OSINT API Keys ---
    jina_api_key: str = ""
    hunter_api_key: str = ""
    linkdapi_key: str = ""
    apify_token: str = ""

    # --- LangSmith ---
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "meetingpilot"

    # --- Sentry ---
    sentry_dsn: str = ""

    # --- Application ---
    app_secret_key: str
    admin_email: str = "abhinavisdas83@gmail.com"
    frontend_url: str = "http://localhost:3000"
    cors_origins: List[str] = ["http://localhost:3000"]

    # --- KB Ingestion Limits ---
    kb_gmail_limit: int = 10
    kb_drive_limit: int = 3
    kb_sheets_limit: int = 3

    # --- Workflow Tuning ---
    direct_search_word_cap: int = 800
    rag_retrieval_word_cap: int = 500

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [s.strip() for s in v.split(",")]
        return v


settings = Settings()  # type: ignore[call-arg]
