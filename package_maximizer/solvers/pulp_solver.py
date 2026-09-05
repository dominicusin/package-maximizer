"""
PuLP ILP Solver — целочисленное линейное программирование.

Поддерживает:
- Максимизацию числа/веса выбранных пакетов
- Учёт конфликтов между пакетами
- Учёт зависимостей (implications)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable, Optional

from ..core.interfaces import ConstraintSolver
from ..core.model_encoder import ModelConstraints, encode_packages

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)

try:
    import pulp
    from pulp import LpBinary, LpMaximize, LpProblem, LpStatus, LpVariable, lpSum, value

    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False


class PulPSolver(ConstraintSolver):
    """ILP/MIP-солвер на основе PuLP."""

    def __init__(
        self, solver_name: Optional[str] = None, time_limit: int = 10000
    ) -> None:
        self.solver_name = solver_name
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        if not PULP_AVAILABLE:
            logger.warning("PuLP not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve(packages)

        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        prob = LpProblem("Package_Maximization", LpMaximize)

        # Бинарные переменные
        x = LpVariable.dicts("Package", constraints.packages, cat=LpBinary)

        # Цель: максимизировать количество
        prob += lpSum(x[name] for name in constraints.packages), "Total_Packages"

        # Конфликты
        for a, b in constraints.conflicts:
            prob += x[a] + x[b] <= 1, f"Conflict_{a}_{b}"

        # Зависимости: selected(pkg) => selected(dep)
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                prob += x[pkg] - x[dep] <= 0, f"Dep_{pkg}_{dep}"

        try:
            prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=self.time_limit / 1000))
        except Exception as e:
            logger.warning(f"PuLP solver failed: {e}")
            return self._greedy_fallback(package_list)

        if LpStatus[prob.status] == "Optimal":
            return [name for name in constraints.packages if value(x[name]) == 1]
        else:
            logger.warning(f"PuLP solver status: {prob.status}")
            return self._greedy_fallback(package_list)

    def solve_with_weights(
        self, packages: Iterable[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        if not PULP_AVAILABLE:
            logger.warning("PuLP not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve_with_weights(packages, weights)

        package_list = list(packages)
        if not package_list:
            return []

        if weights is None:
            weights = {pkg.name: 1.0 for pkg in package_list}

        constraints = encode_packages(package_list)
        prob = LpProblem("Weighted_Package_Maximization", LpMaximize)

        x = LpVariable.dicts("Package", constraints.packages, cat=LpBinary)

        # Цель: максимизировать вес
        prob += (
            lpSum(x[name] * weights.get(name, 1.0) for name in constraints.packages),
            "Total_Weight",
        )

        # Конфликты
        for a, b in constraints.conflicts:
            prob += x[a] + x[b] <= 1, f"Conflict_{a}_{b}"

        # Зависимости
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                prob += x[pkg] - x[dep] <= 0, f"Dep_{pkg}_{dep}"

        try:
            prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=self.time_limit / 1000))
        except Exception as e:
            logger.warning(f"PuLP solver failed: {e}")
            return self._greedy_fallback(package_list, weights)

        if LpStatus[prob.status] == "Optimal":
            return [name for name in constraints.packages if value(x[name]) == 1]
        else:
            logger.warning(f"PuLP solver status: {prob.status}")
            return self._greedy_fallback(package_list, weights)

    def _greedy_fallback(
        self, packages: list[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        from .greedy import GreedySolver

        solver = GreedySolver()
        if weights:
            return solver.solve_with_weights(packages, weights)
        return solver.solve(packages)
