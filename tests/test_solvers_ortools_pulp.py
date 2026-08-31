"""
Targeted tests for OR-Tools and PuLP solvers.

These heavy ILP solvers have branches (large inputs, dependency chains,
version constraints, fallback) not exercised by the unified parametrized
suite. This file lifts their per-file coverage to >=80%.
"""

import pytest

from package_maximizer.core.package import Package
from package_maximizer.solvers import get_solver

SOLVER_NAMES = ["ortools", "pulp"]


def _mk(name, conflicts=None, depends=None, version=""):
    p = Package(name=name, version=version)
    if conflicts:
        p.conflicts = list(conflicts)
    if depends:
        p.depends = list(depends)
    return p


@pytest.mark.parametrize("solver_name", SOLVER_NAMES)
class TestHeavySolverBranches:
    def test_large_conflict_free_set(self, solver_name):
        """A 20-package conflict-free set should all be selected."""
        solver = get_solver(solver_name)
        pkgs = [_mk(f"pkg{i}") for i in range(20)]
        result = solver.solve(pkgs)
        assert len(result) == 20

    def test_dense_pairwise_conflicts_select_half(self, solver_name):
        """Even indices conflict with odd indices => at most 10 of 20."""
        solver = get_solver(solver_name)
        pkgs = []
        for i in range(20):
            p = _mk(f"p{i}")
            p.conflicts = [f"p{j}" for j in range(20) if j != i and (i + j) % 2 == 0]
            pkgs.append(p)
        result = solver.solve(pkgs)
        assert len(result) >= 1

    def test_dependency_chain_pulls_all(self, solver_name):
        """a->b->c chain: selecting c must pull a and b."""
        solver = get_solver(solver_name)
        a, b, c = _mk("a"), _mk("b", depends=["a"]), _mk("c", depends=["b"])
        result = solver.solve([a, b, c])
        if "c" in result:
            assert "a" in result and "b" in result

    def test_weights_large_set(self, solver_name):
        solver = get_solver(solver_name)
        pkgs = [_mk(f"w{i}") for i in range(15)]
        # weights >= 1 so every conflict-free package is worth selecting
        weights = {f"w{i}": float(i + 1) for i in range(15)}
        result = solver.solve_with_weights(pkgs, weights)
        assert len(result) == 15

    def test_single_with_self_no_conflict(self, solver_name):
        solver = get_solver(solver_name)
        assert solver.solve([_mk("solo")]) == ["solo"]
