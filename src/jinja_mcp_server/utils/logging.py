"""Logging configuration for Jinja MCP Server."""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog.types import Processor

from ..config import LoggingSettings


def _bootstrap_structlog() -> None:
    """Use stdlib logging (stderr) instead of structlog's default PrintLogger (stdout)."""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


_bootstrap_structlog()


def _stream_is_stdout(stream: object) -> bool:
    return stream in (sys.stdout, sys.__stdout__)


def _handler_writes_stdout(handler: logging.Handler) -> bool:
    return isinstance(handler, logging.StreamHandler) and _stream_is_stdout(handler.stream)


def apply_stdio_log_policy() -> None:
    """Ensure nothing is logged to stdout (MCP stdio JSON-RPC channel).

    Call after FastMCP initializes, which may reconfigure logging.
    """
    logging.disable(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.WARNING)

    for logger in [root, *[
        logging.getLogger(name)
        for name in list(logging.root.manager.loggerDict)
    ]]:
        if not isinstance(logger, logging.Logger):
            continue
        logger.setLevel(logging.WARNING)
        for handler in list(logger.handlers):
            if _handler_writes_stdout(handler):
                logger.removeHandler(handler)

    for handler in list(root.handlers):
        if _handler_writes_stdout(handler):
            root.removeHandler(handler)

    if not any(
        isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
        for h in root.handlers
    ):
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.WARNING)
        stderr_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root.addHandler(stderr_handler)


def setup_logging(
    settings: LoggingSettings,
    *,
    transport: str | None = None,
) -> None:
    """Setup logging configuration based on settings.

    For MCP stdio transport, logs must go to stderr only — stdout is reserved
    for JSON-RPC messages.
    """
    level_name = settings.level.upper()
    use_structlog = settings.enable_structlog
    if transport == "stdio":
        # MCP stdio: stdout is JSON-RPC only — keep stderr quiet and non-JSON
        level_name = "WARNING"
        use_structlog = False

    logging_level = getattr(logging, level_name)

    formatter = logging.Formatter(settings.format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stderr)
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
    
    if transport == "stdio":
        apply_stdio_log_policy()

    if use_structlog:
        configure_structlog(settings, level_name=level_name, transport=transport)
    else:
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging_level),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=False,
        )


def configure_structlog(
    settings: LoggingSettings,
    *,
    level_name: str,
    transport: str | None = None,
) -> None:
    """Configure structlog; output always goes through stdlib logging (stderr)."""
    pre_chain: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if transport == "stdio" or level_name == "DEBUG":
        renderer: Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=pre_chain + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level_name)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    structlog_formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=pre_chain,
    )

    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stderr:
            handler.setFormatter(structlog_formatter)


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