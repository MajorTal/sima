"""
Prompt Renderer - Render prompt templates with Jinja2.
"""

from typing import Any

from jinja2 import Environment, BaseLoader, StrictUndefined

from .registry import PromptConfig


# Create Jinja2 environment
_env = Environment(
    loader=BaseLoader(),
    undefined=StrictUndefined,
    autoescape=False,
)


def render_prompt(
    config: PromptConfig,
    variables: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Render a prompt configuration with Jinja2 template substitution.

    Supports:
    - Variable substitution: {{variable_name}}
    - Nested access: {{senses.heartbeat_rate.value}}
    - Conditionals: {% if senses %}...{% endif %}
    - Loops: {% for item in items %}...{% endfor %}

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

        # Render with Jinja2
        try:
            template = _env.from_string(content)
            rendered_content = template.render(**variables)
        except Exception:
            # If template fails, return content as-is
            rendered_content = content

        rendered.append({
            "role": role,
            "content": rendered_content,
        })

    return rendered


def render_messages(
    messages: list[dict[str, str]],
    variables: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Render a list of message templates with Jinja2.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        variables: Dict of variable name -> value for substitution.

    Returns:
        List of rendered messages.
    """
    rendered = []
    for msg in messages:
        try:
            template = _env.from_string(msg["content"])
            rendered_content = template.render(**variables)
        except Exception:
            rendered_content = msg["content"]

        rendered.append({
            "role": msg["role"],
            "content": rendered_content,
        })
    return rendered
