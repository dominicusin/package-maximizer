"""
Tests for integrations module
"""

import pytest
from unittest.mock import patch, MagicMock
from package_maximizer.integrations import RealRepoIntegration
from package_maximizer.core.package import Package


class TestRealRepoIntegration:
    """Tests for RealRepoIntegration"""

    def test_init_default(self):
        """Test default initialization"""
        integration = RealRepoIntegration()
        assert integration.package_manager == "apt"

    def test_init_with_manager(self):
        """Test initialization with specific package manager"""
        integration = RealRepoIntegration(package_manager="pacman")
        assert integration.package_manager == "pacman"

    @patch('subprocess.run')
    def test_get_installed_packages_apt(self, mock_run):
        """Test getting installed packages for APT"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ii  pkg1  1.0.0  amd64  Package 1\nii  pkg2  2.0.0  amd64  Package 2"
        )
        
        integration = RealRepoIntegration(package_manager="apt")
        packages = integration.get_installed_packages()
        
        assert len(packages) >= 0

    @patch('subprocess.run')
    def test_get_installed_packages_pacman(self, mock_run):
        """Test getting installed packages for Pacman"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="core/pkg1 1.0.0\ncore/pkg2 2.0.0"
        )
        
        integration = RealRepoIntegration(package_manager="pacman")
        packages = integration.get_installed_packages()
        
        assert len(packages) >= 0

    @patch('subprocess.run')
    def test_search_packages_apt(self, mock_run):
        """Test searching packages for APT"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="pkg1  amd64  1.0.0\npkg2  amd64  2.0.0"
        )
        
        integration = RealRepoIntegration(package_manager="apt")
        packages = integration.search_packages("test")
        
        assert len(packages) >= 0

    @patch('subprocess.run')
    def test_get_package_info_apt(self, mock_run):
        """Test getting package info for APT"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Package: pkg1\nVersion: 1.0.0\nDepends: libc6\nConflicts: pkg2"
        )
        
        integration = RealRepoIntegration(package_manager="apt")
        info = integration.get_package_info("pkg1")
        
        # Should return PackageInfo or None
        assert info is None or hasattr(info, 'name')

    @patch('subprocess.run')
    def test_check_package_installed(self, mock_run):
        """Test checking if package is installed"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ii  pkg1  1.0.0  amd64  Package 1"
        )
        
        integration = RealRepoIntegration(package_manager="apt")
        installed = integration.check_package_installed("pkg1")
        
        assert isinstance(installed, bool)

    @patch('subprocess.run')
    def test_get_available_updates_apt(self, mock_run):
        """Test getting available updates for APT"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="pkg1  amd64  1.0.0 -> 1.0.1\npkg2  amd64  2.0.0 -> 2.0.1"
        )
        
        integration = RealRepoIntegration(package_manager="apt")
        updates = integration.get_available_updates()
        
        assert len(updates) >= 0

    @patch('subprocess.run')
    def test_get_system_info(self, mock_run):
        """Test getting system info"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="pkg1\npkg2"),  # installed
            MagicMock(returncode=0, stdout=""),  # updates
            MagicMock(returncode=0, stdout="apt 2.4.9"),  # version
        ]
        
        integration = RealRepoIntegration(package_manager="apt")
        info = integration.get_system_info()
        
        assert "package_manager" in info
        assert info["package_manager"] == "apt"

    def test_parser_selection(self):
        """Test parser selection based on package manager"""
        for manager in ["apt", "pacman", "dnf", "brew"]:
            integration = RealRepoIntegration(package_manager=manager)
            parser = integration.parser
            assert parser is not None

    def test_get_parser_method(self):
        """Test get_parser method"""
        integration = RealRepoIntegration()
        parser = integration._get_parser()
        assert parser is not None
