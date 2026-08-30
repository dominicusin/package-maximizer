"""Integration tests for Package Maximizer — end-to-end scenarios."""

from __future__ import annotations

import json

import pytest

from package_maximizer.core.package import Package
from package_maximizer.core.maximizer import PackageMaximizer
from package_maximizer.core.constraints import VersionConstraint, ConstraintParser
from package_maximizer.solvers import get_solver, SOLVER_REGISTRY
from package_maximizer.parsers import get_parser, PARSER_REGISTRY


# ─── End-to-end maximization scenarios ───────────────────────
class TestMaximizerEndToEnd:
    """Test PackageMaximizer with realistic package sets."""

    def test_simple_selection(self):
        """All packages without conflicts should all be selected."""
        packages = [Package(name=f"pkg{i}") for i in range(5)]
        maximizer = PackageMaximizer(solver="greedy")
        result = maximizer.maximize(packages)
        assert len(result) == 5

    def test_mutual_exclusion(self):
        """Two conflicting packages — only one should be selected."""
        pkg_a = Package(name="vim")
        pkg_b = Package(name="emacs")
        pkg_a.conflicts = ["emacs"]
        pkg_b.conflicts = ["vim"]

        maximizer = PackageMaximizer(solver="greedy")
        result = maximizer.maximize([pkg_a, pkg_b])
        assert len(result) == 1
        assert result[0].name in ("vim", "emacs")

    def test_large_package_set(self):
        """Test with 200 packages and random conflicts."""
        import random

        random.seed(42)

        packages = []
        for i in range(200):
            pkg = Package(name=f"pkg-{i:03d}")
            # 5% chance of conflict
            if random.random() < 0.05:
                target = random.randint(0, 199)
                if target != i:
                    pkg.conflicts = [f"pkg-{target:03d}"]
            packages.append(pkg)

        maximizer = PackageMaximizer(solver="greedy")
        result = maximizer.maximize(packages)
        # With ~5% conflict rate, should select most packages
        assert len(result) > 150

    def test_with_weights_prefers_higher(self):
        """Weighted solve should prefer higher-weight packages."""
        pkgs = [
            Package(name="low-priority"),
            Package(name="high-priority"),
        ]
        # Give high-priority a much higher weight
        weights = {"low-priority": 1.0, "high-priority": 100.0}

        # No conflicts, both should be selected
        maximizer = PackageMaximizer(solver="greedy")
        result = maximizer.solve_with_weights(pkgs, weights)
        assert "high-priority" in result
        assert "low-priority" in result

    def test_weighted_conflict_resolution(self):
        """When forced to choose, higher weight should win."""
        pkg_low = Package(name="low", conflicts=["high"])
        pkg_high = Package(name="high", conflicts=["low"])

        weights = {"low": 1.0, "high": 10.0}

        maximizer = PackageMaximizer(solver="greedy")
        result = maximizer.solve_with_weights([pkg_low, pkg_high], weights)
        assert "high" in result
        assert len(result) == 1

    def test_empty_input(self):
        maximizer = PackageMaximizer(solver="greedy")
        result = maximizer.maximize([])
        assert result == []

    def test_solver_switching(self):
        """Test that switching solvers at runtime works."""
        pkgs = [Package(name="a"), Package(name="b"), Package(name="c")]

        maximizer = PackageMaximizer(solver="greedy")
        r1 = maximizer.maximize(pkgs)

        maximizer.set_solver("greedy")
        r2 = maximizer.maximize(pkgs)

        assert len(r1) == len(r2)

    def test_analyze_results(self):
        """Test result analysis."""
        maximizer = PackageMaximizer(solver="greedy")
        analysis = maximizer.analyze(
            installed=["vim", "git"], proposed=["vim", "nano", "git", "curl"]
        )
        assert isinstance(analysis, dict)


# ─── Solver comparison tests ─────────────────────────────────
class TestSolverComparison:
    """Verify all solvers produce consistent results."""

    @pytest.fixture
    def conflict_scenario(self):
        """Create a scenario with known conflicts."""
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
            Package(name="d", conflicts=["e"]),
            Package(name="e", conflicts=["d"]),
        ]
        return pkgs

    @pytest.mark.parametrize("solver_name", ["greedy", "enhanced_greedy"])
    def test_solvers_respect_conflicts(self, solver_name, conflict_scenario):
        """No solver should select conflicting packages together."""
        solver = get_solver(solver_name)
        result = solver.solve(conflict_scenario)

        result_set = set(result)
        # a and b can't both be in result
        assert not ("a" in result_set and "b" in result_set)
        # d and e can't both be in result
        assert not ("d" in result_set and "e" in result_set)

    @pytest.mark.parametrize("solver_name", ["greedy", "enhanced_greedy"])
    def test_solvers_select_non_conflicting(self, solver_name):
        """All solvers should select packages with no conflicts."""
        pkgs = [Package(name=f"pkg{i}") for i in range(10)]
        solver = get_solver(solver_name)
        result = solver.solve(pkgs)
        assert len(result) == 10


# ─── Constraint tests ────────────────────────────────────────
class TestConstraintIntegration:
    """Test constraints in realistic scenarios."""

    def test_version_satisfaction(self):
        """Version constraint should correctly check versions."""
        constraint = VersionConstraint(package="python", operator=">=", version="3.8")
        assert constraint.satisfied_by("3.9")
        assert constraint.satisfied_by("3.10")
        assert not constraint.satisfied_by("3.7")

    def test_dependency_resolution(self):
        """Parser should correctly parse dependency format."""
        dep = ConstraintParser.parse_dependency("numpy>=1.20.0")
        assert dep is not None
        assert dep.package == "numpy"
        assert dep.version_constraint is not None
        assert dep.version_constraint.operator == ">="
        assert dep.version_constraint.satisfied_by("1.21.0")
        assert not dep.version_constraint.satisfied_by("1.19.0")

    def test_complex_version_constraints(self):
        """Test ~ (compatible) operator."""
        c = VersionConstraint(package="lib", operator="~", version="1.2.3")
        # Compatible: >=1.2.3, <1.3.0
        assert c.satisfied_by("1.2.3")
        assert c.satisfied_by("1.2.9")
        assert not c.satisfied_by("1.3.0")
        assert not c.satisfied_by("1.2.2")

    def test_conflict_constraint(self):
        """Conflict constraint should detect conflicts."""
        cc = ConstraintParser.parse_conflict("python<3.8")
        assert cc is not None
        assert cc.conflicts_with("python", "3.7")
        assert not cc.conflicts_with("python", "3.9")
        assert not cc.conflicts_with("ruby", "3.7")


# ─── Parser integration tests ────────────────────────────────
class TestParserIntegration:
    """Test parsers with sample data."""

    def test_apt_parser_with_sample(self):
        parser = get_parser("apt")
        sample = """
Package: vim
Status: install ok installed
Version: 2:8.2.3995-1ubuntu2.1
Depends: vim-common (= 2:8.2.3995-1ubuntu2.1), vim-runtime (= 2:8.2.3995-1ubuntu2.1)
Conflicts: vim-gnome, vim-gtk

Package: nano
Status: install ok installed
Version: 6.2-1
Depends: libc6 (>= 2.34)
Conflicts: nano-tiny
"""
        packages = parser.parse(sample)
        assert len(packages) >= 2
        names = {p.name for p in packages}
        assert "vim" in names
        assert "nano" in names

    def test_brew_parser_with_list_format(self):
        parser = get_parser("brew")
        sample = "vim\nnano\ncurl\ngit\n"
        packages = parser.parse(sample)
        names = {p.name for p in packages}
        assert "vim" in names
        assert "nano" in names

    def test_pacman_parser_with_sample(self):
        parser = get_parser("pacman")
        sample = """extra/vim 2:8.2.3995-1 amd64
    Vi IMproved - enhanced editor
extra/nano 6.2-1 amd64
    small, friendly text editor
"""
        packages = parser.parse(sample)
        names = {p.name for p in packages}
        assert "vim" in names or "nano" in names

    def test_dnf_parser_with_sample(self):
        parser = get_parser("dnf")
        sample = """vim.x86_64    2:8.2.3995-1    @ubuntunano.x86_64    6.2-1    @ubuntu
"""
        packages = parser.parse(sample)
        assert len(packages) >= 1


# ─── Web API integration tests ───────────────────────────────
class TestWebAPIIntegration:
    """Test the web API using Flask test client."""

    @pytest.fixture
    def client(self):
        from package_maximizer.web.app import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def auth_headers(self):
        return {"X-API-Key": "dev-key-change-in-production"}

    def test_health_check(self, client):
        """Health endpoint should work without auth."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_maximize_post(self, client, auth_headers):
        """POST to /api/v1/maximize should return maximized set."""
        resp = client.post(
            "/api/v1/maximize",
            json={"packages": ["vim", "nano", "curl"], "solver": "greedy"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["output_count"] == 3

    def test_maximize_without_auth(self, client):
        """API should reject requests without API key."""
        resp = client.post(
            "/api/v1/maximize",
            json={"packages": ["vim"]},
        )
        assert resp.status_code == 401

    def test_maximize_with_conflicts(self, client, auth_headers):
        """Conflicts should be respected."""
        resp = client.post(
            "/api/v1/maximize",
            json={
                "packages": ["vim", "emacs", "nano"],
                "solver": "greedy",
                "conflicts": [["vim", "emacs"]],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        selected = set(data["selected"])
        assert "nano" in selected
        assert not ("vim" in selected and "emacs" in selected)

    def test_maximize_missing_packages(self, client, auth_headers):
        """Missing packages field should return 400."""
        resp = client.post(
            "/api/v1/maximize",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_list_solvers(self, client, auth_headers):
        """Solver listing should work with auth."""
        resp = client.get("/api/v1/solvers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "greedy" in [s["name"] for s in data["solvers"]]

    def test_list_parsers(self, client, auth_headers):
        """Parser listing should work with auth."""
        resp = client.get("/api/v1/parsers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["parsers"]) >= 4

    def test_benchmark_endpoint(self, client, auth_headers):
        """Benchmark endpoint should return results."""
        resp = client.post(
            "/api/v1/benchmark",
            json={
                "solvers": ["greedy", "enhanced_greedy"],
                "package_count": 50,
                "runs": 2,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) >= 1

    def test_cache_stats(self, client, auth_headers):
        """Cache stats endpoint should work."""
        resp = client.get("/api/v1/cache/stats", headers=auth_headers)
        assert resp.status_code == 200

    def test_404_handler(self, client):
        """Unknown endpoint should return 404."""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_maximize_get_backward_compat(self, client, auth_headers):
        """GET /api/maximize should still work."""
        resp = client.get(
            "/api/maximize?packages=vim,nano&manager=apt&solver=greedy",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    # ─── Input validation (security) ──────────────────────────
    def test_missing_packages_field(self, client, auth_headers):
        resp = client.post("/api/v1/maximize", json={"manager": "apt"}, headers=auth_headers)
        assert resp.status_code == 400
        assert "packages" in resp.get_json()["message"].lower()

    def test_non_string_package_name(self, client, auth_headers):
        resp = client.post(
            "/api/v1/maximize",
            json={"packages": ["vim", 123, "nano"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_empty_package_name(self, client, auth_headers):
        resp = client.post(
            "/api/v1/maximize",
            json={"packages": ["", "vim"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_non_numeric_weight(self, client, auth_headers):
        resp = client.post(
            "/api/v1/maximize",
            json={"packages": ["vim", "nano"], "weights": {"vim": "heavy"}},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_missing_api_key(self, client):
        resp = client.post(
            "/api/v1/maximize",
            json={"packages": ["vim", "nano"]},
        )
        assert resp.status_code == 401

    def test_too_many_packages_rejected(self, client, auth_headers, monkeypatch):
        import sys

        web_mod = sys.modules["package_maximizer.web.app"]
        monkeypatch.setattr(web_mod, "MAX_PACKAGES", 3)
        resp = client.post(
            "/api/v1/maximize",
            json={"packages": ["a", "b", "c", "d"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400
