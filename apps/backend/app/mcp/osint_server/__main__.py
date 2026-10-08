"""
OSINT MCP Server — Entry point.

Run this module to start the OSINT MCP server as a standalone process:
    python -m app.mcp.osint_server

Or via FastMCP CLI:
    fastmcp run app/mcp/osint_server/server.py

The server communicates via stdio transport by default,
which is how the LangGraph workflow connects to it.
"""

from app.mcp.osint_server.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
