"""
Extended tests for RealRepoIntegration — all package managers, error paths.

Mocks subprocess.run so no real package-manager binaries are invoked.
Covers success, FileNotFoundError, and TimeoutExpired for every manager,
plus RepoConfig.get_parser, PackageInfo.to_package, check_package_installed
and get_system_info.
"""

from unittest.mock import MagicMock, patch

import pytest

from package_maximizer.core.package import Package
from package_maximizer.integrations import RealRepoIntegration
from package_maximizer.integrations.real_repo_integration import PackageInfo, RepoConfig

MANAGERS = ["apt", "pacman", "dnf", "brew"]

SAMPLE_DPKG = "ii  vim  2:8.1-1  amd64  Vi IMproved\nii  git 1:2.0-1 amd64 Git\n"


def _run(returncode=0, stdout=""):
    """Build a fake subprocess.CompletedProcess."""
    return MagicMock(returncode=returncode, stdout=stdout, stderr="")


@pytest.mark.parametrize("manager", MANAGERS)
class TestInstalledPackages:
    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_success(self, mock_run, manager):
        mock_run.return_value = _run(0, SAMPLE_DPKG)
        integration = RealRepoIntegration(package_manager=manager)
        result = integration.get_installed_packages()
        assert isinstance(result, list)

    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_filenotfound_returns_empty(self, mock_run, manager):
        mock_run.side_effect = FileNotFoundError("no binary")
        integration = RealRepoIntegration(package_manager=manager)
        assert integration.get_installed_packages() == []

    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_timeout_returns_empty(self, mock_run, manager):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=30)
        integration = RealRepoIntegration(package_manager=manager)
        assert integration.get_installed_packages() == []

    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_nonzero_returncode_empty(self, mock_run, manager):
        mock_run.return_value = _run(1, "")
        integration = RealRepoIntegration(package_manager=manager)
        assert integration.get_installed_packages() == []


@pytest.mark.parametrize("manager", MANAGERS)
class TestSearchPackages:
    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_success(self, mock_run, manager):
        mock_run.return_value = _run(0, "vim - Vi IMproved\n")
        integration = RealRepoIntegration(package_manager=manager)
        result = integration.search_packages("vim", limit=10)
        assert isinstance(result, list)

    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_filenotfound_empty(self, mock_run, manager):
        mock_run.side_effect = FileNotFoundError()
        integration = RealRepoIntegration(package_manager=manager)
        assert integration.search_packages("vim") == []


@pytest.mark.parametrize("manager", MANAGERS)
class TestPackageInfo:
    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_success(self, mock_run, manager):
        stdout = (
            "Version: 1.2.3\n"
            "Description: test package\n"
            "Depends: a, b\n"
            "Conflicts: c\n"
        )
        mock_run.return_value = _run(0, stdout)
        integration = RealRepoIntegration(package_manager=manager)
        info = integration.get_package_info("foo")
        # All managers must return a PackageInfo with the requested name
        # (field parsing is manager-specific; we only assert the contract).
        assert info is not None
        assert info.name == "foo"

    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_filenotfound_none(self, mock_run, manager):
        mock_run.side_effect = FileNotFoundError()
        integration = RealRepoIntegration(package_manager=manager)
        assert integration.get_package_info("foo") is None


@pytest.mark.parametrize("manager", MANAGERS)
class TestAvailableUpdates:
    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_success(self, mock_run, manager):
        mock_run.return_value = _run(0, "")
        integration = RealRepoIntegration(package_manager=manager)
        assert integration.get_available_updates() == []

    @patch("package_maximizer.integrations.real_repo_integration.subprocess.run")
    def test_filenotfound_empty(self, mock_run, manager):
        mock_run.side_effect = FileNotFoundError()
        integration = RealRepoIntegration(package_manager=manager)
        assert integration.get_available_updates() == []


def test_unknown_manager_returns_empty():
    integration = RealRepoIntegration(package_manager="unknown")
    assert integration.get_installed_packages() == []
    assert integration.search_packages("x") == []
    assert integration.get_package_info("x") is None
    assert integration.get_available_updates() == []


def test_repo_config_get_parser():
    assert (
        RepoConfig(name="a", url="u", package_manager="apt")
        .get_parser()
        .__class__.__name__
        == "APTParser"
    )
    assert (
        RepoConfig(name="a", url="u", package_manager="pacman")
        .get_parser()
        .__class__.__name__
        == "PacmanParser"
    )
    assert (
        RepoConfig(name="a", url="u", package_manager="dnf")
        .get_parser()
        .__class__.__name__
        == "DNFParser"
    )
    assert (
        RepoConfig(name="a", url="u", package_manager="brew")
        .get_parser()
        .__class__.__name__
        == "BrewParser"
    )
    # Unknown manager falls back to APTParser
    assert (
        RepoConfig(name="a", url="u", package_manager="xyz")
        .get_parser()
        .__class__.__name__
        == "APTParser"
    )


def test_package_info_to_package():
    info = PackageInfo(
        name="foo", version="1.0", depends=["a"], conflicts=["b"], installed=True
    )
    pkg = info.to_package()
    assert isinstance(pkg, Package)
    assert pkg.name == "foo"
    assert pkg.version == "1.0"
    assert pkg.status == "installed"


def test_check_package_installed():
    integration = RealRepoIntegration(package_manager="apt")
    with patch.object(
        integration, "get_installed_packages", return_value=[Package(name="vim")]
    ):
        assert integration.check_package_installed("vim") is True
        assert integration.check_package_installed("nope") is False


def test_get_system_info():
    integration = RealRepoIntegration(package_manager="apt")
    with (
        patch.object(
            integration, "get_installed_packages", return_value=[Package(name="x")]
        ),
        patch.object(integration, "get_available_updates", return_value=[]),
    ):
        info = integration.get_system_info()
        assert info["package_manager"] == "apt"
        assert info["installed_packages"] == 1
        assert info["available_updates"] == 0
