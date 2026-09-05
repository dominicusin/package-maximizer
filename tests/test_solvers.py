"""
Tests for solvers module.
"""

import pytest

from package_maximizer.core.package import Package
from package_maximizer.solvers import (GreedySolver, ORToolsSolver, PulPSolver,
                                       Z3Solver, get_solver)


class TestGreedySolver:
    """Tests for GreedySolver."""

    def test_empty_input(self):
        """Test with empty package list."""
        solver = GreedySolver()
        result = solver.solve([])
        assert result == []

    def test_single_package(self):
        """Test with single package."""
        solver = GreedySolver()
        packages = [Package(name="pkg1")]
        result = solver.solve(packages)
        assert result == ["pkg1"]

    def test_no_conflicts(self):
        """Test with packages that have no conflicts."""
        solver = GreedySolver()
        packages = [
            Package(name="pkg1"),
            Package(name="pkg2"),
            Package(name="pkg3"),
        ]
        result = solver.solve(packages)
        assert len(result) == 3
        assert set(result) == {"pkg1", "pkg2", "pkg3"}

    def test_with_conflicts(self):
        """Test with packages that have conflicts."""
        solver = GreedySolver()
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        result = solver.solve(packages)

        # Should select either pkg1 or pkg2, plus pkg3
        assert len(result) == 2
        assert "pkg3" in result
        assert not ("pkg1" in result and "pkg2" in result)

    def test_with_weights(self):
        """Test greedy solver with weights."""
        solver = GreedySolver()
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        weights = {"pkg1": 1.0, "pkg2": 2.0, "pkg3": 1.0}

        result = solver.solve_with_weights(packages, weights)

        # Should prefer pkg2 (higher weight) over pkg1
        assert "pkg2" in result
        assert "pkg3" in result
        assert len(result) == 2

    def test_remove_conflict_resolution(self):
        """Test with remove conflict resolution strategy."""
        solver = GreedySolver(conflict_resolution="remove")
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]
        pkg3.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        result = solver.solve(packages)

        # With remove strategy, should have at least 1 package
        assert len(result) >= 1


class TestZ3Solver:
    """Tests for Z3Solver."""

    def test_empty_input(self):
        """Test with empty package list."""
        solver = Z3Solver()
        result = solver.solve([])
        assert result == []

    def test_single_package(self):
        """Test with single package."""
        solver = Z3Solver()
        packages = [Package(name="pkg1")]
        result = solver.solve(packages)
        assert result == ["pkg1"]

    def test_no_conflicts(self):
        """Test with packages that have no conflicts."""
        solver = Z3Solver()
        packages = [
            Package(name="pkg1"),
            Package(name="pkg2"),
            Package(name="pkg3"),
        ]
        result = solver.solve(packages)
        assert len(result) == 3
        assert set(result) == {"pkg1", "pkg2", "pkg3"}

    def test_with_conflicts(self):
        """Test with packages that have conflicts."""
        solver = Z3Solver()
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        result = solver.solve(packages)

        # Should select either pkg1 or pkg2, plus pkg3
        assert len(result) == 2
        assert "pkg3" in result
        assert not ("pkg1" in result and "pkg2" in result)


class TestPulPSolver:
    """Tests for PulPSolver."""

    def test_empty_input(self):
        """Test with empty package list."""
        solver = PulPSolver()
        result = solver.solve([])
        assert result == []

    def test_single_package(self):
        """Test with single package."""
        solver = PulPSolver()
        packages = [Package(name="pkg1")]
        result = solver.solve(packages)
        assert result == ["pkg1"]

    def test_no_conflicts(self):
        """Test with packages that have no conflicts."""
        solver = PulPSolver()
        packages = [
            Package(name="pkg1"),
            Package(name="pkg2"),
            Package(name="pkg3"),
        ]
        result = solver.solve(packages)
        assert len(result) == 3
        assert set(result) == {"pkg1", "pkg2", "pkg3"}

    def test_with_conflicts(self):
        """Test with packages that have conflicts."""
        solver = PulPSolver()
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        result = solver.solve(packages)

        # Should select either pkg1 or pkg2, plus pkg3
        assert len(result) == 2
        assert "pkg3" in result
        assert not ("pkg1" in result and "pkg2" in result)


class TestORToolsSolver:
    """Tests for ORToolsSolver."""

    def test_empty_input(self):
        """Test with empty package list."""
        solver = ORToolsSolver()
        result = solver.solve([])
        assert result == []

    def test_single_package(self):
        """Test with single package."""
        solver = ORToolsSolver()
        packages = [Package(name="pkg1")]
        result = solver.solve(packages)
        assert result == ["pkg1"]

    def test_no_conflicts(self):
        """Test with packages that have no conflicts."""
        solver = ORToolsSolver()
        packages = [
            Package(name="pkg1"),
            Package(name="pkg2"),
            Package(name="pkg3"),
        ]
        result = solver.solve(packages)
        assert len(result) == 3
        assert set(result) == {"pkg1", "pkg2", "pkg3"}

    def test_with_conflicts(self):
        """Test with packages that have conflicts."""
        solver = ORToolsSolver()
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        result = solver.solve(packages)

        # Should select either pkg1 or pkg2, plus pkg3
        assert len(result) == 2
        assert "pkg3" in result
        assert not ("pkg1" in result and "pkg2" in result)


class TestSolverRegistry:
    """Tests for solver registry."""

    def test_get_solver_greedy(self):
        """Test getting greedy solver."""
        solver = get_solver("greedy")
        assert isinstance(solver, GreedySolver)

    def test_get_solver_z3(self):
        """Test getting Z3 solver."""
        solver = get_solver("z3")
        assert isinstance(solver, Z3Solver)

    def test_get_solver_pulp(self):
        """Test getting PuLP solver."""
        solver = get_solver("pulp")
        assert isinstance(solver, PulPSolver)

    def test_get_solver_ortools(self):
        """Test getting OR-Tools solver."""
        solver = get_solver("ortools")
        assert isinstance(solver, ORToolsSolver)

    def test_get_solver_case_insensitive(self):
        """Test case-insensitive solver lookup."""
        solver = get_solver("GREEDY")
        assert isinstance(solver, GreedySolver)

    def test_get_solver_invalid(self):
        """Test getting invalid solver."""
        with pytest.raises(ValueError):
            get_solver("invalid_solver")
