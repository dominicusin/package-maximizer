"""
OR-Tools CP-SAT Solver — солвер удовлетворения ограничений.

Поддерживает:
- Максимизацию числа/веса выбранных пакетов
- Учёт конфликтов между пакетами
- Учёт зависимостей (implications)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from ..core.interfaces import ConstraintSolver
from ..core.model_encoder import ModelConstraints, encode_packages

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)

try:
    from ortools.sat.python import cp_model

    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False


class ORToolsSolver(ConstraintSolver):
    """CP-SAT-солвер на основе OR-Tools."""

    def __init__(self, time_limit: int = 10000) -> None:
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        if not ORTOOLS_AVAILABLE:
            logger.warning("OR-Tools not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve(packages)

        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        model = cp_model.CpModel()

        # Бинарные переменные
        x = {name: model.NewBoolVar(name) for name in constraints.packages}

        # Цель: максимизировать количество
        model.Maximize(sum(x.values()))

        # Конфликты
        for a, b in constraints.conflicts:
            model.AddBoolOr([x[a].Not(), x[b].Not()])

        # Зависимости: selected(pkg) => selected(dep)
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                model.AddImplication(x[pkg], x[dep])

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit / 1000.0

        try:
            status = solver.Solve(model)
        except Exception as e:
            logger.warning(f"OR-Tools solver failed: {e}")
            return self._greedy_fallback(package_list)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return [name for name in constraints.packages if solver.Value(x[name])]
        else:
            logger.warning(f"OR-Tools solver status: {status}")
            return self._greedy_fallback(package_list)

    def solve_with_weights(
        self, packages: Iterable[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        if not ORTOOLS_AVAILABLE:
            logger.warning("OR-Tools not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve_with_weights(packages, weights)

        package_list = list(packages)
        if not package_list:
            return []

        if weights is None:
            weights = {pkg.name: 1.0 for pkg in package_list}

        constraints = encode_packages(package_list)
        model = cp_model.CpModel()

        x = {name: model.NewBoolVar(name) for name in constraints.packages}

        # Цель: максимизировать вес (целочисленный)
        int_weights = {name: int(w * 1000) for name, w in weights.items()}
        model.Maximize(
            sum(x[name] * int_weights.get(name, 1000) for name in constraints.packages)
        )

        # Конфликты
        for a, b in constraints.conflicts:
            model.AddBoolOr([x[a].Not(), x[b].Not()])

        # Зависимости
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                model.AddImplication(x[pkg], x[dep])

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit / 1000.0

        try:
            status = solver.Solve(model)
        except Exception as e:
            logger.warning(f"OR-Tools solver failed: {e}")
            return self._greedy_fallback(package_list, weights)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return [name for name in constraints.packages if solver.Value(x[name])]
        else:
            logger.warning(f"OR-Tools solver status: {status}")
            return self._greedy_fallback(package_list, weights)

    def _greedy_fallback(
        self, packages: list[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        from .greedy import GreedySolver

        solver = GreedySolver()
        if weights:
            return solver.solve_with_weights(packages, weights)
        return solver.solve(packages)
