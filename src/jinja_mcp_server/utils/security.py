"""Security utilities for Jinja MCP Server."""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..config import SecuritySettings
from .exceptions import SecurityError
from .logging import LoggerMixin


class SecurityManager(LoggerMixin):
    """Security manager for template rendering and execution."""
    
    def __init__(self, settings: SecuritySettings):
        self.settings = settings
        self._blocked_patterns = self._compile_blocked_patterns()
        self._allowed_globals = set(settings.allowed_globals)
        self._blocked_globals = set(settings.blocked_globals)
    
    def _compile_blocked_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for blocked template constructs."""
        patterns = [
            # Dangerous function calls
            r'__import__\s*\(',
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            r'open\s*\(',
            r'file\s*\(',
            
            # Dangerous attribute access
            r'\.__[a-zA-Z_]',  # Dunder attributes
            r'\.func_globals',
            r'\.func_code',
            r'\.gi_frame',
            r'\.f_globals',
            r'\.f_locals',
            
            # System access
            r'import\s+os',
            r'import\s+sys',
            r'import\s+subprocess',
            r'from\s+os',
            r'from\s+sys',
            r'from\s+subprocess',
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def validate_template_content(self, content: str, template_name: Optional[str] = None) -> None:
        """Validate template content for security issues."""
        self.logger.debug(
            "Validating template content",
            template_name=template_name,
            content_length=len(content)
        )
        
        # Check for blocked patterns
        for pattern in self._blocked_patterns:
            if pattern.search(content):
                raise SecurityError(
                    f"Template contains blocked pattern: {pattern.pattern}",
                    security_rule="blocked_pattern",
                    attempted_action=f"pattern_match:{pattern.pattern}",
                    details={"template_name": template_name}
                )
        
        # Check template size
        if len(content.encode('utf-8')) > self.settings.max_template_size:
            raise SecurityError(
                f"Template size exceeds limit: {len(content)} > {self.settings.max_template_size}",
                security_rule="max_template_size",
                details={
                    "template_name": template_name,
                    "size": len(content),
                    "max_size": self.settings.max_template_size
                }
            )
        
        # Additional AST-based validation for Python expressions
        self._validate_template_expressions(content, template_name)
    
    def _validate_template_expressions(self, content: str, template_name: Optional[str] = None) -> None:
        """Validate Python expressions in template using AST parsing."""
        # Extract potential Python expressions from Jinja2 syntax
        # This is a simplified approach - real implementation would need proper Jinja2 parsing
        
        # Look for {{ }} expressions
        expression_pattern = r'\{\{\s*([^}]+)\s*\}\}'
        expressions = re.findall(expression_pattern, content)
        
        for expr in expressions:
            self._validate_expression(expr.strip(), template_name)
    
    def _validate_expression(self, expression: str, template_name: Optional[str] = None) -> None:
        """Validate a single Python expression."""
        try:
            # Parse the expression as Python AST
            tree = ast.parse(expression, mode='eval')
            
            # Check for dangerous node types
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    raise SecurityError(
                        f"Import statements not allowed in templates: {expression}",
                        security_rule="no_imports",
                        attempted_action=f"import:{expression}",
                        details={"template_name": template_name}
                    )
                
                if isinstance(node, ast.ImportFrom):
                    raise SecurityError(
                        f"Import statements not allowed in templates: {expression}",
                        security_rule="no_imports",
                        attempted_action=f"import_from:{expression}",
                        details={"template_name": template_name}
                    )
                
                if isinstance(node, ast.Call):
                    # Check function calls
                    func_name = self._get_function_name(node.func)
                    if func_name in self._blocked_globals:
                        raise SecurityError(
                            f"Blocked function call: {func_name}",
                            security_rule="blocked_function",
                            attempted_action=f"call:{func_name}",
                            details={"template_name": template_name}
                        )
                
                if isinstance(node, ast.Attribute):
                    # Check attribute access
                    attr_name = node.attr
                    if attr_name.startswith('__') and attr_name.endswith('__'):
                        raise SecurityError(
                            f"Dunder attribute access not allowed: {attr_name}",
                            security_rule="no_dunder_access",
                            attempted_action=f"attr:{attr_name}",
                            details={"template_name": template_name}
                        )
        
        except SyntaxError:
            # If we can't parse it as Python, it's probably fine (Jinja2 syntax)
            pass
        except SecurityError:
            raise
        except Exception as e:
            self.logger.warning(
                "Error validating expression",
                expression=expression,
                error=str(e),
                template_name=template_name
            )
    
    def _get_function_name(self, node: ast.AST) -> str:
        """Extract function name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        else:
            return str(node)
    
    def validate_context_variables(self, context: Dict[str, Any], template_name: Optional[str] = None) -> None:
        """Validate context variables for security issues."""
        self.logger.debug(
            "Validating context variables",
            template_name=template_name,
            var_count=len(context)
        )
        
        for key, value in context.items():
            # Check for dangerous variable names
            if key.startswith('__') and key.endswith('__'):
                raise SecurityError(
                    f"Dunder variable names not allowed: {key}",
                    security_rule="no_dunder_variables",
                    attempted_action=f"variable:{key}",
                    details={"template_name": template_name}
                )
            
            # Check for dangerous variable types
            if callable(value) and key not in self._allowed_globals:
                raise SecurityError(
                    f"Callable variables not allowed unless explicitly allowed: {key}",
                    security_rule="no_callable_variables",
                    attempted_action=f"callable:{key}",
                    details={
                        "template_name": template_name,
                        "variable_type": type(value).__name__
                    }
                )
    
    def create_safe_globals(self) -> Dict[str, Any]:
        """Create a safe globals dictionary for template rendering."""
        safe_globals = {
            # Safe built-ins
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'sorted': sorted,
            'reversed': reversed,
            'enumerate': enumerate,
            'zip': zip,
            'range': range,
        }
        
        # Add allowed globals from settings
        for name in self._allowed_globals:
            if name in __builtins__:
                safe_globals[name] = __builtins__[name]
        
        # Remove blocked globals
        for name in self._blocked_globals:
            safe_globals.pop(name, None)
        
        return safe_globals
    
    def validate_file_access(self, file_path: Path) -> None:
        """Validate file access is allowed."""
        if not self.settings.allow_file_access:
            raise SecurityError(
                "File access is disabled",
                security_rule="no_file_access",
                attempted_action=f"file_access:{file_path}",
                details={"file_path": str(file_path)}
            )
        
        # Additional file access validation could go here
        # (e.g., path traversal protection, allowed directories, etc.)
    
    def check_recursion_depth(self, current_depth: int) -> None:
        """Check if recursion depth is within limits."""
        if current_depth > self.settings.max_recursion_depth:
            raise SecurityError(
                f"Maximum recursion depth exceeded: {current_depth} > {self.settings.max_recursion_depth}",
                security_rule="max_recursion_depth",
                attempted_action=f"recursion:{current_depth}",
                details={"current_depth": current_depth, "max_depth": self.settings.max_recursion_depth}
            )
    
    def check_loop_iterations(self, iterations: int) -> None:
        """Check if loop iterations are within limits."""
        if iterations > self.settings.max_loop_iterations:
            raise SecurityError(
                f"Maximum loop iterations exceeded: {iterations} > {self.settings.max_loop_iterations}",
                security_rule="max_loop_iterations",
                attempted_action=f"loop:{iterations}",
                details={"iterations": iterations, "max_iterations": self.settings.max_loop_iterations}
            ) 