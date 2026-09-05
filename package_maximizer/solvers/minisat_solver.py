"""
MiniSat Solver — SAT-солвер на основе MiniSat с поддержкой зависимостей.

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
    from pysat.solvers import Solver
    from pysat.card import CardEnc, EncType
    from pysat.formula import CNF

    MINISAT_AVAILABLE = True
except ImportError:
    MINISAT_AVAILABLE = False


class MiniSatSolver(ConstraintSolver):
    """SAT-солвер на основе MiniSat для решения задачи максимизации пакетов."""

    def __init__(self, time_limit: int = 10000, solver_name: str = "m22") -> None:
        self.time_limit = time_limit
        self.solver_name = solver_name

    def solve(self, packages: Iterable[Package]) -> list[str]:
        if not MINISAT_AVAILABLE:
            logger.warning("MiniSat not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve(packages)

        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        cnf = CNF()

        var_map = {name: i + 1 for i, name in enumerate(constraints.packages)}

        # Конфликты
        for a, b in constraints.conflicts:
            cnf.append([-var_map[a], -var_map[b]])

        # Зависимости
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                cnf.append([-var_map[pkg], var_map[dep]])

        low = 0
        high = len(constraints.packages)
        best_solution = []

        while low <= high:
            mid = (low + high) // 2

            card_enc = CardEnc.equals(
                lits=[var_map[name] for name in constraints.packages],
                bound=mid,
                encoding=EncType.seqcounter,
            )

            with Solver(name=self.solver_name) as solver:
                for clause in cnf.clauses:
                    solver.add_clause(clause)
                for clause in card_enc.clauses:
                    solver.add_clause(clause)

                if solver.solve():
                    solution = solver.get_model()
                    selected = [
                        name
                        for name in constraints.packages
                        if solution[var_map[name] - 1] > 0
                    ]
                    best_solution = selected
                    low = mid + 1
                else:
                    high = mid - 1

        return best_solution

    def solve_with_weights(
        self,
        packages: Iterable[Package],
        weights: dict[str, float] | None = None,
    ) -> list[str]:
        if not MINISAT_AVAILABLE:
            logger.warning("MiniSat not available, falling back to GreedySolver")
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

        selected = []
        selected_names = set()

        for pkg in package_list:
            if any(c in selected_names for c in (pkg.conflicts or [])):
                continue

            test_packages = [
                p
                for p in package_list
                if p.name in selected_names or p.name == pkg.name
            ]

            cnf = CNF()
            temp_var_map = {p.name: i + 1 for i, p in enumerate(test_packages)}

            # Конфликты
            for a, b in constraints.conflicts:
                if a in temp_var_map and b in temp_var_map:
                    cnf.append([-temp_var_map[a], -temp_var_map[b]])

            # Зависимости
            for p in test_packages:
                for dep in (constraints.dependencies.get(p.name) or []):
                    if dep in temp_var_map:
                        cnf.append([-temp_var_map[p.name], temp_var_map[dep]])

            with Solver(name=self.solver_name) as solver:
                for clause in cnf.clauses:
                    solver.add_clause(clause)

                if solver.solve():
                    selected.append(pkg.name)
                    selected_names.add(pkg.name)

        return selected

    def get_solver_names(self) -> list[str]:
        if not MINISAT_AVAILABLE:
            return []
        from pysat.solvers import Solver

        return Solver().names()
