"""Tests for NpmMetadataAdapter and BrewMetadataAdapter."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from package_maximizer.adapters import (
    BrewMetadataAdapter,
    NpmMetadataAdapter,
    PackageMetadata,
)


class TestNpmMetadataAdapter:
    """Tests for NpmMetadataAdapter."""

    def test_parse_basic(self):
        """Test parsing npm view output."""
        raw = json.dumps(
            {
                "name": "express",
                "version": "4.18.2",
                "description": "Fast, unopinionated, minimalist web framework",
                "homepage": "http://expressjs.com/",
                "dependencies": {
                    "accepts": "~1.3.8",
                    "body-parser": "1.20.1",
                },
            }
        )

        adapter = NpmMetadataAdapter()
        result = adapter.parse(raw)

        assert result is not None
        assert result.name == "express"
        assert result.version == "4.18.2"
        assert result.description == "Fast, unopinionated, minimalist web framework"
        assert "accepts" in result.depends
        assert "body-parser" in result.depends

    def test_parse_array_response(self):
        """Test parsing npm view array response (multiple versions)."""
        raw = json.dumps(
            [
                {"name": "express", "version": "4.17.1"},
                {"name": "express", "version": "4.18.2"},
            ]
        )

        adapter = NpmMetadataAdapter()
        result = adapter.parse(raw)

        assert result is not None
        assert result.name == "express"
        assert result.version == "4.18.2"

    def test_parse_empty(self):
        """Test parsing empty input."""
        adapter = NpmMetadataAdapter()
        assert adapter.parse("") is None
        assert adapter.parse("invalid json") is None

    def test_parse_lockfile_v3(self):
        """Test parsing package-lock.json v3."""
        raw = json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/express": {
                        "version": "4.18.2",
                        "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
                        "dependencies": {
                            "accepts": "~1.3.8",
                        },
                    },
                    "node_modules/@types/express": {
                        "version": "4.17.21",
                    },
                },
            }
        )

        adapter = NpmMetadataAdapter()
        results = adapter.parse_lockfile(raw)

        assert len(results) == 2
        names = {r.name for r in results}
        assert "express" in names
        assert "@types/express" in names

    def test_fetch_success(self):
        """Test successful fetch."""
        raw = json.dumps(
            {
                "name": "express",
                "version": "4.18.2",
                "dependencies": {"accepts": "~1.3.8"},
            }
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = raw

        adapter = NpmMetadataAdapter()
        with patch("subprocess.run", return_value=mock_result):
            result = adapter.fetch("express")

        assert result is not None
        assert result.name == "express"

    def test_fetch_failure(self):
        """Test fetch failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        adapter = NpmMetadataAdapter()
        with patch("subprocess.run", return_value=mock_result):
            result = adapter.fetch("nonexistent-package-xyz")

        assert result is None


class TestBrewMetadataAdapter:
    """Tests for BrewMetadataAdapter."""

    def test_parse_basic(self):
        """Test parsing brew info JSON output."""
        raw = json.dumps(
            [
                {
                    "name": "node",
                    "versions": {"stable": "20.9.0"},
                    "desc": "Platform built on V8 to build network applications",
                    "homepage": "https://nodejs.org/",
                    "dependencies": ["openssl", "icu4c"],
                    "conflicts_with": ["nodejs"],
                }
            ]
        )

        adapter = BrewMetadataAdapter()
        result = adapter.parse(raw)

        assert result is not None
        assert result.name == "node"
        assert result.version == "20.9.0"
        assert "openssl" in result.depends
        assert "nodejs" in result.conflicts

    def test_parse_empty(self):
        """Test parsing empty input."""
        adapter = BrewMetadataAdapter()
        assert adapter.parse("") is None
        assert adapter.parse("invalid json") is None

    def test_parse_dict_response(self):
        """Test parsing dict response (single package)."""
        raw = json.dumps(
            {
                "name": "python",
                "versions": {"stable": "3.12.0"},
                "desc": "Interpreted, interactive, object-oriented programming language",
                "dependencies": ["openssl", "readline"],
            }
        )

        adapter = BrewMetadataAdapter()
        result = adapter.parse(raw)

        assert result is not None
        assert result.name == "python"
        assert result.version == "3.12.0"

    def test_fetch_success(self):
        """Test successful fetch."""
        raw = json.dumps(
            [
                {
                    "name": "node",
                    "versions": {"stable": "20.9.0"},
                    "dependencies": ["openssl"],
                }
            ]
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = raw

        adapter = BrewMetadataAdapter()
        with patch("subprocess.run", return_value=mock_result):
            result = adapter.fetch("node")

        assert result is not None
        assert result.name == "node"

    def test_fetch_failure(self):
        """Test fetch failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        adapter = BrewMetadataAdapter()
        with patch("subprocess.run", return_value=mock_result):
            result = adapter.fetch("nonexistent-formula-xyz")

        assert result is None


class TestGetAdapter:
    """Tests for get_adapter factory function."""

    def test_get_npm_adapter(self):
        from package_maximizer.adapters import get_adapter

        adapter = get_adapter("npm")
        assert isinstance(adapter, NpmMetadataAdapter)

    def test_get_brew_adapter(self):
        from package_maximizer.adapters import get_adapter

        adapter = get_adapter("brew")
        assert isinstance(adapter, BrewMetadataAdapter)

    def test_get_invalid_adapter(self):
        from package_maximizer.adapters import get_adapter

        with pytest.raises(ValueError):
            get_adapter("invalid_manager_xyz")
