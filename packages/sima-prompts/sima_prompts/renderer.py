"""
Prompt Renderer - Render prompt templates with variable substitution.
"""

import re
from typing import Any

from .registry import PromptConfig


def render_prompt(
    config: PromptConfig,
    variables: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Render a prompt configuration with variable substitution.

    Uses {{variable_name}} syntax for template variables.

    Args:
        config: PromptConfig loaded from registry.
        variables: Dict of variable name -> value for substitution.

    Returns:
        List of rendered messages with 'role' and 'content'.
    """
    rendered = []

    for msg in config.messages:
        role = msg["role"]
        content = msg["content"]

        # Substitute {{variable}} patterns
        rendered_content = _substitute_variables(content, variables)

        rendered.append({
            "role": role,
            "content": rendered_content,
        })

    return rendered


def _substitute_variables(template: str, variables: dict[str, Any]) -> str:
    """
    Substitute {{variable}} patterns in a template string.

    Args:
        template: Template string with {{variable}} placeholders.
        variables: Dict of variable name -> value.

    Returns:
        Rendered string with variables substituted.
    """
    def replace_var(match: re.Match) -> str:
        var_name = match.group(1).strip()
        if var_name in variables:
            value = variables[var_name]
            if isinstance(value, (dict, list)):
                import json
                return json.dumps(value, indent=2, default=str)
            return str(value)
        # Keep placeholder if variable not found
        return match.group(0)

    # Match {{variable_name}} patterns
    pattern = r"\{\{([^}]+)\}\}"
    return re.sub(pattern, replace_var, template)


def render_messages(
    messages: list[dict[str, str]],
    variables: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Render a list of message templates.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        variables: Dict of variable name -> value for substitution.

    Returns:
        List of rendered messages.
    """
    rendered = []
    for msg in messages:
        rendered.append({
            "role": msg["role"],
            "content": _substitute_variables(msg["content"], variables),
        })
    return rendered
