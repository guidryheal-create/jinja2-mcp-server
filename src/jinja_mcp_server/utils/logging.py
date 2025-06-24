"""Logging configuration for Jinja MCP Server."""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog.types import Processor

from ..config import LoggingSettings


def setup_logging(settings: LoggingSettings) -> None:
    """Setup logging configuration based on settings."""
    
    # Configure standard logging
    logging_level = getattr(logging, settings.level.upper())
    
    # Create formatter
    formatter = logging.Formatter(settings.format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if settings.log_file:
        log_file = Path(settings.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure structlog if enabled
    if settings.enable_structlog:
        configure_structlog(settings)


def configure_structlog(settings: LoggingSettings) -> None:
    """Configure structlog for structured logging."""
    
    # Determine processors based on environment
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    # Add processor for exceptions
    processors.append(structlog.processors.format_exc_info)
    
    # Configure output format
    if settings.level.upper() == "DEBUG":
        # Pretty output for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger instance for this class."""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls with parameters and results."""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(
            "Function called",
            function=func.__name__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        try:
            result = func(*args, **kwargs)
            logger.debug(
                "Function completed",
                function=func.__name__,
                result_type=type(result).__name__
            )
            return result
        except Exception as e:
            logger.error(
                "Function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls with parameters and results."""
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(
            "Async function called",
            function=func.__name__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(
                "Async function completed",
                function=func.__name__,
                result_type=type(result).__name__
            )
            return result
        except Exception as e:
            logger.error(
                "Async function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    return wrapper


class ContextualLogger:
    """Logger with contextual information."""
    
    def __init__(self, name: str, **context):
        self._logger = get_logger(name)
        self._context = context
    
    def bind(self, **context):
        """Bind additional context to logger."""
        new_context = {**self._context, **context}
        return ContextualLogger(self._logger.name, **new_context)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._logger.debug(message, **self._context, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._logger.info(message, **self._context, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._logger.warning(message, **self._context, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._logger.error(message, **self._context, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._logger.critical(message, **self._context, **kwargs) 