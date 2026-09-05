"""
Z3 SMT Solver — оптимизационный солвер на основе Z3.

Поддерживает:
- Максимизацию числа/веса выбранных пакетов
- Учёт конфликтов между пакетами
- Учёт зависимостей (implications)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..core.interfaces import ConstraintSolver
from ..core.model_encoder import ModelConstraints, encode_packages

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)

try:
    from z3 import Bool, If, Not, Optimize, Or, RealVal, sat, unsat

    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False


class Z3Solver(ConstraintSolver):
    """SMT-солвер на основе Z3 Optimize."""

    def __init__(self, timeout: int = 10000) -> None:
        self.timeout = timeout

    def solve(self, packages) -> list[str]:
        if not Z3_AVAILABLE:
            logger.warning("Z3 not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve(packages)

        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        solver = Optimize()

        # Создаём булевы переменные
        x = {name: Bool(name) for name in constraints.packages}

        # Цель: максимировать количество выбранных пакетов
        solver.maximize(sum(x[name] for name in constraints.packages))

        # Конфликты: не могут быть выбраны вместе
        for a, b in constraints.conflicts:
            solver.add(Or(Not(x[a]), Not(x[b])))

        # Зависимости: если выбран pkg, должны быть выбраны зависимости
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                # selected(pkg) => selected(dep)
                solver.add(Or(Not(x[pkg]), x[dep]))

        solver.set("timeout", self.timeout)

        result = solver.check()
        if result == unsat:
            return []
        elif result == sat:
            model = solver.model()
            return [
                name
                for name, var in x.items()
                if model.evaluate(var, model_completion=True)
            ]
        else:
            return []

    def solve_with_weights(
        self, packages, weights: dict[str, float] | None = None
    ) -> list[str]:
        if not Z3_AVAILABLE:
            logger.warning("Z3 not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve_with_weights(packages, weights)

        package_list = list(packages)
        if not package_list:
            return []

        if weights is None:
            weights = {pkg.name: 1.0 for pkg in package_list}

        constraints = encode_packages(package_list)
        solver = Optimize()

        x = {name: Bool(name) for name in constraints.packages}

        # Цель: максимизировать взвешенную сумму
        weighted_sum = sum(
            If(x[name], RealVal(weights.get(name, 1.0)), RealVal(0))
            for name in constraints.packages
        )
        solver.maximize(weighted_sum)

        # Конфликты
        for a, b in constraints.conflicts:
            solver.add(Or(Not(x[a]), Not(x[b])))

        # Зависимости
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                solver.add(Or(Not(x[pkg]), x[dep]))

        solver.set("timeout", self.timeout)

        result = solver.check()
        if result == unsat:
            return []
        elif result == sat:
            model = solver.model()
            return [
                name
                for name, var in x.items()
                if model.evaluate(var, model_completion=True)
            ]
        else:
            return []
