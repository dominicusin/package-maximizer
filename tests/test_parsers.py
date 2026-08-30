"""
Tests for parsers module.
"""

import pytest

from package_maximizer.core.package import Package
from package_maximizer.parsers import (
    APTParser,
    get_parser,
)


class TestAPTParser:
    """Tests for APTParser."""

    def test_empty_input(self):
        """Test with empty input."""
        parser = APTParser()
        result = parser.parse("")
        assert result == []

    def test_parse_dpkg_l_format(self):
        """Test parsing dpkg -l format."""
        parser = APTParser()
        raw = """ii  vim                        2:8.2.3995-1ubuntu1 amd64        Vi IMproved
rc  apache2                    2.4.57-1ubuntu1     amd64        Apache HTTP Server
"""
        result = parser.parse(raw)
        assert len(result) == 2
        assert any(p.name == "vim" for p in result)
        assert any(p.name == "apache2" for p in result)

    def test_parse_apt_list_format(self):
        """Test parsing apt list --installed format."""
        parser = APTParser()
        raw = """Listing... Done
apache2/stable,stable 2.4.57-1ubuntu1 amd64 [installed]
vim/stable 2:8.2.3995-1ubuntu1 amd64 [installed]
"""
        result = parser.parse(raw)
        assert len(result) == 2
        assert any(p.name == "apache2" and p.status == "installed" for p in result)
        assert any(p.name == "vim" and p.status == "installed" for p in result)

    def test_parse_simple_list(self):
        """Test parsing simple package list."""
        parser = APTParser()
        raw = """pkg1
pkg2
pkg3"""
        result = parser.parse(raw)
        assert len(result) == 3
        assert all(p.status == "candidate" for p in result)

    def test_parse_apt_cache_show_format(self):
        """Test parsing apt-cache show format."""
        parser = APTParser()
        raw = """Package: vim
Version: 2:8.2.3995-1ubuntu1
Depends: vim-runtime (= 2:8.2.3995-1ubuntu1), libc6 (>= 2.27)
Conflicts: vim-tiny

Package: apache2
Version: 2.4.57-1ubuntu1
Depends: apache2-bin (= 2.4.57-1ubuntu1)
"""
        result = parser.parse(raw)
        assert len(result) == 2
        
        vim_pkg = next((p for p in result if p.name == "vim"), None)
        assert vim_pkg is not None
        assert vim_pkg.version == "2:8.2.3995-1ubuntu1"
        assert "vim-runtime" in vim_pkg.depends
        assert "vim-tiny" in vim_pkg.conflicts


class TestParserRegistry:
    """Tests for parser registry."""

    def test_get_parser_apt(self):
        """Test getting APT parser."""
        parser = get_parser("apt")
        assert isinstance(parser, APTParser)

    def test_get_parser_case_insensitive(self):
        """Test case-insensitive parser lookup."""
        parser = get_parser("APT")
        assert isinstance(parser, APTParser)

    def test_get_parser_invalid(self):
        """Test getting invalid parser."""
        with pytest.raises(ValueError):
            get_parser("invalid_parser")
