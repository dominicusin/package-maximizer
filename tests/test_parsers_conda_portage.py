"""Tests for Conda and Portage parsers."""

from __future__ import annotations

import pytest

from package_maximizer.parsers import CondaParser, PortageParser


class TestCondaParser:
    """Tests for Conda parser."""

    def test_parse_basic(self):
        parser = CondaParser()
        raw = "numpy 1.23.5\npandas 2.0.0\n# comment\n"
        result = parser.parse(raw)
        assert len(result) == 2
        assert result[0].name == "numpy"
        assert result[0].version == "1.23.5"

    def test_parse_empty(self):
        parser = CondaParser()
        assert parser.parse("") == []

    def test_parse_skips_comments(self):
        parser = CondaParser()
        raw = "# only comments\n"
        result = parser.parse(raw)
        assert result == []


class TestPortageParser:
    """Tests for Portage parser."""

    def test_parse_basic(self):
        parser = PortageParser()
        raw = "[ebuild   r] app-editors/vim-8.2.0\n[ebuild   r] sys-apps/less-590\n"
        result = parser.parse(raw)
        assert len(result) == 2
        assert result[0].name == "vim"
        assert result[0].version == "8.2.0"

    def test_parse_empty(self):
        parser = PortageParser()
        assert parser.parse("") == []

    def test_parse_ignores_non_portage_lines(self):
        parser = PortageParser()
        raw = "some random line\nanother line\n"
        result = parser.parse(raw)
        assert result == []
