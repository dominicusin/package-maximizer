"""Tests for optional solver behavior when their dependencies are missing."""

from __future__ import annotations

import pytest


def _optional_solver_modules():
    return [
        ("package_maximizer.solvers.maxsat_solver", "MaxSatSolver"),
        ("package_maximizer.solvers.minisat_solver", "MiniSatSolver"),
        ("package_maximizer.solvers.z3_solver", "Z3Solver"),
        ("package_maximizer.solvers.pulp_solver", "PulPSolver"),
        ("package_maximizer.solvers.ortools_solver", "ORToolsSolver"),
    ]


class TestOptionalSolverBehavior:
    """Optional solvers should be instantiable and return list results."""

    @pytest.mark.parametrize("module_name,class_name", _optional_solver_modules())
    def test_solver_instantiable(self, module_name, class_name):
        import importlib

        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        solver = cls()
        assert solver is not None

    @pytest.mark.parametrize("module_name,class_name", _optional_solver_modules())
    def test_solver_returns_list_on_empty_input(self, module_name, class_name):
        import importlib

        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        result = cls().solve([])
        assert isinstance(result, list)
