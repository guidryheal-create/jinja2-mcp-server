"""
Jinja MCP Server using official MCP Python SDK with StreamableHttp transport.
"""

from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .jinja.environment import JinjaEnvironmentManager
from .utils.logging import get_logger, setup_logging


class JinjaMCPServer:
    """Jinja2 MCP Server implementation using FastMCP."""

    def __init__(self, *, log_level: str | None = None):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.jinja_manager = JinjaEnvironmentManager(self.settings.jinja)

        effective_log_level = log_level or self.settings.logging.level
        self.mcp = FastMCP(
            name=self.settings.mcp.name,
            stateless_http=False,
            log_level=effective_log_level,  # type: ignore[arg-type]
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
    
    async def initialize(self) -> None:
        """Initialize the Jinja2 environment."""
        await self.jinja_manager.initialize()

    async def run_stdio(self) -> None:
        """Run the server with stdio transport."""
        await self.initialize()
        await self.mcp.run_stdio_async()

    async def run_streamable_http(self, host: str = "0.0.0.0", port: int = 3000) -> None:
        """Run the server with Streamable HTTP transport."""
        setup_logging(self.settings.logging, transport="streamable-http")
        await self.initialize()
        self.logger.info("Jinja MCP Server initialized")

        import uvicorn

        app = self.mcp.streamable_http_app()
        self.logger.info("Starting Jinja MCP Server", host=host, port=port)

        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()


def main() -> None:
    """Synchronous CLI entry point for uvx and console_scripts."""
    import argparse

    import anyio

    parser = argparse.ArgumentParser(description="Jinja MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "http"],
        default="stdio",
        help="Transport protocol to use (http is an alias for streamable-http)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (for streamable-http)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to bind to (for streamable-http)",
    )

    args = parser.parse_args()
    settings = get_settings()

    log_level = "WARNING" if args.transport == "stdio" else None
    if args.transport == "stdio":
        setup_logging(settings.logging, transport="stdio")

    server = JinjaMCPServer(log_level=log_level)

    if args.transport == "stdio":
        anyio.run(server.run_stdio)
    else:
        anyio.run(server.run_streamable_http, args.host, args.port)


if __name__ == "__main__":
    main() 