"""
Custom MCP 1 — OSINT Research Server

A proper MCP server built with FastMCP that exposes OSINT research capabilities
as MCP tools. This server runs as a separate process and is connected to via
stdio transport by the LangGraph workflow.

The server enforces:
- Per-user credit quota (from credit_ledger)
- Per-contact do_not_research opt-outs
- Person-level caching (from person_research)

Tools exposed:
- research_person: Full OSINT pipeline for a single person
- check_credits: Check remaining credits for a user
- get_cached_research: Retrieve cached research without running pipeline

Resources exposed:
- osint://person/{person_key}: Cached OSINT data for a person
- osint://credits/{user_id}: Credit balance for a user
"""
