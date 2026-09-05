"""Tests for dependency support in solvers."""

from __future__ import annotations

import pytest

from package_maximizer.core.package import Package
from package_maximizer.solvers.greedy import GreedySolver
from package_maximizer.solvers.enhanced_greedy import EnhancedGreedySolver


class TestGreedyDependencies:
    """Greedy solver with dependencies."""

    def test_dependency_auto_included(self):
        """If pkg with depends=[dep] is selected, dep must be selected."""
        pkgs = [
            Package(name="nginx", depends=["libnginx"]),
            Package(name="libnginx"),
            Package(name="vim"),
        ]
        result = GreedySolver().solve(pkgs)
        if "nginx" in result:
            assert "libnginx" in result

    def test_chain_dependencies(self):
        """Chain: a -> b -> c."""
        pkgs = [
            Package(name="a", depends=["b"]),
            Package(name="b", depends=["c"]),
            Package(name="c"),
        ]
        result = GreedySolver().solve(pkgs)
        if "a" in result:
            assert "b" in result
            assert "c" in result

    def test_conflict_prevents_both(self):
        """Conflicting packages cannot both be selected."""
        pkgs = [
            Package(name="nginx", conflicts=["apache2"]),
            Package(name="apache2"),
        ]
        result = GreedySolver().solve(pkgs)
        assert not ("nginx" in result and "apache2" in result)

    def test_dependency_and_conflict(self):
        """Dependency + conflict interaction."""
        pkgs = [
            Package(name="nginx", depends=["libnginx"], conflicts=["apache2"]),
            Package(name="libnginx"),
            Package(name="apache2"),
        ]
        result = GreedySolver().solve(pkgs)
        if "nginx" in result:
            assert "libnginx" in result
            assert "apache2" not in result


class TestEnhancedGreedyDependencies:
    """Enhanced greedy solver with dependencies."""

    def test_dependency_auto_included(self):
        pkgs = [
            Package(name="nginx", depends=["libnginx"]),
            Package(name="libnginx"),
        ]
        result = EnhancedGreedySolver().solve(pkgs)
        if "nginx" in result:
            assert "libnginx" in result

    def test_conflict_strategy_skip(self):
        pkgs = [
            Package(name="nginx", conflicts=["apache2"]),
            Package(name="apache2"),
        ]
        result = EnhancedGreedySolver(conflict_strategy="skip").solve(pkgs)
        assert not ("nginx" in result and "apache2" in result)

    def test_real_world_nginx_apache(self):
        """Realistic nginx vs apache scenario."""
        pkgs = [
            Package(name="nginx", depends=["libnginx", "libc"], conflicts=["apache2"]),
            Package(name="apache2", depends=["libapache", "libc"], conflicts=["nginx"]),
            Package(name="libnginx"),
            Package(name="libapache"),
            Package(name="libc"),
        ]
        result = EnhancedGreedySolver().solve(pkgs)
        assert not ("nginx" in result and "apache2" in result)
        if "nginx" in result:
            assert "libnginx" in result
            assert "libc" in result
