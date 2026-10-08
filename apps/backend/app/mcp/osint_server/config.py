"""
OSINT MCP Server — Configuration.

Holds settings specific to this MCP server, loaded from environment variables.
This keeps the MCP server self-contained and independently configurable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class OSINTServerConfig:
    """Configuration for the OSINT MCP Server."""

    # API keys for the underlying pipeline
    jina_api_key: str = ""
    hunter_api_key: str = ""
    linkdapi_key: str = ""
    apify_token: str = ""

    # Database connection (needed for cache/credit checks)
    database_url: str = ""

    # Server metadata
    server_name: str = "MeetingPilot OSINT Research Server"
    server_version: str = "1.0.0"

    @classmethod
    def from_env(cls) -> "OSINTServerConfig":
        """Load config from environment variables."""
        return cls(
            jina_api_key=os.environ.get("JINA_API_KEY", ""),
            hunter_api_key=os.environ.get("HUNTER_API_KEY", ""),
            linkdapi_key=os.environ.get("LINKDAPI_KEY", ""),
            apify_token=os.environ.get("APIFY_TOKEN", ""),
            database_url=os.environ.get("DATABASE_URL", ""),
        )
