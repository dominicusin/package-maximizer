"""
Configuration support for Package Maximizer.

Loads settings from an optional config file (YAML or JSON) and overlays
environment variables (``PM_*``). Provides a single :class:`Config` object
consumed by the CLI, web, and solver layers.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_PATH_ENV = "PM_CONFIG"


@dataclass
class Config:
    """
    Runtime configuration for Package Maximizer.

    Attributes are merged from (in increasing priority):
    1. Built-in defaults
    2. A config file (``--config`` / ``PM_CONFIG``)
    3. Environment variables (``PM_*``)
    """

    default_solver: str = "greedy"
    default_manager: str = "apt"
    cache_enabled: bool = True
    cache_ttl: int = 3600
    api_key: str = "dev-key-change-in-production"
    max_packages: int = 5000
    max_name_len: int = 256
    log_level: str = "INFO"
    log_json: bool = False

    # Solver-specific tuning
    solver_timeout_ms: int = 10000

    # Source file that produced this config (for diagnostics)
    source: str = "defaults"

    @classmethod
    def load(
        cls,
        path: str | Path | None = None,
        *,
        environ: dict[str, str] | None = None,
    ) -> "Config":
        """
        Build a Config, applying file + environment overrides.

        Args:
            path: Explicit config file path. Defaults to ``$PM_CONFIG``.
            environ: Mapping of environment variables (defaults to os.environ).

        Returns:
            A populated :class:`Config`.
        """
        env = environ if environ is not None else dict(os.environ)
        cfg = cls()

        # 1) file
        file_path = Path(path) if path else None
        if file_path is None and env.get(_CONFIG_PATH_ENV):
            file_path = Path(env[_CONFIG_PATH_ENV])

        if file_path and file_path.exists():
            data = cls._read_file(file_path)
            for key in cls.__dataclass_fields__:
                if key in data and key != "source":
                    setattr(cfg, key, data[key])
            cfg.source = str(file_path)

        # 2) environment overrides
        mapping = {
            "PM_SOLVER": "default_solver",
            "PM_MANAGER": "default_manager",
            "PM_CACHE_ENABLED": "cache_enabled",
            "PM_CACHE_TTL": "cache_ttl",
            "PM_API_KEY": "api_key",
            "PM_MAX_PACKAGES": "max_packages",
            "PM_MAX_NAME_LEN": "max_name_len",
            "PM_LOG_LEVEL": "log_level",
            "PM_LOG_JSON": "log_json",
            "PM_SOLVER_TIMEOUT": "solver_timeout_ms",
        }
        for env_key, attr in mapping.items():
            if env_key in env:
                cfg._apply_env(attr, env[env_key])

        return cfg

    @staticmethod
    def _read_file(path: Path) -> dict[str, Any]:
        """Read a YAML or JSON config file."""
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError:
                logger.warning("PyYAML not installed; treating %s as JSON", path)
                return json.loads(text)
            return yaml.safe_load(text) or {}
        return json.loads(text)

    def _apply_env(self, attr: str, value: str) -> None:
        """Coerce an environment string into the attribute's type."""
        current = getattr(self, attr)
        if isinstance(current, bool):
            setattr(self, attr, value.strip().lower() in ("1", "true", "yes", "on"))
        elif isinstance(current, int):
            try:
                setattr(self, attr, int(value))
            except ValueError:
                logger.warning("Ignoring non-int value for %s: %r", attr, value)
        else:
            setattr(self, attr, value)

    def as_dict(self) -> dict[str, Any]:
        """Return the config as a plain dict (excludes ``source``)."""
        return {k: v for k, v in self.__dict__.items() if k != "source"}


def load_config(path: str | Path | None = None) -> Config:
    """Convenience wrapper returning a populated :class:`Config`."""
    return Config.load(path)
