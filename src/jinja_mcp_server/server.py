"""
Jinja MCP Server - Main server implementation using MCP Python SDK with StreamableHttp transport.

This module provides the main MCP server implementation for Jinja2 template
rendering with comprehensive JSON parameter support.
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, AsyncIterator

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.streamable_http import streamable_http_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
    GetPromptResult,
    PromptMessage,
    PromptArgument,
    Prompt,
    ListPromptsResult,
)
import mcp.types as types

from .config import get_settings
from .jinja.environment import JinjaEnvironmentManager
from .tools.registry import ToolRegistryManager
from .utils import setup_logging, get_logger
from .utils.exceptions import JinjaMCPError, TemplateError, RenderError, ValidationError


class JinjaMCPServer:
    """Main Jinja MCP Server class using MCP Python SDK with StreamableHttp transport."""
    
    def __init__(self, name: str = "Jinja2 MCP Server"):
        """Initialize the Jinja MCP Server."""
        self.name = name
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.jinja_manager = JinjaEnvironmentManager(self.settings.jinja)
        self.tool_registry = ToolRegistryManager(self.settings)
        
        # Create MCP server
        self.server = Server(name)
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            tools = [
                Tool(
                    name="render_template",
                    description="Render a Jinja2 template with provided variables",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template": {
                                "type": "string",
                                "description": "Jinja2 template content to render"
                            },
                            "variables": {
                                "type": "object",
                                "description": "Variables to pass to the template",
                                "default": {}
                            },
                            "options": {
                                "type": "object",
                                "description": "Additional rendering options",
                                "default": {}
                            }
                        },
                        "required": ["template"]
                    }
                ),
                Tool(
                    name="render_template_file",
                    description="Render a Jinja2 template file with provided variables",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_path": {
                                "type": "string",
                                "description": "Path to the template file"
                            },
                            "variables": {
                                "type": "object",
                                "description": "Variables to pass to the template",
                                "default": {}
                            },
                            "options": {
                                "type": "object",
                                "description": "Additional rendering options",
                                "default": {}
                            }
                        },
                        "required": ["template_path"]
                    }
                ),
                Tool(
                    name="validate_template",
                    description="Validate Jinja2 template syntax and analyze structure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template": {
                                "type": "string",
                                "description": "Template content to validate"
                            }
                        },
                        "required": ["template"]
                    }
                ),
                Tool(
                    name="list_filters",
                    description="List all available Jinja2 filters",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                ),
                Tool(
                    name="get_template_info",
                    description="Get detailed information about a template",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template": {
                                "type": "string",
                                "description": "Template content to analyze"
                            }
                        },
                        "required": ["template"]
                    }
                )
            ]
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                self.logger.info(f"Tool called: {name}", arguments=list(arguments.keys()))
                
                if name == "render_template":
                    result = await self.jinja_manager.render_template(
                        template_content=arguments["template"],
                        variables=arguments.get("variables", {}),
                        options=arguments.get("options", {})
                    )
                    return CallToolResult(
                        content=[TextContent(type="text", text=result)]
                    )
                
                elif name == "render_template_file":
                    result = await self.jinja_manager.render_template_file(
                        template_path=arguments["template_path"],
                        variables=arguments.get("variables", {}),
                        options=arguments.get("options", {})
                    )
                    return CallToolResult(
                        content=[TextContent(type="text", text=result)]
                    )
                
                elif name == "validate_template":
                    result = await self.jinja_manager.validate_template(
                        template_content=arguments["template"]
                    )
                    import json
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif name == "list_filters":
                    result = await self.jinja_manager.list_filters()
                    import json
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif name == "get_template_info":
                    result = await self.jinja_manager.get_template_info(
                        template_content=arguments["template"]
                    )
                    import json
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                self.logger.error(f"Tool execution failed: {name}", error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
        
        @self.server.list_prompts()
        async def handle_list_prompts() -> ListPromptsResult:
            """List available prompts."""
            prompts = [
                Prompt(
                    name="template_help",
                    description="Get help with Jinja2 template syntax and usage",
                    arguments=[
                        PromptArgument(
                            name="topic",
                            description="Specific topic to get help with",
                            required=False
                        )
                    ]
                ),
                Prompt(
                    name="debug_template",
                    description="Debug a Jinja2 template that's not working correctly",
                    arguments=[
                        PromptArgument(
                            name="template",
                            description="The template content that needs debugging",
                            required=True
                        ),
                        PromptArgument(
                            name="variables",
                            description="Variables being passed to the template",
                            required=False
                        ),
                        PromptArgument(
                            name="error",
                            description="Error message received",
                            required=False
                        )
                    ]
                )
            ]
            
            return ListPromptsResult(prompts=prompts)
        
        @self.server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Optional[Dict[str, str]]) -> GetPromptResult:
            """Handle prompt requests."""
            if name == "template_help":
                topic = arguments.get("topic", "general") if arguments else "general"
                
                help_content = f"""# Jinja2 Template Help - {topic.title()}

## Basic Syntax
- Variables: `{{{{ variable_name }}}}`
- Comments: `{{# This is a comment #}}`
- Control structures: `{{% if condition %}}...{{% endif %}}`

## Common Filters
- `|upper` - Convert to uppercase
- `|lower` - Convert to lowercase
- `|length` - Get length of sequence
- `|default('fallback')` - Provide default value

## Control Structures
- `{{% if condition %}}...{{% endif %}}`
- `{{% for item in items %}}...{{% endfor %}}`
- `{{% set variable = value %}}` - Set variables

## Examples
```jinja2
Hello {{{{ name|default('World') }}}}!

{{% if users %}}
<ul>
{{% for user in users %}}
  <li>{{{{ user.name }}}} ({{{{ user.email }}}})</li>
{{% endfor %}}
</ul>
{{% else %}}
<p>No users found.</p>
{{% endif %}}
```

Use the `validate_template` tool to check your template syntax!
"""
                
                return GetPromptResult(
                    description=f"Jinja2 help for {topic}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(type="text", text=help_content)
                        )
                    ]
                )
            
            elif name == "debug_template":
                template = arguments.get("template", "") if arguments else ""
                variables = arguments.get("variables", "{}") if arguments else "{}"
                error = arguments.get("error", "") if arguments else ""
                
                debug_content = f"""# Debug Jinja2 Template

## Template Content
```jinja2
{template}
```

## Variables
```json
{variables}
```

## Error Message
```
{error}
```

## Debugging Steps
1. **Validate Syntax**: Use the `validate_template` tool to check for syntax errors
2. **Check Variables**: Ensure all variables used in the template are provided
3. **Test Filters**: Verify that all filters are available and used correctly
4. **Check Logic**: Review conditional statements and loops

## Common Issues
- Missing variables: Use `|default('fallback')` filter
- Undefined filters: Check available filters with `list_filters` tool
- Syntax errors: Mismatched braces or incorrect control structure syntax
- Escaping issues: Use `|safe` filter for HTML content or configure autoescape

Let me help you debug this template step by step!
"""
                
                return GetPromptResult(
                    description="Debug Jinja2 template",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(type="text", text=debug_content)
                        )
                    ]
                )
            
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    @asynccontextmanager
    async def _lifespan_handler(self) -> AsyncIterator[None]:
        """Manage server startup and shutdown lifecycle."""
        self.logger.info("Starting Jinja MCP Server...")
        
        try:
            # Initialize Jinja environment
            await self.jinja_manager.initialize()
            
            # Initialize tool registry
            await self.tool_registry.initialize()
            
            self.logger.info("Jinja MCP Server initialized successfully")
            
            yield
            
        except Exception as e:
            self.logger.error("Failed to initialize Jinja MCP Server", error=str(e))
            raise
        finally:
            # Cleanup on shutdown
            await self.jinja_manager.cleanup()
            self.logger.info("Jinja MCP Server shutdown complete")
    
    async def run_stdio(self) -> None:
        """Run the server with stdio transport."""
        import mcp.server.stdio
        
        async with self._lifespan_handler():
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.name,
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=types.ServerCapabilities(),
                            experimental_capabilities={}
                        )
                    )
                )
    
    async def run_streamable_http(self, host: str = "0.0.0.0", port: int = 3000) -> None:
        """Run the server with StreamableHttp transport."""
        async with self._lifespan_handler():
            async with streamable_http_server(
                self.server,
                host=host,
                port=port
            ) as server:
                self.logger.info(f"Jinja MCP Server running on http://{host}:{port}")
                await server.serve_forever()


async def main():
    """Main entry point for the Jinja MCP Server."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Jinja2 MCP Server")
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
        default=int(os.getenv("PORT", "3000")),
        help="Port to bind to (for streamable-http)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Create and run server
    server = JinjaMCPServer()
    
    try:
        if args.transport == "stdio":
            await server.run_stdio()
        elif args.transport == "streamable-http":
            await server.run_streamable_http(host=args.host, port=args.port)
    except KeyboardInterrupt:
        server.logger.info("Server interrupted by user")
    except Exception as e:
        server.logger.error("Server error", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main()) 