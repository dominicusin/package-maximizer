"""Tests for manifest loader coverage (parsing/__init__.py + manifest_loader.py)."""
from __future__ import annotations

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

import requests_mock  # noqa: F401

from package_maximizer.parsing import (
    ManifestLoader,
    ManifestParseException,
    RemoteManifestSource,
    PARSER_REGISTRY,
    get_parser,
)
from package_maximizer.parsing import _LazyParserRegistry
import package_maximizer.parsing as parsing
import package_maximizer.parsers as parsers  # noqa: F401

from package_maximizer.core.package import Package


class TestManifestLoaderJSON:
    def test_parse_json_list(self):
        loader = ManifestLoader.from_paths(["manifest.json"])
        text = '[{"name": "vim", "version": "9.0"}, {"name": "libc6"}]'
        with open("manifest.json", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert len(result) == 2
            assert result[0].name == "vim"
        finally:
            import os
            os.remove("manifest.json")

    def test_parse_json_object_with_packages_key(self):
        loader = ManifestLoader.from_paths(["manifest.json"])
        obj = {"packages": [{"name": "vim", "version": "9.0"}]}
        text = __import__("json").dumps(obj)
        with open("manifest.json", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert len(result) == 1
            assert result[0].name == "vim"
        finally:
            import os
            os.remove("manifest.json")

    def test_parse_json_invalid(self):
        loader = ManifestLoader.from_paths(["manifest.json"])
        with open("manifest.json", "w") as f:
            f.write("{invalid")
        try:
            with pytest.raises(ManifestParseException):
                loader.parse()
        finally:
            import os
            os.remove("manifest.json")

    def test_parse_json_list_of_strings(self):
        loader = ManifestLoader.from_paths(["manifest.json"])
        text = '["vim", "libc6"]'
        with open("manifest.json", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert len(result) == 2
            assert result[0].name == "vim"
        finally:
            import os
            os.remove("manifest.json")


class TestManifestLoaderYAML:
    def test_parse_yaml_list(self):
        loader = ManifestLoader.from_paths(["manifest.yaml"])
        text = "- name: vim\n  version: 9.0\n- name: libc6"
        with open("manifest.yaml", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert len(result) == 2
            assert result[0].name == "vim"
        finally:
            import os
            os.remove("manifest.yaml")

    def test_parse_yaml_dict_with_packages_key(self):
        loader = ManifestLoader.from_paths(["manifest.yaml"])
        data = {"packages": [{"name": "vim", "version": "9.0"}]}
        import yaml
        text = yaml.dump(data)
        with open("manifest.yaml", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert len(result) == 1
            assert result[0].name == "vim"
        finally:
            import os
            os.remove("manifest.yaml")

    def test_parse_yaml_invalid(self):
        loader = ManifestLoader.from_paths(["manifest.yaml"])
        with open("manifest.yaml", "w") as f:
            f.write("invalid: [")
        try:
            with pytest.raises(ManifestParseException):
                loader.parse()
        finally:
            import os
            os.remove("manifest.yaml")


class TestManifestLoaderCsv:
    def test_parse_csv(self):
        loader = ManifestLoader.from_paths(["manifest.csv"])
        text = "name,version,depends\nvim,9.0,libc6\napache2,2.4.57,libm"
        with open("manifest.csv", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert len(result) == 2
            assert result[0].name == "vim"
            assert "libc6" in result[0].depends
        finally:
            import os
            os.remove("manifest.csv")

    def test_parse_csv_empty_fieldnames(self):
        loader = ManifestLoader.from_paths(["manifest.csv"])
        text = ""
        with open("manifest.csv", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert result == []
        finally:
            import os
            os.remove("manifest.csv")


class TestManifestLoaderDedup:
    def test_dedup_by_name_and_version(self):
        loader = ManifestLoader.from_paths(["manifest.json"])
        text = '[{"name": "vim", "version": "9.0"}, {"name": "vim", "version": "9.0"}]'
        with open("manifest.json", "w") as f:
            f.write(text)
        try:
            result = loader.parse()
            assert len(result) == 1
        finally:
            import os
            os.remove("manifest.json")


class TestRemoteManifestSource:
    def test_fetch_list(self, requests_mock):
        from package_maximizer.parsing import RemoteManifestSource

        url = "https://repo.example.org/api/packages"
        source = RemoteManifestSource(url)
        source.headers = {}
        source.params = {}
        source.timeout = 15.0

        requests_mock.get(
            url,
            json=[{"name": "vim", "version": "9.0"}, {"name": "libc6"}],
            headers={"Content-Type": "application/json"},
        )
        resp = source.fetch()
        assert len(resp) == 2
        assert resp[0].name == "vim"

    def test_fetch_with_packages_key(self, requests_mock):
        from package_maximizer.parsing import RemoteManifestSource

        source = RemoteManifestSource("https://repo.example.org/api/packages")
        source.headers = {}
        source.params = {}
        source.timeout = 15.0

        requests_mock.get(
            "https://repo.example.org/api/packages",
            json={"packages": [{"name": "vim", "version": "9.0"}]},
            headers={"Content-Type": "application/json"},
        )
        resp = source.fetch()
        assert len(resp) == 1
        assert resp[0].name == "vim"


class TestParserRegistry:
    def test_parser_registry_getitem(self):
        assert PARSER_REGISTRY["apt"] is not None
        with pytest.raises(KeyError):
            PARSER_REGISTRY["unknown"]

    def test_parser_registry_get(self):
        assert PARSER_REGISTRY.get("apt") is not None
        assert PARSER_REGISTRY.get("unknown") is None
        assert PARSER_REGISTRY.get("unknown", "default") == "default"

    def test_parser_registry_contains(self):
        assert "apt" in PARSER_REGISTRY
        assert "unknown" not in PARSER_REGISTRY

    def test_parser_registry_keys(self):
        keys = list(PARSER_REGISTRY.keys())
        assert "apt" in keys

    def test_parser_registry_items(self):
        items = list(PARSER_REGISTRY.items())
        assert any(name == "apt" for name, _ in items)

    def test_parser_registry_values(self):
        values = list(PARSER_REGISTRY.values())
        assert any(cls is not None for cls in values)

    def test_parser_registry_iter(self):
        names = list(PARSER_REGISTRY)
        assert "apt" in names

    def test_get_parser(self):
        parser = get_parser("apt")
        assert parser is not None

    def test_get_parser_unknown(self):
        with pytest.raises(ValueError):
            get_parser("unknown")


class TestLazyParserRegistry:
    def test_lazy_registry_init(self):
        reg = _LazyParserRegistry()
        assert len(reg) == len(parsing._PARSER_SPECS)

    def test_lazy_registry_getitem(self):
        reg = _LazyParserRegistry()
        assert reg["apt"] is not None

    def test_lazy_registry_get(self):
        reg = _LazyParserRegistry()
        assert reg.get("apt") is not None
        assert reg.get("unknown") is None

    def test_lazy_registry_contains(self):
        reg = _LazyParserRegistry()
        assert "apt" in reg
        assert "unknown" not in reg

    def test_lazy_registry_keys(self):
        reg = _LazyParserRegistry()
        assert "apt" in reg.keys()

    def test_lazy_registry_items(self):
        reg = _LazyParserRegistry()
        assert ("apt", parsers.APTParser) in reg.items()

    def test_lazy_registry_values(self):
        reg = _LazyParserRegistry()
        assert any(cls is not None for cls in reg.values())

    def test_lazy_registry_iter(self):
        reg = _LazyParserRegistry()
        assert "apt" in list(reg)
