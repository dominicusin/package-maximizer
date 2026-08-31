"""
Unified solver tests — one set of fixtures exercised across ALL solvers.

Drives every registered solver via ``get_solver(name)`` so coverage stays
uniform across greedy / enhanced_greedy / z3 / pulp / ortools / maxsat / minisat.
Heavy solvers (z3, pulp, ortools, maxsat, minisat) require optional deps; they
are skipped gracefully when missing, but in CI all are installed.
"""

import pytest

from package_maximizer.core.package import Package
from package_maximizer.solvers import SOLVER_REGISTRY, get_solver

# All solver names we expect to be able to instantiate in CI.
SOLVER_NAMES = [
    "greedy",
    "enhanced_greedy",
    "z3",
    "pulp",
    "ortools",
    "maxsat",
    "minisat",
]


def _mk(name, conflicts=None, depends=None, version=""):
    p = Package(name=name, version=version)
    if conflicts:
        p.conflicts = list(conflicts)
    if depends:
        p.depends = list(depends)
    return p


# --- Fixtures shared across every solver -----------------------------------


def conflict_fixture():
    """Three packages, pkg1<->pkg2 conflict, pkg3 independent."""
    pkg1 = _mk("pkg1", conflicts=["pkg2"])
    pkg2 = _mk("pkg2", conflicts=["pkg1"])
    pkg3 = _mk("pkg3")
    return [pkg1, pkg2, pkg3]


def dependency_fixture():
    """pkg2 depends on pkg1; picking pkg2 must pull pkg1."""
    pkg1 = _mk("pkg1")
    pkg2 = _mk("pkg2", depends=["pkg1"])
    pkg3 = _mk("pkg3", conflicts=["pkg2"])
    return [pkg1, pkg2, pkg3]


def all_conflict_fixture():
    """Every package conflicts with every other — only one can be chosen."""
    a = _mk("a", conflicts=["b", "c"])
    b = _mk("b", conflicts=["a", "c"])
    c = _mk("c", conflicts=["a", "b"])
    return [a, b, c]


def empty_fixture():
    return []


def single_fixture():
    return [_mk("only")]


# --- Parametrized cross-solver tests ----------------------------------------


@pytest.mark.parametrize("solver_name", SOLVER_NAMES)
class TestSolversUnified:
    def test_empty_input(self, solver_name):
        solver = get_solver(solver_name)
        assert solver.solve(empty_fixture()) == []

    def test_single_package(self, solver_name):
        solver = get_solver(solver_name)
        result = solver.solve(single_fixture())
        assert result == ["only"]

    def test_pairwise_conflict_keeps_independent(self, solver_name):
        solver = get_solver(solver_name)
        result = solver.solve(conflict_fixture())
        assert "pkg3" in result
        # pkg1 and pkg2 conflict — at most one of them
        assert not (("pkg1" in result) and ("pkg2" in result))
        assert len(result) == 2

    def test_dependency_is_satisfied(self, solver_name):
        solver = get_solver(solver_name)
        result = solver.solve(dependency_fixture())
        # If pkg2 is selected, pkg1 must also be present (dependency).
        if "pkg2" in result:
            assert "pkg1" in result

    def test_all_conflict_picks_one(self, solver_name):
        solver = get_solver(solver_name)
        result = solver.solve(all_conflict_fixture())
        assert len(result) == 1
        assert result[0] in {"a", "b", "c"}

    def test_result_is_maximal_nonempty(self, solver_name):
        """A solver should never return fewer packages than greedy could,
        given no conflicts (all 3 selectable)."""
        solver = get_solver(solver_name)
        pkgs = [_mk("x1"), _mk("x2"), _mk("x3")]
        result = solver.solve(pkgs)
        assert set(result) == {"x1", "x2", "x3"}


def test_registry_lists_all_expected_solvers():
    registered = set(SOLVER_REGISTRY.keys())
    assert registered >= set(SOLVER_NAMES)


def test_get_solver_unknown_raises():
    with pytest.raises((ValueError, KeyError, ImportError)):
        get_solver("does_not_exist")
