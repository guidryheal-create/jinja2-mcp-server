"""Tool registry manager for MCP tools."""

import asyncio
import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from ..config import Settings
from ..utils import get_logger
from ..utils.exceptions import ConfigurationError, JinjaMCPError
from .base import BaseTool, ToolRegistry, ToolSchema


class ToolRegistryManager:
    """Advanced tool registry manager with auto-discovery and configuration."""
    
    def __init__(self, settings: Settings):
        """Initialize the tool registry manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.registry = ToolRegistry()
        self.logger = get_logger(__name__)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the tool registry manager."""
        if self._initialized:
            return
        
        self.logger.info("Initializing tool registry manager")
        
        try:
            # Auto-discover and register tools
            await self._auto_discover_tools()
            
            # Apply configuration filters
            self._apply_tool_filters()
            
            self._initialized = True
            self.logger.info(
                "Tool registry manager initialized",
                total_tools=len(self.registry.list_tools()),
                categories=self.registry.list_categories()
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize tool registry manager", error=str(e))
            raise ConfigurationError(f"Tool registry initialization failed: {e}")
    
    async def _auto_discover_tools(self) -> None:
        """Auto-discover tools from the tools package."""
        self.logger.debug("Auto-discovering tools")
        
        # Get the tools package directory
        tools_dir = Path(__file__).parent
        
        # Scan for tool modules
        for tool_file in tools_dir.glob("*.py"):
            if tool_file.name.startswith("_") or tool_file.name in ("base.py", "registry.py"):
                continue
            
            module_name = f"jinja_mcp_server.tools.{tool_file.stem}"
            
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Find tool classes
                await self._register_tools_from_module(module)
                
            except Exception as e:
                self.logger.warning(
                    "Failed to load tool module",
                    module=module_name,
                    error=str(e)
                )
    
    async def _register_tools_from_module(self, module) -> None:
        """Register tools from a module.
        
        Args:
            module: Python module to scan for tools
        """
        for name in dir(module):
            obj = getattr(module, name)
            
            # Check if it's a tool class
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseTool) and 
                obj != BaseTool):
                
                try:
                    # Instantiate and register the tool
                    tool_instance = obj()
                    self.registry.register(tool_instance)
                    
                    self.logger.debug(
                        "Tool registered from module",
                        tool=tool_instance.name,
                        module=module.__name__
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to register tool from module",
                        tool_class=name,
                        module=module.__name__,
                        error=str(e)
                    )
    
    def _apply_tool_filters(self) -> None:
        """Apply configuration-based tool filters."""
        mcp_settings = self.settings.mcp
        
        # If not all tools enabled, remove disabled ones
        if not mcp_settings.enable_all_tools:
            for tool_name in mcp_settings.disabled_tools:
                if self.registry.get_tool(tool_name):
                    self.registry.unregister(tool_name)
                    self.logger.info("Tool disabled by configuration", tool=tool_name)
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool manually.
        
        Args:
            tool: Tool to register
        """
        self.registry.register(tool)
    
    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        self.registry.unregister(tool_name)
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self.registry.get_tool(tool_name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """List all registered tools.
        
        Args:
            category: Filter by category (optional)
            
        Returns:
            List of tool names
        """
        return self.registry.list_tools(category)
    
    def list_categories(self) -> List[str]:
        """List all tool categories.
        
        Returns:
            List of category names
        """
        return self.registry.list_categories()
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """Get all tools in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of tools in the category
        """
        return self.registry.get_tools_by_category(category)
    
    def get_tool_schemas(self) -> List[ToolSchema]:
        """Get schemas for all registered tools.
        
        Returns:
            List of tool schemas
        """
        return self.registry.get_tool_schemas()
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name.
        
        Args:
            tool_name: Tool name
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        if not self._initialized:
            await self.initialize()
        
        return await self.registry.execute_tool(tool_name, **kwargs)
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get tool registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        tools = self.registry.list_tools()
        categories = self.registry.list_categories()
        
        category_counts = {}
        for category in categories:
            category_counts[category] = len(self.registry.list_tools(category))
        
        return {
            "total_tools": len(tools),
            "total_categories": len(categories),
            "category_counts": category_counts,
            "tools": tools,
            "categories": categories
        }
    
    def validate_tool_configuration(self) -> List[str]:
        """Validate tool configuration and return any issues.
        
        Returns:
            List of validation issues
        """
        issues = []
        mcp_settings = self.settings.mcp
        
        # Check for disabled tools that don't exist
        for disabled_tool in mcp_settings.disabled_tools:
            if not self.registry.get_tool(disabled_tool):
                issues.append(f"Disabled tool '{disabled_tool}' not found in registry")
        
        # Check for duplicate tool names (shouldn't happen but good to verify)
        tool_names = self.registry.list_tools()
        if len(tool_names) != len(set(tool_names)):
            issues.append("Duplicate tool names detected in registry")
        
        return issues
    
    async def reload_tools(self) -> None:
        """Reload all tools from modules."""
        self.logger.info("Reloading tools")
        
        # Clear existing tools
        for tool_name in self.registry.list_tools():
            self.registry.unregister(tool_name)
        
        # Re-initialize
        self._initialized = False
        await self.initialize()
        
        self.logger.info("Tools reloaded successfully")
    
    def export_tool_schemas(self, format: str = "json") -> Union[str, Dict]:
        """Export tool schemas in specified format.
        
        Args:
            format: Export format ("json", "yaml", "dict")
            
        Returns:
            Exported schemas in requested format
        """
        schemas = self.get_tool_schemas()
        schema_data = [schema.dict() for schema in schemas]
        
        if format == "dict":
            return schema_data
        elif format == "json":
            import json
            return json.dumps(schema_data, indent=2)
        elif format == "yaml":
            try:
                import yaml
                return yaml.dump(schema_data, default_flow_style=False)
            except ImportError:
                raise JinjaMCPError("PyYAML not installed, cannot export to YAML format")
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on tool registry.
        
        Returns:
            Health check results
        """
        if not self._initialized:
            return {
                "status": "unhealthy",
                "reason": "Tool registry not initialized"
            }
        
        try:
            # Basic validation
            issues = self.validate_tool_configuration()
            
            # Get statistics
            stats = self.get_tool_statistics()
            
            status = "healthy" if not issues else "warning"
            
            return {
                "status": status,
                "issues": issues,
                "statistics": stats,
                "initialized": self._initialized
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "reason": f"Health check failed: {str(e)}"
            } 