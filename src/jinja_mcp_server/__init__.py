"""
Jinja MCP Server - A Model Context Protocol server for Jinja2 template rendering.

This package provides a MCP-compatible server that enables clients to render
Jinja2 templates with JSON parameter support, template validation, and 
comprehensive error handling.
"""

__version__ = "0.1.0"
__author__ = "BarlowLiu"
__email__ = "toxingwang@gmail.com"

from .mcp_server import main

__all__ = ["main"] 