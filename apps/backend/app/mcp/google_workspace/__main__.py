"""
Google Workspace MCP Server — Entry point.

Run:  python -m app.mcp.google_workspace
"""

from app.mcp.google_workspace.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
