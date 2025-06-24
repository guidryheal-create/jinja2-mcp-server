"""Configuration settings for Jinja MCP Server."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, ConfigDict


class JinjaSettings(BaseModel):
    """Jinja2 engine configuration settings."""
    
    # Template directories
    template_dirs: List[Path] = Field(
        default_factory=lambda: [Path("templates")],
        description="List of directories to search for templates"
    )
    
    # Security settings
    autoescape: bool = Field(
        default=True,
        description="Enable automatic HTML escaping for security"
    )
    
    # Performance settings
    cache_size: int = Field(
        default=400,
        ge=0,
        description="Template cache size (0 to disable caching)"
    )
    
    auto_reload: bool = Field(
        default=True,
        description="Automatically reload templates when changed"
    )
    
    # Template rendering limits
    max_template_size: int = Field(
        default=1024 * 1024,  # 1MB
        ge=1024,
        description="Maximum template size in bytes"
    )
    
    max_render_time: float = Field(
        default=30.0,
        ge=0.1,
        description="Maximum template rendering time in seconds"
    )
    
    # Custom filters and extensions
    custom_filters: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom Jinja2 filters (name -> import path)"
    )
    
    extensions: List[str] = Field(
        default_factory=list,
        description="Jinja2 extensions to load"
    )
    
    @field_validator("template_dirs", mode="before")
    @classmethod
    def validate_template_dirs(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, (str, Path)):
            v = [v]
        return [Path(path) for path in v]


class SecuritySettings(BaseModel):
    """Security configuration settings."""
    
    # Template execution limits
    max_loop_iterations: int = Field(
        default=10000,
        ge=1,
        description="Maximum loop iterations in templates"
    )
    
    max_recursion_depth: int = Field(
        default=100,
        ge=1,
        description="Maximum recursion depth in templates"
    )
    
    # Allowed/blocked features
    allow_file_access: bool = Field(
        default=False,
        description="Allow templates to access files"
    )
    
    allowed_globals: List[str] = Field(
        default_factory=list,
        description="List of allowed global variables/functions"
    )
    
    blocked_globals: List[str] = Field(
        default_factory=lambda: ["__import__", "open", "eval", "exec"],
        description="List of blocked global variables/functions"
    )


class LoggingSettings(BaseModel):
    """Logging configuration settings."""
    
    level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level"
    )
    
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    
    enable_structlog: bool = Field(
        default=True,
        description="Enable structured logging with structlog"
    )
    
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (None for console only)"
    )


class MCPSettings(BaseModel):
    """MCP server configuration settings."""
    
    name: str = Field(
        default="jinja-mcp-server",
        description="MCP server name"
    )
    
    version: str = Field(
        default="0.1.0",
        description="MCP server version"
    )
    
    description: str = Field(
        default="Jinja2 template rendering server",
        description="MCP server description"
    )
    
    # Transport settings
    stdio: bool = Field(
        default=True,
        description="Enable stdio transport"
    )
    
    # Tool settings
    enable_all_tools: bool = Field(
        default=True,
        description="Enable all available tools"
    )
    
    disabled_tools: List[str] = Field(
        default_factory=list,
        description="List of disabled tool names"
    )


class Settings(BaseModel):
    """Main configuration settings for Jinja MCP Server."""
    
    # Environment
    environment: str = Field(
        default="development",
        pattern=r"^(development|testing|production)$",
        description="Application environment"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Sub-configurations
    jinja: JinjaSettings = Field(default_factory=JinjaSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    
    @field_validator("debug", mode="before")
    @classmethod
    def set_debug_from_env(cls, v):
        """Set debug mode from environment variable."""
        if os.getenv("DEBUG", "").lower() in ("true", "1", "yes", "on"):
            return True
        return v
    
    @field_validator("environment", mode="before")
    @classmethod
    def set_environment_from_env(cls, v):
        """Set environment from environment variable."""
        return os.getenv("ENVIRONMENT", v)
    
    model_config = ConfigDict(
        env_prefix="JINJA_MCP_",
        env_nested_delimiter="__",
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def load_settings_from_file(file_path: Union[str, Path]) -> Settings:
    """Load settings from a JSON or YAML file."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Settings file not found: {file_path}")
    
    if file_path.suffix.lower() == ".json":
        import json
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif file_path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required to load YAML settings files")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported settings file format: {file_path.suffix}")
    
    return Settings(**data) 