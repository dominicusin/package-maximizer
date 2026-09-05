"""
MaxSAT Solver — SAT-солвер на основе MaxSAT с поддержкой зависимостей.

Требует установки пакета: pip install python-sat
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
    from pysat.card import CardEnc, EncType
    from pysat.formula import CNF
    from pysat.solvers import Solver

    MAXSAT_AVAILABLE = True
except ImportError:
    MAXSAT_AVAILABLE = False


class MaxSatSolver(ConstraintSolver):
    """SAT-солвер на основе MaxSAT для решения задачи максимизации пакетов."""

    def __init__(self, time_limit: int = 10000) -> None:
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        if not MAXSAT_AVAILABLE:
            logger.warning("MaxSAT not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve(packages)

        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        cnf = CNF()

        # Создаём переменные для каждого пакета
        var_map = {name: i + 1 for i, name in enumerate(constraints.packages)}

        # Конфликты
        for a, b in constraints.conflicts:
            cnf.append([-var_map[a], -var_map[b]])

        # Зависимости: selected(pkg) => selected(dep)
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                cnf.append([-var_map[pkg], var_map[dep]])

        lits = [var_map[name] for name in constraints.packages]

        best_solution = []
        low = 1
        high = len(constraints.packages)

        while low <= high:
            mid = (low + high) // 2

            neg_lits = [-lit for lit in lits]
            card_enc = CardEnc.atmost(
                lits=neg_lits,
                bound=len(constraints.packages) - mid,
                encoding=EncType.seqcounter,
            )

            with Solver(name="g3") as temp_solver:
                for clause in cnf.clauses:
                    temp_solver.add_clause(clause)
                for clause in card_enc.clauses:
                    temp_solver.add_clause(clause)

                if temp_solver.solve():
                    solution = temp_solver.get_model()
                    best_solution = [
                        name
                        for name in constraints.packages
                        if solution[var_map[name] - 1] > 0
                    ]
                    low = mid + 1
                else:
                    high = mid - 1

        return best_solution

    def solve_with_weights(
        self,
        packages: Iterable[Package],
        weights: dict[str, float] | None = None,
    ) -> list[str]:
        if not MAXSAT_AVAILABLE:
            logger.warning("MaxSAT not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve_with_weights(packages, weights)

        if weights is None:
            return self.solve(packages)

        package_list = sorted(
            list(packages),
            key=lambda p: weights.get(p.name, 1.0),
            reverse=True,
        )

        constraints = encode_packages(package_list)
        var_map = {name: i + 1 for i, name in enumerate(constraints.packages)}

        selected: list[str] = []
        selected_names: set[str] = set()

        for pkg in package_list:
            temp_pkg_list = [
                p
                for p in package_list
                if p.name in selected_names or p.name == pkg.name
            ]

            cnf = CNF()
            temp_var_map = {p.name: i + 1 for i, p in enumerate(temp_pkg_list)}

            # Конфликты
            for a, b in constraints.conflicts:
                if a in temp_var_map and b in temp_var_map:
                    cnf.append([-temp_var_map[a], -temp_var_map[b]])

            # Зависимости
            for p in temp_pkg_list:
                for dep in constraints.dependencies.get(p.name) or []:
                    if dep in temp_var_map:
                        cnf.append([-temp_var_map[p.name], temp_var_map[dep]])

            # Удерживаем выбранные и включаем кандидата
            for name in selected_names:
                cnf.append([temp_var_map[name]])
            cnf.append([temp_var_map[pkg.name]])

            with Solver(name="g3") as solver:
                for clause in cnf.clauses:
                    solver.add_clause(clause)

                if solver.solve():
                    selected.append(pkg.name)
                    selected_names.add(pkg.name)

        return selected
