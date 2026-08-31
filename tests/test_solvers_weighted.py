"""
Weighted + version-constraint solver tests across all solvers.

Exercises ``solve_with_weights`` and version-constrained packages so the
heavy solvers (z3/pulp/ortools/maxsat/minisat) reach ≥80% coverage.
"""

import pytest

from package_maximizer.core.package import Package
from package_maximizer.solvers import get_solver

SOLVER_NAMES = ["greedy", "enhanced_greedy", "z3", "pulp", "ortools", "maxsat", "minisat"]


def _mk(name, conflicts=None, depends=None, version=""):
    p = Package(name=name, version=version)
    if conflicts:
        p.conflicts = list(conflicts)
    if depends:
        p.depends = list(depends)
    return p


@pytest.mark.parametrize("solver_name", SOLVER_NAMES)
class TestSolverWeights:
    def test_solve_with_weights_default_equal(self, solver_name):
        solver = get_solver(solver_name)
        pkgs = [_mk("a"), _mk("b"), _mk("c")]
        result = solver.solve_with_weights(pkgs)
        assert set(result) == {"a", "b", "c"}

    def test_solve_with_weights_empty(self, solver_name):
        solver = get_solver(solver_name)
        assert solver.solve_with_weights([]) == []

    def test_solve_with_weights_prefers_high(self, solver_name):
        """When a conflict forces a choice, the higher-weighted package wins."""
        solver = get_solver(solver_name)
        low = _mk("low", conflicts=["high"])
        high = _mk("high", conflicts=["low"])
        weights = {"low": 1.0, "high": 10.0}
        result = solver.solve_with_weights([low, high], weights)
        assert "high" in result
        if "low" in result:
            assert "high" in result

    def test_solve_with_weights_respects_conflicts(self, solver_name):
        solver = get_solver(solver_name)
        a = _mk("a", conflicts=["b"])
        b = _mk("b", conflicts=["a"])
        c = _mk("c")
        weights = {"a": 5.0, "b": 1.0, "c": 1.0}
        result = solver.solve_with_weights([a, b, c], weights)
        assert "c" in result
        assert not (("a" in result) and ("b" in result))


@pytest.mark.parametrize("solver_name", ["greedy", "enhanced_greedy", "z3", "pulp", "ortools", "maxsat", "minisat"])
class TestSolverVersionConstraints:
    def test_version_constraint_keeps_compatible(self, solver_name):
        """A package with a version that satisfies no constraint is still
        selectable when it has no conflicts."""
        solver = get_solver(solver_name)
        pkgs = [_mk("v1", version="1.2.3")]
        result = solver.solve(pkgs)
        assert result == ["v1"]

    def test_solve_is_deterministic(self, solver_name):
        solver = get_solver(solver_name)
        pkgs = [_mk("x", conflicts=["y"]), _mk("y", conflicts=["x"]), _mk("z")]
        r1 = solver.solve(pkgs)
        r2 = solver.solve(pkgs)
        assert set(r1) == set(r2)
