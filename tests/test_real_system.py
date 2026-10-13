"""RealRepoIntegration against the host's real package manager.

Each test is skipped unless the corresponding tool is installed, so on CI the
APT tests run on ubuntu runners and the Homebrew tests on macOS runners.
"""

from __future__ import annotations

import shutil

import pytest

from package_maximizer.integrations.real_repo_integration import RealRepoIntegration

pytestmark = pytest.mark.real_system

needs_apt = pytest.mark.skipif(
    not (shutil.which("dpkg") and shutil.which("apt-cache")),
    reason="dpkg/apt-cache not installed",
)
needs_brew = pytest.mark.skipif(not shutil.which("brew"), reason="brew not installed")


@needs_apt
class TestRealAPT:
    def test_installed_packages_are_real_rows(self):
        packages = RealRepoIntegration("apt").get_installed_packages()
        assert packages
        names = {p.name for p in packages}
        assert "dpkg" in names
        assert not any(n.startswith(("Err?", "Name", "|", "+")) for n in names)
        assert all(p.version for p in packages)

    def test_check_package_installed(self):
        integration = RealRepoIntegration("apt")
        assert integration.check_package_installed("dpkg")
        assert not integration.check_package_installed("no-such-package-pm-xyz")

    def test_package_info(self):
        info = RealRepoIntegration("apt").get_package_info("dpkg")
        if info is None:
            pytest.skip("apt cache has no entry for dpkg (lists not downloaded)")
        assert info.name == "dpkg"
        assert info.version

    def test_unknown_package_info_is_none(self):
        assert (
            RealRepoIntegration("apt").get_package_info("no-such-package-pm-xyz")
            is None
        )


@needs_brew
class TestRealBrew:
    def test_installed_packages(self):
        packages = RealRepoIntegration("brew").get_installed_packages()
        assert all(p.status == "installed" for p in packages)
        assert not any(p.name.startswith("==>") for p in packages)
