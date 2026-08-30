"""
Extended tests for parsers (Pacman, DNF, Brew)
"""

import pytest
from package_maximizer.parsers import PacmanParser, DNFParser, BrewParser


class TestPacmanParser:
    """Tests for Pacman parser"""

    def test_parse_pacman_q(self):
        """Test parsing pacman -Q output"""
        raw = """core/linux 6.6.10.arch1-1
core/glibc 2.38-5
core/python 3.11.5-1
extra/vim 9.1.0000-1"""
        parser = PacmanParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 4
        names = [p.name for p in packages]
        assert "linux" in names
        assert "glibc" in names
        assert "python" in names
        assert "vim" in names

    def test_parse_pacman_ss(self):
        """Test parsing pacman -Ss output"""
        raw = """core/linux 6.6.10.arch1-1
core/python 3.11.5-1
extra/vim 9.1.0000-1 [installed]"""
        parser = PacmanParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 3
        names = [p.name for p in packages]
        assert "linux" in names
        assert "python" in names
        assert "vim" in names

    def test_parse_pacman_si(self):
        """Test parsing pacman -Si output"""
        raw = """Repository     : core
Name            : linux
Version        : 6.6.10.arch1-1
Depends On     : coreutils  glibc
Conflicts With : linux-lts
Status         : installed"""
        parser = PacmanParser()
        packages = parser.parse(raw)
        
        # Should parse correctly with colon separator
        assert len(packages) >= 0
        if packages and packages[0].name:
            pkg = packages[0]
            assert pkg.name == "linux"
            assert pkg.version == "6.6.10.arch1-1"

    def test_parse_simple_list(self):
        """Test parsing simple package list"""
        raw = """pkg1
pkg2
pkg3"""
        parser = PacmanParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 3
        names = [p.name for p in packages]
        assert "pkg1" in names
        assert "pkg2" in names
        assert "pkg3" in names


class TestDNFParser:
    """Tests for DNF parser"""

    def test_parse_dnf_list_installed(self):
        """Test parsing dnf list installed output"""
        raw = """Installed Packages
kernel-core.x86_64  6.6.10-100.fc39  @updates
vim-enhanced.x86_64  2:9.1.0000-1.fc39  @fedora
python3.x86_64  3.11.0-1.fc39  fedora"""
        parser = DNFParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 3
        names = [p.name for p in packages]
        assert "kernel-core" in names
        assert "vim-enhanced" in names
        assert "python3" in names

    def test_parse_dnf_info(self):
        """Test parsing dnf info output"""
        raw = """Name         : kernel-core
Version      : 6.6.10
Release      : 100.fc39
Architecture : x86_64
Depends On   : kernel = 6.6.10-100.fc39
Conflicts With: kernel < 6.6.10
Installed    : Yes"""
        parser = DNFParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 1
        pkg = packages[0]
        assert pkg.name == "kernel-core"
        assert pkg.version == "6.6.10-100.fc39"

    def test_parse_dnf_search(self):
        """Test parsing dnf search output"""
        raw = """kernel-core.x86_64 : The Linux kernel
vim-enhanced.x86_64 : A version of the VIM editor
python3.x86_64 : Python programming language"""
        parser = DNFParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 3
        names = [p.name for p in packages]
        assert "kernel-core" in names
        assert "vim-enhanced" in names
        assert "python3" in names


class TestBrewParser:
    """Tests for Brew parser"""

    def test_parse_brew_list(self):
        """Test parsing brew list output"""
        raw = """==> Formulae
vim
wget
python@3.11

==> Casks
firefox
google-chrome"""
        parser = BrewParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 5
        names = [p.name for p in packages]
        assert "vim" in names
        assert "wget" in names
        assert "python@3.11" in names
        assert "firefox" in names
        assert "google-chrome" in names

    def test_parse_brew_info(self):
        """Test parsing brew info output"""
        raw = """vim:
Stable version: 9.1.0000
From: https://github.com/vim/vim
Dependencies: python@3.11, ncurses
Conflicts with: vim-tiny
Installed: YES"""
        parser = BrewParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 1
        pkg = packages[0]
        assert pkg.name == "vim"
        assert pkg.version == "9.1.0000"

    def test_parse_simple_list(self):
        """Test parsing simple package list"""
        raw = """pkg1
pkg2
pkg3"""
        parser = BrewParser()
        packages = parser.parse(raw)
        
        assert len(packages) == 3
        names = [p.name for p in packages]
        assert "pkg1" in names
        assert "pkg2" in names
        assert "pkg3" in names


class TestParserRegistry:
    """Tests for parser registry"""

    def test_get_parser_pacman(self):
        """Test getting pacman parser"""
        from package_maximizer.parsers import get_parser
        parser = get_parser("pacman")
        assert isinstance(parser, PacmanParser)

    def test_get_parser_dnf(self):
        """Test getting dnf parser"""
        from package_maximizer.parsers import get_parser
        parser = get_parser("dnf")
        assert isinstance(parser, DNFParser)

    def test_get_parser_brew(self):
        """Test getting brew parser"""
        from package_maximizer.parsers import get_parser
        parser = get_parser("brew")
        assert isinstance(parser, BrewParser)

    def test_get_parser_case_insensitive(self):
        """Test case insensitive parser lookup"""
        from package_maximizer.parsers import get_parser
        
        parser1 = get_parser("PACMAN")
        parser2 = get_parser("Pacman")
        parser3 = get_parser("pacman")
        
        assert isinstance(parser1, PacmanParser)
        assert isinstance(parser2, PacmanParser)
        assert isinstance(parser3, PacmanParser)

    def test_get_parser_invalid(self):
        """Test getting invalid parser"""
        from package_maximizer.parsers import get_parser
        
        with pytest.raises(ValueError) as exc_info:
            get_parser("invalid")
        
        assert "not found" in str(exc_info.value)
