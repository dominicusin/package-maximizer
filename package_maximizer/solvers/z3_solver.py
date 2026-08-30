"""
Z3 SMT Solver - SMT-солвер на основе Z3.

Требует установки пакета: pip install z3-solver
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..core.interfaces import ConstraintSolver

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)

try:
    from z3 import Optimize, Bool, sat, unsat, Or, Not
except ImportError:
    # Z3 is optional, provide fallback to greedy
    Z3_AVAILABLE = False
else:
    Z3_AVAILABLE = True


class Z3Solver(ConstraintSolver):
    """
    SMT-солвер на основе Z3 Optimize для решения задачи максимизации пакетов.

    Использует Z3 Optimize для нахождения оптимального решения с поддержкой
    максимизации целевой функции.

    Поддерживает:
    - Максимизацию числа выбранных пакетов
    - Учет конфликтов между пакетами
    - Ограничение по времени выполнения
    - Взвешенные задачи оптимизации

    Сложность: O(n^2) для создания ограничений.
    """

    def __init__(self, timeout: int = 10000) -> None:
        """
        Инициализация Z3 солвера.

        Args:
            timeout: Ограничение по времени в миллисекундах
        """
        self.timeout = timeout

    def solve(self, packages) -> list[str]:
        """
        Решить задачу максимизации множества пакетов.

        Args:
            packages: Итерируемый объект Package

        Returns:
            Список имен выбранных пакетов
        """
        if not Z3_AVAILABLE:
            logger.warning("Z3 not available, falling back to GreedySolver")
            from .greedy import GreedySolver
            return GreedySolver().solve(packages)

        package_list = list(packages)

        if not package_list:
            return []

        # Create Z3 Optimize solver (not Solver) for maximize() support
        solver = Optimize()

        # Create boolean variables for each package
        # x[pkg_name] = True means package is selected
        x = {pkg.name: Bool(pkg.name) for pkg in package_list}

        # Objective: Maximize the number of selected packages
        # For optimization, create a sum of boolean variables
        objective = sum([x[pkg.name] for pkg in package_list])
        solver.maximize(objective)

        # Constraints: If package A conflicts with package B, they cannot both be selected
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in x:
                    # At most one of pkg or conflict can be selected
                    solver.add(Or(Not(x[pkg.name]), Not(x[conflict])))

        # Set timeout
        solver.set("timeout", self.timeout)

        # Check if solution exists
        result = solver.check()

        if result == unsat:
            # No solution found, return empty list
            return []
        elif result == sat:
            # Solution found, extract selected packages
            model = solver.model()
            selected = [
                pkg_name for pkg_name, var in x.items()
                if model.evaluate(var, model_completion=True)
            ]
            return selected
        else:
            # Unknown result
            return []

    def solve_with_weights(
        self,
        packages,
        weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Решить задачу с учетом весов пакетов.

        Args:
            packages: Итерируемый объект Package
            weights: Словарь весов для пакетов

        Returns:
            Список имен выбранных пакетов
        """
        if not Z3_AVAILABLE:
            logger.warning("Z3 not available, falling back to GreedySolver")
            from .greedy import GreedySolver
            return GreedySolver().solve_with_weights(packages, weights)

        from z3 import Real, If

        package_list = list(packages)

        if not package_list:
            return []

        if weights is None:
            weights = {pkg.name: 1.0 for pkg in package_list}

        # Create Z3 Optimize solver
        solver = Optimize()

        # Create boolean variables for each package
        x = {pkg.name: Bool(pkg.name) for pkg in package_list}

        # Create weight variables (as reals for weighted sum)
        # Objective: Maximize weighted sum
        weighted_sum = sum(
            If(x[pkg.name], Real(weights.get(pkg.name, 1.0)), Real(0))
            for pkg in package_list
        )
        solver.maximize(weighted_sum)

        # Constraints: Conflict resolution
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in x:
                    solver.add(Or(Not(x[pkg.name]), Not(x[conflict])))

        # Set timeout
        solver.set("timeout", self.timeout)

        # Check if solution exists
        result = solver.check()

        if result == unsat:
            return []
        elif result == sat:
            model = solver.model()
            selected = [
                pkg_name for pkg_name, var in x.items()
                if model.evaluate(var, model_completion=True)
            ]
            return selected
        else:
            return []