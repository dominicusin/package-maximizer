"""Tests for configuration loading and logging setup."""

from __future__ import annotations

import json
import os

import pytest

from package_maximizer.core.config import Config, load_config
from package_maximizer.utils.logging_config import configure_logging, get_logger


class TestConfigDefaults:
    """Config should provide sane defaults."""

    def test_defaults(self):
        cfg = Config()
        assert cfg.default_solver == "greedy"
        assert cfg.cache_enabled is True
        assert cfg.max_packages == 5000

    def test_as_dict_excludes_source(self):
        cfg = Config()
        d = cfg.as_dict()
        assert "source" not in d
        assert d["default_solver"] == "greedy"


class TestConfigEnvOverride:
    """Environment variables should override defaults."""

    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv("PM_SOLVER", "ortools")
        monkeypatch.setenv("PM_CACHE_ENABLED", "false")
        monkeypatch.setenv("PM_MAX_PACKAGES", "100")
        monkeypatch.setenv("PM_LOG_JSON", "true")
        cfg = load_config()
        assert cfg.default_solver == "ortools"
        assert cfg.cache_enabled is False
        assert cfg.max_packages == 100
        assert cfg.log_json is True

    def test_bad_int_env_ignored(self, monkeypatch):
        monkeypatch.setenv("PM_MAX_PACKAGES", "not-a-number")
        cfg = load_config()
        # Falls back to default since coercion failed
        assert cfg.max_packages == 5000


class TestConfigFile:
    """Config file loading (JSON and YAML)."""

    def test_load_json_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PM_CONFIG", raising=False)
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps({"default_solver": "z3", "cache_ttl": 99}))
        cfg = load_config(p)
        assert cfg.default_solver == "z3"
        assert cfg.cache_ttl == 99
        assert cfg.source.endswith("cfg.json")

    def test_load_yaml_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PM_CONFIG", raising=False)
        monkeypatch.delenv("PM_API_KEY", raising=False)
        p = tmp_path / "cfg.yaml"
        p.write_text("default_manager: dnf\napi_key: secret-123\n")
        cfg = load_config(p)
        assert cfg.default_manager == "dnf"
        assert cfg.api_key == "secret-123"


class TestLoggingConfig:
    """Logging configuration should be side-effect free and return a logger."""

    def test_configure_returns_root_logger(self):
        logger = configure_logging("DEBUG")
        assert logger.level == 10  # DEBUG
        assert len(logger.handlers) >= 1

    def test_json_formatter_emits_valid_json(self, capsys):
        configure_logging("INFO", json_output=True)
        log = get_logger("pm.test")
        log.info("hello %s", "world")
        captured = capsys.readouterr().err
        assert "hello world" in captured
        # Should be valid JSON
        import json as _json

        line = next(l for l in captured.splitlines() if l.strip())
        payload = _json.loads(line)
        assert payload["level"] == "INFO"
        assert payload["message"] == "hello world"
