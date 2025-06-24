"""Jinja2 environment manager for MCP server."""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2
from jinja2 import Environment, FileSystemLoader, BaseLoader, select_autoescape, meta

from ..config.settings import JinjaSettings
from ..utils import get_logger
from ..utils.exceptions import TemplateError, RenderError, ValidationError


class JinjaEnvironmentManager:
    """Manager for Jinja2 environment and template operations."""
    
    def __init__(self, settings: JinjaSettings):
        """Initialize the Jinja environment manager.
        
        Args:
            settings: Jinja configuration settings
        """
        self.settings = settings
        self.logger = get_logger(__name__)
        self.environment: Optional[Environment] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Jinja2 environment."""
        if self._initialized:
            return
        
        self.logger.info("Initializing Jinja2 environment")
        
        try:
            # Setup template loader
            loader = self._create_loader()
            
            # Create Jinja2 environment
            self.environment = Environment(
                loader=loader,
                autoescape=select_autoescape(['html', 'xml']) if self.settings.autoescape else False,
                auto_reload=self.settings.auto_reload,
                cache_size=self.settings.cache_size,
                extensions=self.settings.extensions
            )
            
            # Configure environment
            self._configure_environment()
            
            self._initialized = True
            self.logger.info("Jinja2 environment initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize Jinja2 environment", error=str(e))
            raise TemplateError(f"Environment initialization failed: {e}")
    
    def _create_loader(self) -> BaseLoader:
        """Create Jinja2 template loader.
        
        Returns:
            Configured template loader
        """
        if self.settings.template_dirs:
            # Use filesystem loader for template directories
            search_paths = [str(path) for path in self.settings.template_dirs]
            self.logger.debug("Using FileSystemLoader", paths=search_paths)
            return FileSystemLoader(search_paths)
        else:
            # Use base loader for string templates only
            self.logger.debug("Using BaseLoader for string templates")
            return BaseLoader()
    
    def _configure_environment(self) -> None:
        """Configure the Jinja2 environment with custom settings."""
        if not self.environment:
            return
        
        # Add custom filters
        for filter_name, filter_path in self.settings.custom_filters.items():
            try:
                # Import and register custom filter
                module_path, func_name = filter_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[func_name])
                filter_func = getattr(module, func_name)
                self.environment.filters[filter_name] = filter_func
                
                self.logger.debug("Custom filter registered", filter=filter_name)
                
            except Exception as e:
                self.logger.warning(
                    "Failed to register custom filter",
                    filter=filter_name,
                    path=filter_path,
                    error=str(e)
                )
        
        # Configure globals (if any security settings allow)
        # This would be expanded in Phase 2 with security considerations
        
        self.logger.debug("Jinja2 environment configured")
    
    async def render_template(
        self, 
        template_content: str, 
        variables: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render a template string with variables.
        
        Args:
            template_content: Template content as string
            variables: Variables to pass to template
            options: Additional rendering options
            
        Returns:
            Rendered template content
            
        Raises:
            RenderError: If rendering fails
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.environment:
            raise RenderError("Jinja2 environment not initialized")
        
        start_time = time.time()
        
        try:
            self.logger.debug(
                "Rendering template",
                template_size=len(template_content),
                variables_count=len(variables)
            )
            
            # Check template size
            if len(template_content.encode('utf-8')) > self.settings.max_template_size:
                raise RenderError(
                    f"Template too large: {len(template_content)} > {self.settings.max_template_size} bytes"
                )
            
            # Create template from string
            template = self.environment.from_string(template_content)
            
            # Render with timeout
            result = await self._render_with_timeout(template, variables)
            
            render_time = time.time() - start_time
            
            self.logger.debug(
                "Template rendered successfully",
                render_time=render_time,
                result_size=len(result)
            )
            
            return result
            
        except jinja2.TemplateError as e:
            render_time = time.time() - start_time
            error_msg = f"Template rendering failed: {str(e)}"
            
            self.logger.error(
                "Template rendering error",
                error=error_msg,
                render_time=render_time
            )
            
            raise RenderError(error_msg, details={
                "template_error": str(e),
                "error_type": type(e).__name__,
                "render_time": render_time
            })
        
        except Exception as e:
            render_time = time.time() - start_time
            error_msg = f"Unexpected error during rendering: {str(e)}"
            
            self.logger.error(
                "Unexpected rendering error",
                error=error_msg,
                render_time=render_time
            )
            
            raise RenderError(error_msg, details={
                "original_error": str(e),
                "error_type": type(e).__name__,
                "render_time": render_time
            })
    
    async def render_template_file(
        self,
        template_path: str,
        variables: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render a template file with variables.
        
        Args:
            template_path: Path to template file
            variables: Variables to pass to template
            options: Additional rendering options
            
        Returns:
            Rendered template content
            
        Raises:
            RenderError: If rendering fails
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.environment:
            raise RenderError("Jinja2 environment not initialized")
        
        start_time = time.time()
        
        try:
            self.logger.debug(
                "Rendering template file",
                template_path=template_path,
                variables_count=len(variables)
            )
            
            # Load template from file
            template = self.environment.get_template(template_path)
            
            # Render with timeout
            result = await self._render_with_timeout(template, variables)
            
            render_time = time.time() - start_time
            
            self.logger.debug(
                "Template file rendered successfully",
                template_path=template_path,
                render_time=render_time,
                result_size=len(result)
            )
            
            return result
            
        except jinja2.TemplateNotFound as e:
            error_msg = f"Template file not found: {template_path}"
            self.logger.error("Template file not found", template_path=template_path)
            raise RenderError(error_msg, details={"template_path": template_path})
        
        except jinja2.TemplateError as e:
            render_time = time.time() - start_time
            error_msg = f"Template file rendering failed: {str(e)}"
            
            self.logger.error(
                "Template file rendering error",
                template_path=template_path,
                error=error_msg,
                render_time=render_time
            )
            
            raise RenderError(error_msg, details={
                "template_path": template_path,
                "template_error": str(e),
                "error_type": type(e).__name__,
                "render_time": render_time
            })
        
        except Exception as e:
            render_time = time.time() - start_time
            error_msg = f"Unexpected error during file rendering: {str(e)}"
            
            self.logger.error(
                "Unexpected file rendering error",
                template_path=template_path,
                error=error_msg,
                render_time=render_time
            )
            
            raise RenderError(error_msg, details={
                "template_path": template_path,
                "original_error": str(e),
                "error_type": type(e).__name__,
                "render_time": render_time
            })
    
    async def _render_with_timeout(
        self, 
        template: jinja2.Template, 
        variables: Dict[str, Any]
    ) -> str:
        """Render template with timeout protection.
        
        Args:
            template: Jinja2 template object
            variables: Variables to pass to template
            
        Returns:
            Rendered content
            
        Raises:
            RenderError: If rendering times out or fails
        """
        try:
            # Run rendering in executor to allow timeout
            loop = asyncio.get_event_loop()
            
            result = await asyncio.wait_for(
                loop.run_in_executor(None, template.render, variables),
                timeout=self.settings.max_render_time
            )
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Template rendering timed out after {self.settings.max_render_time} seconds"
            self.logger.error("Template rendering timeout", timeout=self.settings.max_render_time)
            raise RenderError(error_msg, details={"timeout": self.settings.max_render_time})
    
    async def validate_template(self, template_content: str) -> Dict[str, Any]:
        """Validate template syntax and analyze structure.
        
        Args:
            template_content: Template content to validate
            
        Returns:
            Validation result with details
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.environment:
            raise ValidationError("Jinja2 environment not initialized")
        
        try:
            self.logger.debug("Validating template", template_size=len(template_content))
            
            # Parse template to check syntax
            ast = self.environment.parse(template_content)
            
            # Basic analysis
            variables_used = list(meta.find_undeclared_variables(ast))
            
            result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "variables_used": variables_used,
                "filters_used": [],  # TODO: Implement in Phase 2
                "tests_used": [],    # TODO: Implement in Phase 2
                "complexity_score": len(variables_used)  # Simple metric for now
            }
            
            self.logger.debug("Template validation completed", result=result)
            return result
            
        except jinja2.TemplateError as e:
            error_msg = str(e)
            self.logger.warning("Template validation failed", error=error_msg)
            
            return {
                "valid": False,
                "errors": [error_msg],
                "warnings": [],
                "variables_used": [],
                "filters_used": [],
                "tests_used": [],
                "complexity_score": 0
            }
        
        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            self.logger.error("Unexpected validation error", error=error_msg)
            raise ValidationError(error_msg, details={"original_error": str(e)})
    
    async def list_filters(self) -> Dict[str, Any]:
        """List available Jinja2 filters.
        
        Returns:
            Dictionary with filter information
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.environment:
            raise ValidationError("Jinja2 environment not initialized")
        
        try:
            # Get all available filters
            builtin_filters = list(self.environment.filters.keys())
            custom_filters = list(self.settings.custom_filters.keys())
            
            result = {
                "builtin_filters": sorted(builtin_filters),
                "custom_filters": sorted(custom_filters),
                "total_count": len(builtin_filters)
            }
            
            self.logger.debug("Listed filters", total_count=result["total_count"])
            return result
            
        except Exception as e:
            error_msg = f"Failed to list filters: {str(e)}"
            self.logger.error("Filter listing error", error=error_msg)
            raise ValidationError(error_msg, details={"original_error": str(e)})
    
    async def get_template_info(self, template_content: str) -> Dict[str, Any]:
        """Get detailed information about a template.
        
        Args:
            template_content: Template content to analyze
            
        Returns:
            Template information and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Validate first
            validation_result = await self.validate_template(template_content)
            
            # Additional analysis
            info = {
                "template_size": len(template_content),
                "template_lines": len(template_content.splitlines()),
                "validation": validation_result,
                "estimated_render_time_ms": 0.5,  # Placeholder
                "blocks": [],     # TODO: Implement in Phase 2
                "includes": [],   # TODO: Implement in Phase 2
                "extends": None,  # TODO: Implement in Phase 2
            }
            
            self.logger.debug("Template info generated", template_size=info["template_size"])
            return info
            
        except Exception as e:
            error_msg = f"Failed to get template info: {str(e)}"
            self.logger.error("Template info error", error=error_msg)
            raise ValidationError(error_msg, details={"original_error": str(e)})
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.environment:
            # Clear template cache
            self.environment.cache.clear()
            
        self._initialized = False
        self.logger.info("Jinja2 environment cleaned up") 