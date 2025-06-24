"""
Jinja MCP Server using official MCP Python SDK with StreamableHttp transport.
"""

import asyncio
import json
import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .jinja.environment import JinjaEnvironmentManager
from .utils import setup_logging, get_logger


class JinjaMCPServer:
    """Jinja2 MCP Server implementation using FastMCP."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.jinja_manager = JinjaEnvironmentManager(self.settings.jinja)
        
        # Create FastMCP server with StreamableHttp support
        self.mcp = FastMCP(
            name=self.settings.mcp.name,
            stateless_http=False  # Use stateful mode for session management
        )
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP tools."""
        
        @self.mcp.tool(description="Render a Jinja2 template with JSON parameters")
        async def render_template(template_content: str, variables: dict) -> str:
            """Render a Jinja2 template string with variables.
            
            Args:
                template_content: The Jinja2 template content as a string
                variables: JSON object containing template variables
                
            Returns:
                The rendered template as a string
            """
            return await self.jinja_manager.render_template(template_content, variables)
        
        @self.mcp.tool(description="Render a Jinja2 template file with JSON parameters")
        async def render_template_file(template_path: str, variables: dict) -> str:
            """Render a Jinja2 template file with variables.
            
            Args:
                template_path: Path to the template file
                variables: JSON object containing template variables
                
            Returns:
                The rendered template as a string
            """
            return await self.jinja_manager.render_template_file(template_path, variables)
        
        @self.mcp.tool(description="Validate Jinja2 template syntax and analyze structure")
        async def validate_template(template_content: str) -> dict:
            """Validate a Jinja2 template and return analysis.
            
            Args:
                template_content: The Jinja2 template content to validate
                
            Returns:
                Validation result with syntax check and template analysis
            """
            return await self.jinja_manager.validate_template(template_content)
        
        @self.mcp.tool(description="List available Jinja2 filters")
        async def list_filters() -> dict:
            """List all available Jinja2 filters.
            
            Returns:
                Dictionary containing builtin and custom filters
            """
            return await self.jinja_manager.list_filters()
        
        @self.mcp.tool(description="Get detailed information about a template")
        async def get_template_info(template_content: str) -> dict:
            """Get detailed information and metadata about a template.
            
            Args:
                template_content: The Jinja2 template content to analyze
                
            Returns:
                Template information including size, complexity, and structure
            """
            return await self.jinja_manager.get_template_info(template_content)
    
    async def initialize(self):
        """Initialize the server."""
        setup_logging(self.settings.logging)
        await self.jinja_manager.initialize()
        self.logger.info("Jinja MCP Server initialized successfully")
    
    def run_stdio(self):
        """Run the server with stdio transport."""
        asyncio.run(self._run_stdio())
    
    async def _run_stdio(self):
        """Run the server with stdio transport (async)."""
        await self.initialize()
        self.mcp.run(transport="stdio")
    
    def run_streamable_http(self, host: str = "0.0.0.0", port: int = 3000):
        """Run the server with StreamableHttp transport."""
        asyncio.run(self._run_streamable_http(host, port))
    
    async def _run_streamable_http(self, host: str, port: int):
        """Run the server with StreamableHttp transport (async)."""
        await self.initialize()
        
        # Configure server for StreamableHttp
        import uvicorn
        
        # Get the ASGI app for StreamableHttp
        app = self.mcp.streamable_http_app()
        
        self.logger.info(f"Starting Jinja MCP Server on {host}:{port}")
        
        # Run with uvicorn
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    """Main entry point for the server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Jinja MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "streamable-http"], 
        default="stdio",
        help="Transport protocol to use"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0",
        help="Host to bind to (for streamable-http)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=3000,
        help="Port to bind to (for streamable-http)"
    )
    
    args = parser.parse_args()
    
    server = JinjaMCPServer()
    
    if args.transport == "stdio":
        await server._run_stdio()
    else:
        await server._run_streamable_http(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main()) 