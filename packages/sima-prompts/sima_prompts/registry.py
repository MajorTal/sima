"""
Prompt Registry - Load and manage module prompts from YAML files.

Prompts are YAML files with:
- name: module name
- version: prompt version
- schema_file: path to JSON schema for output validation
- tools: optional list of tool names the module can use (e.g., ['get_current_datetime'])
- messages: list of {role, content} message templates
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PromptConfig:
    """Configuration loaded from a prompt YAML file."""

    name: str
    """Module name (e.g., 'perception_rpt', 'planner')."""

    version: str
    """Prompt version string."""

    schema_file: str
    """Path to JSON schema file for output validation."""

    messages: list[dict[str, str]]
    """List of message templates with 'role' and 'content'."""

    tools: list[str] = field(default_factory=list)
    """List of tool names this module can use (e.g., ['get_current_datetime'])."""

    raw_yaml: dict[str, Any] = field(default_factory=dict)
    """Original YAML content for reference."""

    source_path: Path | None = None
    """Path to the source YAML file."""


class PromptRegistry:
    """
    Registry for loading and caching module prompts.

    Prompts are loaded from YAML files in the prompts directory.
    Each prompt can optionally specify tools that the module can invoke.
    """

    def __init__(self, prompts_dir: str | Path | None = None):
        """
        Initialize the prompt registry.

        Args:
            prompts_dir: Directory containing prompt YAML files.
                        Defaults to 'prompts/' relative to project root.
        """
        if prompts_dir is None:
            # Default to project root prompts directory
            project_root = Path(__file__).parent.parent.parent.parent
            prompts_dir = project_root / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, PromptConfig] = {}

    def load(self, module_name: str) -> PromptConfig:
        """
        Load a prompt configuration by module name.

        Args:
            module_name: Name of the module (e.g., 'perception_rpt', 'planner').

        Returns:
            PromptConfig with loaded configuration.

        Raises:
            FileNotFoundError: If prompt file doesn't exist.
            ValueError: If YAML is invalid.
        """
        if module_name in self._cache:
            return self._cache[module_name]

        # Try different file name patterns
        patterns = [
            f"{module_name}.yaml",
            f"{module_name}.yml",
        ]

        yaml_path = None
        for pattern in patterns:
            candidate = self.prompts_dir / pattern
            if candidate.exists():
                yaml_path = candidate
                break

        if yaml_path is None:
            raise FileNotFoundError(
                f"Prompt file not found for module '{module_name}' "
                f"in {self.prompts_dir}"
            )

        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise ValueError(f"Invalid prompt YAML in {yaml_path}: expected dict")

        # Parse required fields
        name = raw.get("name", module_name)
        version = raw.get("version", "0.0.0")
        schema_file = raw.get("schema_file", "")
        messages = raw.get("messages", [])

        # Parse optional tools field
        tools = raw.get("tools", [])
        if not isinstance(tools, list):
            tools = [tools] if tools else []

        # Validate messages format
        if not isinstance(messages, list):
            raise ValueError(f"Invalid 'messages' in {yaml_path}: expected list")

        for msg in messages:
            if not isinstance(msg, dict):
                raise ValueError(f"Invalid message in {yaml_path}: expected dict")
            if "role" not in msg:
                raise ValueError(f"Message missing 'role' in {yaml_path}")
            if "content" not in msg:
                raise ValueError(f"Message missing 'content' in {yaml_path}")

        config = PromptConfig(
            name=name,
            version=version,
            schema_file=schema_file,
            messages=messages,
            tools=tools,
            raw_yaml=raw,
            source_path=yaml_path,
        )

        self._cache[module_name] = config
        return config

    def get_tools(self, module_name: str) -> list[str]:
        """
        Get the list of tools available to a module.

        Args:
            module_name: Name of the module.

        Returns:
            List of tool names (e.g., ['get_current_datetime']).
        """
        config = self.load(module_name)
        return config.tools

    def has_tools(self, module_name: str) -> bool:
        """
        Check if a module has any tools configured.

        Args:
            module_name: Name of the module.

        Returns:
            True if the module has tools configured.
        """
        config = self.load(module_name)
        return len(config.tools) > 0

    def list_modules(self) -> list[str]:
        """
        List all available module names in the prompts directory.

        Returns:
            List of module names.
        """
        modules = []
        if not self.prompts_dir.exists():
            return modules

        for path in self.prompts_dir.iterdir():
            if path.suffix in (".yaml", ".yml"):
                modules.append(path.stem)

        return sorted(modules)

    def reload(self, module_name: str | None = None) -> None:
        """
        Reload prompt(s) from disk.

        Args:
            module_name: If specified, reload only this module.
                        If None, clear entire cache.
        """
        if module_name:
            self._cache.pop(module_name, None)
        else:
            self._cache.clear()


# Default registry instance
_default_registry: PromptRegistry | None = None


def get_default_registry() -> PromptRegistry:
    """Get the default prompt registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = PromptRegistry()
    return _default_registry
