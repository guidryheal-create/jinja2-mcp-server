"""Base classes for MCP tools."""

import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from ..utils.logging import get_logger
from ..utils.exceptions import JinjaMCPError, ValidationError


class ToolResult(BaseModel):
    """Result returned by a tool execution."""
    
    success: bool = Field(description="Whether the tool execution was successful")
    result: Any = Field(description="The actual result data")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    execution_time: float = Field(description="Execution time in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""
    
    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type")
    description: str = Field(description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value if not required")


class ToolSchema(BaseModel):
    """Schema definition for a tool."""
    
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: List[ToolParameter] = Field(description="Tool parameters")
    return_type: str = Field(description="Return type description")
    category: str = Field(default="general", description="Tool category")
    version: str = Field(default="1.0.0", description="Tool version")


class BaseTool(ABC):
    """Base class for all MCP tools."""
    
    def __init__(self, name: str, description: str, category: str = "general"):
        """Initialize the base tool.
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category
        """
        self.name = name
        self.description = description
        self.category = category
        self.logger = get_logger(f"tool.{name}")
        self._schema: Optional[ToolSchema] = None
    
    @property
    def schema(self) -> ToolSchema:
        """Get the tool schema."""
        if self._schema is None:
            self._schema = self._generate_schema()
        return self._schema
    
    def _generate_schema(self) -> ToolSchema:
        """Generate tool schema from method signature."""
        # Get the execute method signature
        sig = inspect.signature(self.execute)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "context"):
                continue
                
            param_type = "string"  # Default type
            if param.annotation != inspect.Parameter.empty:
                param_type = self._get_type_string(param.annotation)
            
            required = param.default == inspect.Parameter.empty
            default_value = None if required else param.default
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter {param_name}",
                required=required,
                default=default_value
            ))
        
        return_type = "string"  # Default return type
        if sig.return_annotation != inspect.Signature.empty:
            return_type = self._get_type_string(sig.return_annotation)
        
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=parameters,
            return_type=return_type,
            category=self.category
        )
    
    def _get_type_string(self, annotation: Type) -> str:
        """Convert type annotation to string."""
        if annotation == str:
            return "string"
        elif annotation == int:
            return "integer"
        elif annotation == float:
            return "number"
        elif annotation == bool:
            return "boolean"
        elif annotation == dict or annotation == Dict:
            return "object"
        elif annotation == list or annotation == List:
            return "array"
        else:
            return str(annotation).replace("typing.", "")
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            JinjaMCPError: If execution fails
        """
        pass
    
    async def run(self, **kwargs) -> ToolResult:
        """Run the tool and return a structured result.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with execution details
        """
        start_time = time.time()
        
        try:
            self.logger.debug("Tool execution started", tool=self.name, params=list(kwargs.keys()))
            
            # Validate parameters
            self._validate_parameters(kwargs)
            
            # Execute the tool
            result = await self.execute(**kwargs)
            
            execution_time = time.time() - start_time
            
            self.logger.debug(
                "Tool execution completed", 
                tool=self.name, 
                execution_time=execution_time
            )
            
            return ToolResult(
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={"tool_name": self.name, "category": self.category}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(
                "Tool execution failed",
                tool=self.name,
                error=error_msg,
                execution_time=execution_time
            )
            
            return ToolResult(
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time,
                metadata={"tool_name": self.name, "category": self.category}
            )
    
    def _validate_parameters(self, params: Dict[str, Any]) -> None:
        """Validate tool parameters against schema.
        
        Args:
            params: Parameters to validate
            
        Raises:
            ValidationError: If validation fails
        """
        schema = self.schema
        
        # Check required parameters
        for param in schema.parameters:
            if param.required and param.name not in params:
                raise ValidationError(
                    f"Required parameter '{param.name}' missing for tool '{self.name}'",
                    field_name=param.name,
                    details={"tool": self.name, "required_params": [p.name for p in schema.parameters if p.required]}
                )
        
        # Check parameter types (basic validation)
        for param_name, param_value in params.items():
            param_def = next((p for p in schema.parameters if p.name == param_name), None)
            if param_def:
                if not self._validate_parameter_type(param_value, param_def.type):
                    raise ValidationError(
                        f"Parameter '{param_name}' has invalid type for tool '{self.name}'",
                        field_name=param_name,
                        field_value=str(type(param_value)),
                        details={"expected_type": param_def.type, "actual_type": type(param_value).__name__}
                    )
    
    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type.
        
        Args:
            value: Parameter value
            expected_type: Expected type string
            
        Returns:
            True if type is valid
        """
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "object":
            return isinstance(value, dict)
        elif expected_type == "array":
            return isinstance(value, list)
        else:
            # For complex types, just return True
            return True


class ToolRegistry:
    """Registry for managing MCP tools."""
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
        self.logger = get_logger(__name__)
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool.
        
        Args:
            tool: Tool to register
            
        Raises:
            ValueError: If tool name already exists
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        
        self._tools[tool.name] = tool
        
        # Add to category
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)
        
        self.logger.info("Tool registered", tool=tool.name, category=tool.category)
    
    def unregister(self, tool_name: str) -> None:
        """Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            del self._tools[tool_name]
            
            # Remove from category
            if tool.category in self._categories:
                self._categories[tool.category].remove(tool_name)
                if not self._categories[tool.category]:
                    del self._categories[tool.category]
            
            self.logger.info("Tool unregistered", tool=tool_name)
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """List all registered tools.
        
        Args:
            category: Filter by category (optional)
            
        Returns:
            List of tool names
        """
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """List all tool categories.
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """Get all tools in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of tools in the category
        """
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names]
    
    def get_tool_schemas(self) -> List[ToolSchema]:
        """Get schemas for all registered tools.
        
        Returns:
            List of tool schemas
        """
        return [tool.schema for tool in self._tools.values()]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name.
        
        Args:
            tool_name: Tool name
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        return await tool.run(**kwargs) 