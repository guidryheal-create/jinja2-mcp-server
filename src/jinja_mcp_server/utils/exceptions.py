"""Custom exceptions for Jinja MCP Server."""

from typing import Any, Dict, Optional


class JinjaMCPError(Exception):
    """Base exception for Jinja MCP Server errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class TemplateError(JinjaMCPError):
    """Exception raised for template-related errors."""
    
    def __init__(
        self, 
        message: str, 
        template_name: Optional[str] = None,
        line_number: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        # Prepare details dictionary
        error_details = details.copy() if details else {}
        if template_name:
            error_details["template_name"] = template_name
        if line_number:
            error_details["line_number"] = line_number
        
        super().__init__(message, error_code=error_code, details=error_details)
        self.template_name = template_name
        self.line_number = line_number


class RenderError(TemplateError):
    """Exception raised during template rendering."""
    
    def __init__(
        self, 
        message: str, 
        template_name: Optional[str] = None,
        context_vars: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        # Prepare details dictionary
        error_details = details.copy() if details else {}
        if context_vars:
            # Don't include sensitive data in error details
            safe_vars = {
                k: type(v).__name__ for k, v in context_vars.items()
                if not k.startswith("_")
            }
            error_details["context_types"] = safe_vars
        
        super().__init__(message, template_name=template_name, error_code=error_code, details=error_details)
        self.context_vars = context_vars


class ValidationError(JinjaMCPError):
    """Exception raised for validation errors."""
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if field_name:
            details["field_name"] = field_name
        if field_value is not None:
            details["field_value"] = str(field_value)
        
        super().__init__(message, details=details, **kwargs)
        self.field_name = field_name
        self.field_value = field_value


class SecurityError(JinjaMCPError):
    """Exception raised for security-related errors."""
    
    def __init__(
        self, 
        message: str, 
        security_rule: Optional[str] = None,
        attempted_action: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if security_rule:
            details["security_rule"] = security_rule
        if attempted_action:
            details["attempted_action"] = attempted_action
        
        super().__init__(message, details=details, **kwargs)
        self.security_rule = security_rule
        self.attempted_action = attempted_action


class ConfigurationError(JinjaMCPError):
    """Exception raised for configuration-related errors."""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        if config_value is not None:
            details["config_value"] = str(config_value)
        
        super().__init__(message, details=details, **kwargs)
        self.config_key = config_key
        self.config_value = config_value


class TimeoutError(JinjaMCPError):
    """Exception raised when operations exceed time limits."""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        
        super().__init__(message, details=details, **kwargs)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class FileSizeError(JinjaMCPError):
    """Exception raised when files exceed size limits."""
    
    def __init__(
        self, 
        message: str, 
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        max_size: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if file_path:
            details["file_path"] = file_path
        if file_size:
            details["file_size"] = file_size
        if max_size:
            details["max_size"] = max_size
        
        super().__init__(message, details=details, **kwargs)
        self.file_path = file_path
        self.file_size = file_size
        self.max_size = max_size 