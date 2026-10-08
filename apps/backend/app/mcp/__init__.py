"""
MCP Package — Model Context Protocol servers and client.

This package contains two FastMCP servers and a unified client:

Servers (run as subprocesses via stdio transport):
- osint_server/  — Custom MCP 1: OSINT Research Server
  Tools: research_person, check_credits, get_cached_research
  Resources: osint://credits/{user_id}, osint://person/{user_id}/{person_key}
  Prompts: research_brief_prompt

- google_workspace/  — Custom MCP 2: Google Workspace Server
  Tools: gmail_search, gmail_send, calendar_create_event, calendar_cancel_event,
         calendar_watch, drive_search, drive_get_file_content, sheets_search
  Resources: google://user/profile, google://calendar/upcoming
  Prompts: email_agenda_prompt, search_context_prompt

Client (used by the LangGraph workflow):
- client.py — OSINTMCPClient, GoogleWorkspaceMCPClient
  Connects to the servers above via StdioTransport and calls tools
  using the MCP protocol.
"""

from app.mcp.client import OSINTMCPClient, GoogleWorkspaceMCPClient

__all__ = ["OSINTMCPClient", "GoogleWorkspaceMCPClient"]
