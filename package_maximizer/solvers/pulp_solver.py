"""
PuLP ILP Solver - ILP-солвер на основе PuLP.

Требует установки пакета: pip install pulp
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable, Optional

from ..core.interfaces import ConstraintSolver

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)


try:
    import pulp
    from pulp import LpProblem, LpVariable, LpBinary, LpMaximize, LpStatus, lpSum, value

    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False


class PulPSolver(ConstraintSolver):
    """
    ILP/MIP-солвер на основе PuLP для решения задачи максимизации пакетов.

    Использует библиотеку PuLP для создания и решения задач
    целочисленного линейного программирования.

    Поддерживает:
    - Максимизацию числа выбранных пакетов
    - Учет конфликтов между пакетами
    - Ограничение по времени выполнения
    """

    def __init__(self, solver_name: Optional[str] = None, time_limit: int = 10000) -> None:
        """
        Инициализация PuLP солвера.

        Args:
            solver_name: Имя солвера PuLP (по умолчанию None - использует стандартный)
            time_limit: Ограничение по времени в миллисекундах
        """
        self.solver_name = solver_name
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        """
        Решить задачу максимизации множества пакетов.

        Args:
            packages: Итерируемый объект Package

        Returns:
            Список имен выбранных пакетов
        """
        if not PULP_AVAILABLE:
            logger.warning("PuLP not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve(packages)

        package_list = list(packages)

        if not package_list:
            return []

        # Create problem
        prob = LpProblem("Package_Maximization", LpMaximize)

        # Create binary variables for each package
        # x[pkg_name] = 1 if package is selected, 0 otherwise
        x = LpVariable.dicts(
            "Package", [pkg.name for pkg in package_list], cat=LpBinary
        )

        # Objective: Maximize the number of selected packages
        prob += lpSum([x[pkg.name] for pkg in package_list]), "Total_Packages"

        # Constraints: If package A conflicts with package B, they cannot both be selected
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in x:
                    # x[pkg.name] + x[conflict] <= 1
                    prob += (
                        x[pkg.name] + x[conflict] <= 1,
                        f"Conflict_{pkg.name}_{conflict}",
                    )

        # Solve the problem
        try:
            # Use CBC solver which is typically available
            prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=self.time_limit / 1000))
        except Exception as e:
            logger.warning(f"PuLP solver failed: {e}")
            # Fallback to greedy approach
            return self._greedy_fallback(package_list)

        # Extract solution
        if LpStatus[prob.status] == "Optimal":
            selected = [pkg.name for pkg in package_list if value(x[pkg.name]) == 1]
            return selected
        else:
            # No optimal solution found
            logger.warning(f"PuLP solver status: {prob.status}")
            return self._greedy_fallback(package_list)

    def solve_with_weights(
        self, packages: Iterable[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Решить задачу с учетом весов пакетов.

        Args:
            packages: Итерируемый объект Package
            weights: Словарь весов для пакетов

        Returns:
            Список имен выбранных пакетов
        """
        if not PULP_AVAILABLE:
            logger.warning("PuLP not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve_with_weights(packages, weights)

        package_list = list(packages)

        if not package_list:
            return []

        if weights is None:
            weights = {pkg.name: 1.0 for pkg in package_list}

        # Create problem
        prob = LpProblem("Weighted_Package_Maximization", LpMaximize)

        # Create binary variables for each package
        x = LpVariable.dicts(
            "Package", [pkg.name for pkg in package_list], cat=LpBinary
        )

        # Objective: Maximize weighted sum
        prob += (
            lpSum([x[pkg.name] * weights.get(pkg.name, 1.0) for pkg in package_list]),
            "Total_Weight",
        )

        # Constraints: Conflict resolution
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in x:
                    prob += (
                        x[pkg.name] + x[conflict] <= 1,
                        f"Conflict_{pkg.name}_{conflict}",
                    )

        # Solve the problem
        try:
            prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=self.time_limit / 1000))
        except Exception as e:
            logger.warning(f"PuLP solver failed: {e}")
            return self._greedy_fallback(package_list, weights)

        # Extract solution
        if LpStatus[prob.status] == "Optimal":
            selected = [pkg.name for pkg in package_list if value(x[pkg.name]) == 1]
            return selected
        else:
            logger.warning(f"PuLP solver status: {prob.status}")
            return self._greedy_fallback(package_list, weights)

    def _greedy_fallback(
        self, packages: list[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Резервный метод - использование жадного алгоритма при ошибке PuLP.
        """
        from .greedy import GreedySolver

        solver = GreedySolver()
        if weights:
            return solver.solve_with_weights(packages, weights)
        return solver.solve(packages)
