"""
Module Runner - Execute cognitive modules with LLM calls.

This module handles:
- Loading prompt configurations from registry
- Rendering prompts with context variables
- Calling LLM with tool support
- Validating outputs against JSON schemas
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sima_llm import LLMRouter, LLMResponse
from sima_prompts import PromptRegistry, render_prompt

logger = logging.getLogger(__name__)


@dataclass
class ModuleResult:
    """Result from running a module."""

    module_name: str
    """Name of the module that produced this result."""

    output: dict[str, Any]
    """Parsed JSON output from the module."""

    raw_response: LLMResponse
    """Raw LLM response including tool call information."""

    tool_calls: list[dict[str, Any]]
    """Any tool calls made during execution."""

    is_valid: bool
    """Whether output passed schema validation."""

    validation_errors: list[str]
    """List of validation errors if any."""


class ModuleRunner:
    """
    Runner for cognitive modules.

    Loads prompts, renders with context, calls LLM with tools,
    and validates output against JSON schemas.
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        prompt_registry: PromptRegistry | None = None,
        schemas_dir: str | Path | None = None,
    ):
        """
        Initialize the module runner.

        Args:
            llm_router: LLM router for completions.
            prompt_registry: Prompt registry instance.
            schemas_dir: Directory containing JSON schemas.
        """
        self.llm = llm_router
        self.prompts = prompt_registry or PromptRegistry()

        if schemas_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            schemas_dir = project_root

        self.schemas_dir = Path(schemas_dir)
        self._schema_cache: dict[str, dict] = {}

    async def run(
        self,
        module_name: str,
        variables: dict[str, Any],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ModuleResult:
        """
        Run a cognitive module.

        Args:
            module_name: Name of the module (e.g., 'perception_rpt', 'planner').
            variables: Context variables for prompt rendering.
            provider: LLM provider override.
            model: Model override.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            ModuleResult with parsed output and metadata.
        """
        # Load prompt config
        prompt_config = self.prompts.load(module_name)

        # Render messages with variables
        messages = render_prompt(prompt_config, variables)

        # Get tools from prompt config
        tools = prompt_config.tools if prompt_config.tools else None

        logger.info(
            f"Running module '{module_name}' with {len(messages)} messages"
            + (f" and tools: {tools}" if tools else "")
        )

        # Call LLM
        response = await self.llm.complete(
            messages=messages,
            tools=tools,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            auto_execute_tools=True,
        )

        # Parse JSON output
        output = {}
        validation_errors = []
        is_valid = True

        if response.content:
            try:
                output = json.loads(response.content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from module '{module_name}': {e}")
                validation_errors.append(f"JSON parse error: {e}")
                is_valid = False

        # Validate against schema
        if is_valid and prompt_config.schema_file:
            schema = self._load_schema(prompt_config.schema_file)
            if schema:
                schema_errors = self._validate_schema(output, schema)
                if schema_errors:
                    validation_errors.extend(schema_errors)
                    is_valid = False

        return ModuleResult(
            module_name=module_name,
            output=output,
            raw_response=response,
            tool_calls=response.tool_results,
            is_valid=is_valid,
            validation_errors=validation_errors,
        )

    def run_sync(
        self,
        module_name: str,
        variables: dict[str, Any],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ModuleResult:
        """
        Synchronous version of run().

        See run() for parameter documentation.
        """
        import asyncio

        return asyncio.run(
            self.run(
                module_name=module_name,
                variables=variables,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )

    def _load_schema(self, schema_file: str) -> dict | None:
        """Load a JSON schema file."""
        if schema_file in self._schema_cache:
            return self._schema_cache[schema_file]

        # Handle relative paths
        if schema_file.startswith("shared/schemas/"):
            schema_file = schema_file.replace("shared/schemas/", "")

        schema_path = self.schemas_dir / schema_file
        if not schema_path.exists():
            logger.warning(f"Schema file not found: {schema_path}")
            return None

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            self._schema_cache[schema_file] = schema
            return schema
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load schema {schema_path}: {e}")
            return None

    def _validate_schema(self, data: dict, schema: dict) -> list[str]:
        """
        Validate data against a JSON schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []

        try:
            import jsonschema

            validator = jsonschema.Draft202012Validator(schema)
            for error in validator.iter_errors(data):
                errors.append(f"{error.json_path}: {error.message}")
        except ImportError:
            # jsonschema not installed, do basic validation
            required = schema.get("required", [])
            for field in required:
                if field not in data:
                    errors.append(f"Missing required field: {field}")

        return errors
