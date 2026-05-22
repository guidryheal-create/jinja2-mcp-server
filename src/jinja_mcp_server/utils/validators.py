"""Validation utilities for Jinja MCP Server."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .exceptions import ValidationError
from .logging import get_logger


def _logger():
    return get_logger(__name__)


def validate_json_params(params: Union[str, Dict[str, Any]], max_size: int = 1024 * 1024) -> Dict[str, Any]:
    """Validate and parse JSON parameters.
    
    Args:
        params: JSON string or dictionary
        max_size: Maximum size of JSON string in bytes
        
    Returns:
        Parsed dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    _logger().debug("Validating JSON parameters", params_type=type(params).__name__)
    
    # Handle string input
    if isinstance(params, str):
        # Check size
        if len(params.encode('utf-8')) > max_size:
            raise ValidationError(
                f"JSON parameters too large: {len(params)} > {max_size} bytes",
                field_name="params",
                field_value=f"<{len(params)} bytes>",
                details={"max_size": max_size, "actual_size": len(params)}
            )
        
        # Parse JSON
        try:
            params = json.loads(params)
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Invalid JSON format: {e}",
                field_name="params",
                field_value=params[:100] + "..." if len(params) > 100 else params,
                details={"json_error": str(e)}
            )
    
    # Ensure it's a dictionary
    if not isinstance(params, dict):
        raise ValidationError(
            f"Parameters must be a dictionary, got {type(params).__name__}",
            field_name="params",
            field_value=str(type(params)),
            details={"expected_type": "dict", "actual_type": type(params).__name__}
        )
    
    # Validate parameter names
    for key in params.keys():
        if not isinstance(key, str):
            raise ValidationError(
                f"Parameter keys must be strings, got {type(key).__name__}",
                field_name="params.key",
                field_value=str(key),
                details={"key": str(key), "key_type": type(key).__name__}
            )
        
        # Check for valid variable names
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
            raise ValidationError(
                f"Invalid parameter name: {key}. Must be a valid Python identifier",
                field_name="params.key",
                field_value=key,
                details={"pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$"}
            )
        
        # Check for reserved names
        if key.startswith('__') and key.endswith('__'):
            raise ValidationError(
                f"Parameter name cannot be a dunder name: {key}",
                field_name="params.key",
                field_value=key,
                details={"reason": "dunder_name"}
            )
    
    # Validate parameter values
    _validate_parameter_values(params)
    
    _logger().debug("JSON parameters validated successfully", param_count=len(params))
    return params


def _validate_parameter_values(
    params: Dict[str, Any], 
    path: str = "", 
    max_depth: int = 10, 
    current_depth: int = 0
) -> None:
    """Recursively validate parameter values."""
    
    if current_depth > max_depth:
        raise ValidationError(
            f"Parameter nesting too deep: {current_depth} > {max_depth}",
            field_name=path,
            details={"max_depth": max_depth, "current_depth": current_depth}
        )
    
    for key, value in params.items():
        current_path = f"{path}.{key}" if path else key
        
        # Check for dangerous types
        if callable(value):
            raise ValidationError(
                f"Callable objects not allowed in parameters: {current_path}",
                field_name=current_path,
                field_value=str(type(value)),
                details={"value_type": type(value).__name__}
            )
        
        # Recursively validate nested dictionaries
        if isinstance(value, dict):
            _validate_parameter_values(value, current_path, max_depth, current_depth + 1)
        
        # Validate lists
        elif isinstance(value, list):
            _validate_list_values(value, current_path, max_depth, current_depth + 1)


def _validate_list_values(
    values: List[Any], 
    path: str, 
    max_depth: int, 
    current_depth: int
) -> None:
    """Validate list values recursively."""
    
    if current_depth > max_depth:
        raise ValidationError(
            f"Parameter nesting too deep: {current_depth} > {max_depth}",
            field_name=path,
            details={"max_depth": max_depth, "current_depth": current_depth}
        )
    
    for i, value in enumerate(values):
        current_path = f"{path}[{i}]"
        
        # Check for dangerous types
        if callable(value):
            raise ValidationError(
                f"Callable objects not allowed in parameters: {current_path}",
                field_name=current_path,
                field_value=str(type(value)),
                details={"value_type": type(value).__name__}
            )
        
        # Recursively validate nested structures
        if isinstance(value, dict):
            _validate_parameter_values(value, current_path, max_depth, current_depth + 1)
        elif isinstance(value, list):
            _validate_list_values(value, current_path, max_depth, current_depth + 1)


def validate_template_content(
    content: str, 
    template_name: Optional[str] = None,
    max_size: int = 1024 * 1024
) -> str:
    """Validate template content.
    
    Args:
        content: Template content string
        template_name: Optional template name for error reporting
        max_size: Maximum template size in bytes
        
    Returns:
        Validated template content
        
    Raises:
        ValidationError: If validation fails
    """
    _logger().debug(
        "Validating template content", 
        template_name=template_name,
        content_length=len(content)
    )
    
    # Check if content is a string
    if not isinstance(content, str):
        raise ValidationError(
            f"Template content must be a string, got {type(content).__name__}",
            field_name="template_content",
            field_value=str(type(content)),
            details={
                "template_name": template_name,
                "expected_type": "str",
                "actual_type": type(content).__name__
            }
        )
    
    # Check size
    content_bytes = content.encode('utf-8')
    if len(content_bytes) > max_size:
        raise ValidationError(
            f"Template content too large: {len(content_bytes)} > {max_size} bytes",
            field_name="template_content",
            field_value=f"<{len(content_bytes)} bytes>",
            details={
                "template_name": template_name,
                "max_size": max_size,
                "actual_size": len(content_bytes)
            }
        )
    
    # Check for null bytes (potential binary content)
    if '\x00' in content:
        raise ValidationError(
            "Template content contains null bytes (binary content not allowed)",
            field_name="template_content",
            details={"template_name": template_name}
        )
    
    # Basic Jinja2 syntax validation
    _validate_jinja2_syntax(content, template_name)
    
    _logger().debug("Template content validated successfully", template_name=template_name)
    return content


def _validate_jinja2_syntax(content: str, template_name: Optional[str] = None) -> None:
    """Basic Jinja2 syntax validation."""
    
    # Check for balanced braces
    open_var = content.count('{{')
    close_var = content.count('}}')
    if open_var != close_var:
        raise ValidationError(
            f"Unbalanced variable delimiters: {open_var} '{{{{' vs {close_var} '}}}}'",
            field_name="template_syntax",
            details={
                "template_name": template_name,
                "open_count": open_var,
                "close_count": close_var
            }
        )
    
    open_block = content.count('{%')
    close_block = content.count('%}')
    if open_block != close_block:
        raise ValidationError(
            f"Unbalanced block delimiters: {open_block} '{{%' vs {close_block} '%}}'",
            field_name="template_syntax",
            details={
                "template_name": template_name,
                "open_count": open_block,
                "close_count": close_block
            }
        )
    
    open_comment = content.count('{#')
    close_comment = content.count('#}')
    if open_comment != close_comment:
        raise ValidationError(
            f"Unbalanced comment delimiters: {open_comment} '{{#' vs {close_comment} '#}}'",
            field_name="template_syntax",
            details={
                "template_name": template_name,
                "open_count": open_comment,
                "close_count": close_comment
            }
        )


def validate_template_name(name: str) -> str:
    """Validate template name.
    
    Args:
        name: Template name
        
    Returns:
        Validated template name
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(name, str):
        raise ValidationError(
            f"Template name must be a string, got {type(name).__name__}",
            field_name="template_name",
            field_value=str(type(name)),
            details={"expected_type": "str", "actual_type": type(name).__name__}
        )
    
    if not name.strip():
        raise ValidationError(
            "Template name cannot be empty",
            field_name="template_name",
            field_value=name
        )
    
    # Check for path traversal attempts
    if '..' in name or name.startswith('/') or '\\' in name:
        raise ValidationError(
            f"Invalid template name (path traversal detected): {name}",
            field_name="template_name",
            field_value=name,
            details={"reason": "path_traversal"}
        )
    
    # Check length
    if len(name) > 255:
        raise ValidationError(
            f"Template name too long: {len(name)} > 255 characters",
            field_name="template_name",
            field_value=name[:50] + "..." if len(name) > 50 else name,
            details={"max_length": 255, "actual_length": len(name)}
        )
    
    return name.strip()


def validate_file_path(file_path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """Validate file path for security and existence.
    
    Args:
        file_path: File path to validate
        base_dir: Base directory to restrict access to
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If validation fails
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    # Check for path traversal
    try:
        resolved_path = file_path.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(
            f"Invalid file path: {e}",
            field_name="file_path",
            field_value=str(file_path),
            details={"error": str(e)}
        )
    
    # Check if path is within base directory (if specified)
    if base_dir:
        base_resolved = base_dir.resolve()
        try:
            resolved_path.relative_to(base_resolved)
        except ValueError:
            raise ValidationError(
                f"File path outside allowed directory: {resolved_path}",
                field_name="file_path",
                field_value=str(file_path),
                details={
                    "base_dir": str(base_resolved),
                    "resolved_path": str(resolved_path)
                }
            )
    
    return resolved_path 