"""
OR-Tools CP-SAT Solver - CP-SAT-солвер на основе OR-Tools.

Требует установки пакета: pip install ortools
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from ..core.interfaces import ConstraintSolver

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)


try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False


class ORToolsSolver(ConstraintSolver):
    """
    CP-SAT-солвер на основе OR-Tools для решения задачи максимизации пакетов.

    Использует библиотеку OR-Tools CP-SAT для создания и решения
    задач удовлетворения ограничений.

    Поддерживает:
    - Максимизацию числа выбранных пакетов
    - Учет конфликтов между пакетами
    - Ограничение по времени выполнения
    """

    def __init__(self, time_limit: int = 10000) -> None:
        """
        Инициализация OR-Tools солвера.

        Args:
            time_limit: Ограничение по времени в миллисекундах
        """
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        """
        Решить задачу максимизации множества пакетов.

        Args:
            packages: Итерируемый объект Package

        Returns:
            Список имен выбранных пакетов
        """
        if not ORTOOLS_AVAILABLE:
            logger.warning("OR-Tools not available, falling back to GreedySolver")
            from .greedy import GreedySolver
            return GreedySolver().solve(packages)
        
        package_list = list(packages)
        
        if not package_list:
            return []
        
        # Create model
        model = cp_model.CpModel()
        
        # Create binary variables for each package
        # x[pkg_name] = 1 if package is selected, 0 otherwise
        x = {pkg.name: model.NewBoolVar(pkg.name) for pkg in package_list}
        
        # Objective: Maximize the number of selected packages
        model.Maximize(sum(x.values()))
        
        # Constraints: If package A conflicts with package B, they cannot both be selected
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in x:
                    # x[pkg.name] + x[conflict] <= 1
                    model.AddBoolOr([x[pkg.name].Not(), x[conflict].Not()])
        
        # Solve the problem
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit / 1000.0
        
        try:
            status = solver.Solve(model)
        except Exception as e:
            logger.warning(f"OR-Tools solver failed: {e}")
            return self._greedy_fallback(package_list)
        
        # Extract solution
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            selected = [
                pkg.name for pkg in package_list
                if solver.Value(x[pkg.name])
            ]
            return selected
        else:
            logger.warning(f"OR-Tools solver status: {status}")
            return self._greedy_fallback(package_list)

    def solve_with_weights(
        self, 
        packages: Iterable[Package], 
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
        if not ORTOOLS_AVAILABLE:
            logger.warning("OR-Tools not available, falling back to GreedySolver")
            from .greedy import GreedySolver
            return GreedySolver().solve_with_weights(packages, weights)
        
        package_list = list(packages)
        
        if not package_list:
            return []
        
        if weights is None:
            weights = {pkg.name: 1.0 for pkg in package_list}
        
        # Create model
        model = cp_model.CpModel()
        
        # Create binary variables for each package
        x = {pkg.name: model.NewBoolVar(pkg.name) for pkg in package_list}
        
        # Objective: Maximize weighted sum
        # Since CP-SAT works with integers, we scale weights to integers
        int_weights = {name: int(w * 1000) for name, w in weights.items()}
        model.Maximize(sum(x[pkg.name] * int_weights.get(pkg.name, 1000) for pkg in package_list))
        
        # Constraints: Conflict resolution
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in x:
                    model.AddBoolOr([x[pkg.name].Not(), x[conflict].Not()])
        
        # Solve the problem
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit / 1000.0
        
        try:
            status = solver.Solve(model)
        except Exception as e:
            logger.warning(f"OR-Tools solver failed: {e}")
            return self._greedy_fallback(package_list, weights)
        
        # Extract solution
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            selected = [
                pkg.name for pkg in package_list
                if solver.Value(x[pkg.name])
            ]
            return selected
        else:
            logger.warning(f"OR-Tools solver status: {status}")
            return self._greedy_fallback(package_list, weights)

    def _greedy_fallback(self, packages: list[Package], weights: dict[str, float] | None = None) -> list[str]:
        """
        Резервный метод - использование жадного алгоритма при ошибке OR-Tools.
        """
        from .greedy import GreedySolver
        solver = GreedySolver()
        if weights:
            return solver.solve_with_weights(packages, weights)
        return solver.solve(packages)
