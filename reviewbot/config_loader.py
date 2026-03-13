"""
Configuration loader for reviewbot.

Provides configuration management through environment variables.
"""

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "review": {
        "languages": ["python", "go", "javascript", "typescript", "java", "cpp", "c", "rust"],
        "ignore_paths": ["migrations/", "docs/", "vendor/", "node_modules/", ".git/"],
        "language": "ru",
    },
    "ai": {
        "temperature": 0.3,
        "max_tokens": 2000,
        "model": "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    },
}


class ConfigLoader:
    """Loads and manages reviewbot configuration."""

    def __init__(self, config_path: str | None = None) -> None:
        """
        Initialize the configuration loader.

        Args:
            config_path: Not used in environment-only configuration mode.
        """
        self.config_path = None
        self._config: dict[str, Any] | None = None

    def _find_config_path(self) -> str | None:
        """Not used in environment-only configuration mode."""
        return None

    @property
    def config(self) -> dict[str, Any]:
        """Get the merged configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        config = DEFAULT_CONFIG.copy()

        # Override with environment variables
        config = self._apply_env_overrides(config)

        return config

    def _merge_configs(
        self, default: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = default.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_mapping = {
            "LLM_TEMPERATURE": ("ai", "temperature", float),
            "LLM_MAX_TOKENS": ("ai", "max_tokens", int),
            "LLM_MODEL": ("ai", "model", str),
            "REVIEW_LANGUAGE": ("review", "language", str),
        }

        for env_var, path_parts, converter in [
            (k, v[:-1], v[-1]) for k, v in env_mapping.items()
        ]:
            if env_var in os.environ:
                value = os.environ[env_var]
                try:
                    converted_value = converter(value)
                    config_obj = config
                    for part in path_parts[:-1]:
                        config_obj = config_obj.setdefault(part, {})
                    config_obj[path_parts[-1]] = converted_value
                except (ValueError, TypeError) as e:
                    print(f"[WARNING] Invalid value for {env_var}: {e}")

        return config

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value by nested keys.

        Args:
            keys: Nested keys to traverse (e.g., 'review', 'max_comments')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        config = self.config
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                return default
        return config

    def should_review_file(self, file_path: str) -> bool:
        """
        Check if a file should be reviewed based on configuration.

        Args:
            file_path: Path to the file

        Returns:
            True if file should be reviewed, False otherwise
        """
        ignore_paths = self.get("review", "ignore_paths", default=[])

        for ignore_pattern in ignore_paths:
            if ignore_pattern in file_path:
                return False

        # Check language support
        languages = self.get("review", "languages", default=[])
        ext = Path(file_path).suffix.lstrip(".").lower()

        lang_extensions = {
            "python": ["py"],
            "go": ["go"],
            "javascript": ["js", "jsx", "mjs"],
            "typescript": ["ts", "tsx"],
            "java": ["java"],
            "cpp": ["cpp", "cc", "cxx", "hpp", "hxx"],
            "c": ["c", "h"],
            "rust": ["rs"],
        }

        for lang, extensions in lang_extensions.items():
            if lang in languages and ext in extensions:
                return True

        # If no language filter or unknown extension, review it
        if not languages:
            return True

        return False
