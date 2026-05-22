"""
Console entry point for ``jinja2-mcp-server``.

Implements the FastMCP server in ``mcp_server``; this module exists so
``pyproject.toml`` can expose a stable ``jinja_mcp_server.server:main`` target.
"""

from jinja_mcp_server.mcp_server import main

__all__ = ["main"]
