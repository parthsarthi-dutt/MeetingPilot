"""
MCP Client — Connects to MCP servers from the LangGraph workflow.

Uses FastMCP's Client to spawn and communicate with MCP servers
via stdio transport. The client manages the lifecycle of server
subprocesses and provides a clean async interface for tool calls.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

logger = logging.getLogger(__name__)

# Path to the OSINT MCP server module
_OSINT_SERVER_PATH = str(
    Path(__file__).parent / "osint_server" / "server.py"
)

# Path to the Google Workspace MCP server module
_GOOGLE_WORKSPACE_SERVER_PATH = str(
    Path(__file__).parent / "google_workspace" / "server.py"
)


def _build_env() -> dict:
    """Build environment variables to pass to MCP server subprocesses."""
    env = os.environ.copy()
    # Ensure the app package is importable from the server subprocess
    backend_root = str(Path(__file__).parent.parent.parent)
    existing_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{existing_path}" if existing_path else backend_root
    return env


class OSINTMCPClient:
    """
    Client for the OSINT Research MCP Server.

    Usage:
        async with OSINTMCPClient() as client:
            result = await client.research_person(
                name="Jane Doe",
                company="TechCo",
                email="jane@techco.com",
                user_id="uuid-string",
            )
    """

    def __init__(self):
        self._transport = StdioTransport(
            command=sys.executable,
            args=[_OSINT_SERVER_PATH],
            env=_build_env(),
        )
        self._client = Client(self._transport)

    async def __aenter__(self):
        await self._client.__aenter__()
        logger.info("[MCP:OSINT] Client connected to OSINT server")
        return self

    async def __aexit__(self, *args):
        await self._client.__aexit__(*args)
        logger.info("[MCP:OSINT] Client disconnected from OSINT server")

    async def list_tools(self) -> list:
        """List all tools available on the OSINT server."""
        tools = await self._client.list_tools()
        return tools

    async def research_person(
        self,
        name: str,
        company: str,
        email: Optional[str] = None,
        user_id: Optional[str] = None,
        force_rerun: bool = False,
    ) -> dict:
        """
        Call the research_person tool on the OSINT MCP server.

        Returns parsed JSON dict with status, person_key, osint_data, etc.
        """
        args: Dict[str, Any] = {
            "name": name,
            "company": company,
        }
        if email:
            args["email"] = email
        if user_id:
            args["user_id"] = user_id
        args["force_rerun"] = force_rerun

        logger.info(f"[MCP:OSINT] Calling research_person for {name} ({company})")

        result = await self._client.call_tool("research_person", args)

        # FastMCP returns a list of content blocks; extract text
        raw = _extract_text(result)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"[MCP:OSINT] Invalid JSON from research_person: {raw[:200]}")
            return {"status": "failed", "reason": "invalid_response", "raw": raw}

    async def check_credits(self, user_id: str) -> dict:
        """Call the check_credits tool."""
        result = await self._client.call_tool("check_credits", {"user_id": user_id})
        raw = _extract_text(result)
        return json.loads(raw)

    async def get_cached_research(
        self,
        name: str,
        company: str,
        email: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Call the get_cached_research tool."""
        args: Dict[str, Any] = {"name": name, "company": company}
        if email:
            args["email"] = email
        if user_id:
            args["user_id"] = user_id

        result = await self._client.call_tool("get_cached_research", args)
        raw = _extract_text(result)
        return json.loads(raw)

    async def read_credits_resource(self, user_id: str) -> dict:
        """Read the osint://credits/{user_id} resource."""
        result = await self._client.read_resource(f"osint://credits/{user_id}")
        raw = _extract_text(result)
        return json.loads(raw)


class GoogleWorkspaceMCPClient:
    """
    Client for the Google Workspace MCP Server.

    Stores the user's OAuth tokens (from DB after SSO login) and injects them
    into every MCP tool call. The server is fully stateless — no env-based
    token passing, no per-user subprocess needed.

    Usage:
        async with GoogleWorkspaceMCPClient(
            access_token=user.google_access_token,
            refresh_token=user.google_refresh_token,
        ) as client:
            result = await client.gmail_search("from:boss@company.com")
    """

    def __init__(self, access_token: str, refresh_token: str):
        # Per-user tokens — stored here, injected into every tool call
        self._access_token = access_token
        self._refresh_token = refresh_token

        self._transport = StdioTransport(
            command=sys.executable,
            args=[_GOOGLE_WORKSPACE_SERVER_PATH],
            env=_build_env(),
        )
        self._client = Client(self._transport)

    async def __aenter__(self):
        await self._client.__aenter__()
        logger.info("[MCP:GoogleWS] Client connected to Google Workspace server")
        return self

    async def __aexit__(self, *args):
        await self._client.__aexit__(*args)
        logger.info("[MCP:GoogleWS] Client disconnected from Google Workspace server")

    def _inject_tokens(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Inject user's OAuth tokens into tool call arguments."""
        args["access_token"] = self._access_token
        args["refresh_token"] = self._refresh_token
        return args

    async def list_tools(self) -> list:
        """List all tools available on the Google Workspace server."""
        return await self._client.list_tools()

    async def gmail_search(self, query: str, max_results: int = 20) -> dict:
        """Search Gmail messages."""
        result = await self._client.call_tool(
            "gmail_search",
            self._inject_tokens({"query": query, "max_results": max_results}),
        )
        return json.loads(_extract_text(result))

    async def gmail_send(
        self, to: str, subject: str, body: str, cc: Optional[str] = None
    ) -> dict:
        """Send an email via Gmail."""
        args = {"to": to, "subject": subject, "body": body}
        if cc:
            args["cc"] = cc
        result = await self._client.call_tool("gmail_send", self._inject_tokens(args))
        return json.loads(_extract_text(result))

    async def calendar_create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        attendees: str,
        description: str = "",
    ) -> dict:
        """Create a Google Calendar event."""
        result = await self._client.call_tool(
            "calendar_create_event",
            self._inject_tokens({
                "summary": summary,
                "start_time": start_time,
                "end_time": end_time,
                "attendees_json": attendees,
                "description": description,
            }),
        )
        return json.loads(_extract_text(result))

    async def calendar_cancel_event(self, event_id: str) -> dict:
        """Cancel a Google Calendar event."""
        result = await self._client.call_tool(
            "calendar_cancel_event",
            self._inject_tokens({"event_id": event_id}),
        )
        return json.loads(_extract_text(result))

    async def drive_search(self, query: str, max_results: int = 20) -> dict:
        """Search Google Drive files."""
        result = await self._client.call_tool(
            "drive_search",
            self._inject_tokens({"query": query, "max_results": max_results}),
        )
        return json.loads(_extract_text(result))

    async def drive_get_file_content(self, file_id: str) -> dict:
        """Get content of a Google Drive file."""
        result = await self._client.call_tool(
            "drive_get_file_content",
            self._inject_tokens({"file_id": file_id}),
        )
        return json.loads(_extract_text(result))

    async def sheets_search(self, query: str, max_results: int = 10) -> dict:
        """Search Google Sheets."""
        result = await self._client.call_tool(
            "sheets_search",
            self._inject_tokens({"query": query, "max_results": max_results}),
        )
        return json.loads(_extract_text(result))


def _extract_text(result) -> str:
    """
    Extract text content from an MCP tool call result.
    FastMCP returns results in various formats; this normalizes them.
    """
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        # List of content blocks
        texts = []
        for item in result:
            if hasattr(item, "text"):
                texts.append(item.text)
            elif isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(texts)
    if hasattr(result, "text"):
        return result.text
    if hasattr(result, "content"):
        if isinstance(result.content, list):
            return _extract_text(result.content)
        return str(result.content)
    return str(result)
