#!/usr/bin/env python3

"""
Run Jinja MCP Server with different transport options.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jinja_mcp_server.mcp_server import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 