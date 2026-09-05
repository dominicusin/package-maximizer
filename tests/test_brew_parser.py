"""Tests for parsers.brew_parser — Homebrew package parser."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from package_maximizer.core.package import Package
from package_maximizer.parsers.brew_parser import BrewParser


class TestBrewParserParse:
    """parse method with different formats."""

    def test_parse_empty_string(self):
        parser = BrewParser()
        result = parser.parse("")
        assert result == []

    def test_parse_brew_list_format(self):
        parser = BrewParser()
        raw = (
            "==> Formulae\nvim\nwget\npython@3.11\n==> Casks\nfirefox\ngoogle-chrome\n"
        )
        result = parser.parse(raw)
        names = {p.name for p in result}
        assert "vim" in names
        assert "firefox" in names

    def test_parse_brew_info_format(self):
        parser = BrewParser()
        raw = """vim:
Version: 9.1.0000
From: https://github.com/vim/vim
Dependencies: python@3.11, ncurses
Conflicts with: vim-tiny
Installed: YES
"""
        result = parser.parse(raw)
        assert len(result) >= 1
        assert result[0].name == "vim"

    def test_parse_simple_list(self):
        parser = BrewParser()
        raw = "vim\nwget\ncurl\n"
        result = parser.parse(raw)
        names = {p.name for p in result}
        assert "vim" in names
        assert "wget" in names
        assert "curl" in names

    def test_parse_info_multiple_packages(self):
        parser = BrewParser()
        raw = """vim:
Version: 9.1.0000
From: https://github.com/vim/vim
Installed: YES

wget:
Version: 1.21.0
From: https://ftp.gnu.org/gnu/wget/
Installed: NO
"""
        result = parser.parse(raw)
        assert len(result) == 2
        names = {p.name for p in result}
        assert "vim" in names
        assert "wget" in names

    def test_parse_info_with_dependencies(self):
        parser = BrewParser()
        raw = """vim:
Version: 9.1.0000
From: https://github.com/vim/vim
Dependencies: python@3.11, ncurses
"""
        result = parser.parse(raw)
        assert len(result) == 1
        assert result[0].depends == ["python@3.11", "ncurses"]

    def test_parse_info_with_conflicts(self):
        parser = BrewParser()
        raw = """vim:
Version: 9.1.0000
From: https://github.com/vim/vim
Conflicts with: vim-tiny, gvim
"""
        result = parser.parse(raw)
        assert len(result) == 1
        assert result[0].conflicts == ["vim-tiny", "gvim"]

    def test_parse_info_with_installed_status(self):
        parser = BrewParser()
        raw = """vim:
Version: 9.1.0000
From: https://github.com/vim/vim
Installed: YES
"""
        result = parser.parse(raw)
        assert len(result) == 1
        assert result[0].status == "installed"


class TestBrewParserParseFromSystem:
    """parse_from_system method."""

    def test_parse_from_system_all_installed(self):
        parser = BrewParser()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "==> Formulae\nvim\nwget\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = parser.parse_from_system()
            mock_run.assert_called_once()
            assert len(result) == 2

    def test_parse_from_system_specific_packages(self):
        parser = BrewParser()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "vim:\nVersion: 9.1.0000\nFrom: https://github.com/vim/vim\n"
        )

        with patch("subprocess.run", return_value=mock_result):
            result = parser.parse_from_system(["vim"])
            assert len(result) >= 1

    def test_parse_from_system_subprocess_fails(self):
        parser = BrewParser()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error"

        with patch("subprocess.run", return_value=mock_result):
            result = parser.parse_from_system(["vim"])
            assert len(result) == 1
            assert result[0].status == "candidate"

    def test_parse_from_system_timeout(self):
        parser = BrewParser()
        import subprocess

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="brew", timeout=30),
        ):
            result = parser.parse_from_system()
            assert result == []

    def test_parse_from_system_file_not_found(self):
        parser = BrewParser()

        with patch("subprocess.run", side_effect=FileNotFoundError("brew not found")):
            result = parser.parse_from_system()
            assert result == []
