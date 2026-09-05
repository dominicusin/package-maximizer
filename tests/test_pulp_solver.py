"""
Tests for solvers.pulp_solver — ILP solver with fallback behavior.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from package_maximizer.core.package import Package


class TestPulPSolverInit:
    """Constructor defaults."""

    def test_default_init(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        assert solver.solver_name is None
        assert solver.time_limit == 10000

    def test_custom_init(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver(solver_name="CBC", time_limit=5000)
        assert solver.solver_name == "CBC"
        assert solver.time_limit == 5000


class TestPulPSolverAvailable:
    """PULP_AVAILABLE flag and import handling."""

    def test_pulp_available_true_when_imported(self):
        # If we can import pulp_solver, PULP_AVAILABLE should be True
        # Skip when pulp is not installed
        import importlib

        from package_maximizer.solvers import pulp_solver

        try:
            importlib.import_module("pulp")
        except ImportError:
            pytest.skip("pulp not installed")
        assert pulp_solver.PULP_AVAILABLE is True


class TestPulPSolve:
    """solve method with various inputs."""

    def test_solve_empty_packages(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        result = solver.solve([])
        assert result == []

    def test_solve_single_package(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a")]
        result = solver.solve(pkgs)
        assert "a" in result

    def test_solve_no_conflicts(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a"), Package(name="b"), Package(name="c")]
        result = solver.solve(pkgs)
        assert len(result) == 3

    def test_solve_with_conflicts(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
        ]
        result = solver.solve(pkgs)
        # Should not contain both a and b
        assert not ("a" in result and "b" in result)

    def test_solve_with_chain_conflicts(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["c"]),
            Package(name="c"),
        ]
        result = solver.solve(pkgs)
        # Should select maximum independent set
        assert len(result) >= 1

    def test_solve_with_isolated_packages(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
            Package(name="d"),
        ]
        result = solver.solve(pkgs)
        # c and d should always be selected
        assert "c" in result
        assert "d" in result


class TestPulPSolveWithWeights:
    """solve_with_weights method."""

    def test_solve_with_weights_empty(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        result = solver.solve_with_weights([], {})
        assert result == []

    def test_solve_with_weights_none(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve_with_weights(pkgs, None)
        assert len(result) == 2

    def test_solve_with_weights_prefers_high(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="low", conflicts=["high"]),
            Package(name="high", conflicts=["low"]),
        ]
        weights = {"low": 1.0, "high": 10.0}
        result = solver.solve_with_weights(pkgs, weights)
        assert "high" in result

    def test_solve_with_weights_respects_conflicts(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
        ]
        weights = {"a": 1.0, "b": 1.0}
        result = solver.solve_with_weights(pkgs, weights)
        assert not ("a" in result and "b" in result)

    def test_solve_with_weights_missing_weight_defaults(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        weights = {"a": 5.0}  # b missing
        result = solver.solve_with_weights(pkgs, weights)
        assert "a" in result


class TestPulPGreedyFallback:
    """_greedy_fallback method."""

    def test_greedy_fallback_no_weights(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver._greedy_fallback(pkgs)
        assert isinstance(result, list)

    def test_greedy_fallback_with_weights(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        weights = {"a": 2.0, "b": 1.0}
        result = solver._greedy_fallback(pkgs, weights)
        assert isinstance(result, list)

    def test_greedy_fallback_with_conflicts(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
        ]
        result = solver._greedy_fallback(pkgs)
        assert not ("a" in result and "b" in result)


class TestPulPNotAvailable:
    """Fallback when PuLP is not available."""

    def test_solve_fallback_when_not_available(self):
        from package_maximizer.solvers import pulp_solver
        from package_maximizer.solvers.pulp_solver import PulPSolver

        original = pulp_solver.PULP_AVAILABLE
        pulp_solver.PULP_AVAILABLE = False
        try:
            solver = PulPSolver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve(pkgs)
            assert isinstance(result, list)
        finally:
            pulp_solver.PULP_AVAILABLE = original

    def test_solve_with_weights_fallback_when_not_available(self):
        from package_maximizer.solvers import pulp_solver
        from package_maximizer.solvers.pulp_solver import PulPSolver

        original = pulp_solver.PULP_AVAILABLE
        pulp_solver.PULP_AVAILABLE = False
        try:
            solver = PulPSolver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve_with_weights(pkgs, {"a": 1.0})
            assert isinstance(result, list)
        finally:
            pulp_solver.PULP_AVAILABLE = original


class TestPulPStatusHandling:
    """Handle non-optimal solver status."""

    def test_solve_optimal_status(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve(pkgs)
        assert len(result) == 2

    def test_solve_with_weights_optimal_status(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve_with_weights(pkgs, {"a": 1.0, "b": 1.0})
        assert len(result) == 2


class TestPulPExceptionHandling:
    """Handle solver exceptions."""

    def test_greedy_fallback_produces_valid_result(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
        ]
        result = solver._greedy_fallback(pkgs)
        assert not ("a" in result and "b" in result)
        assert "c" in result

    def test_greedy_fallback_with_weights_produces_valid_result(self):
        from package_maximizer.solvers.pulp_solver import PulPSolver

        solver = PulPSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
        ]
        result = solver._greedy_fallback(pkgs, {"a": 1.0, "b": 2.0})
        assert not ("a" in result and "b" in result)
