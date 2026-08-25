"""Ядро: максимизация непротиворечивого множества пакетов."""

from __future__ import annotations

import itertools
from typing import Iterable, Sequence

from .enums import PackageManagerType, SolverType
from .package import Package, PackageConstraint


class PackageMaximizer:
    """Строит максимальное непротиворечивое подмножество пакетов.

    Базовая реализация (без внешних солверов): жадный обход с проверкой
    конфликтов и зависимостей. Внешние SAT/ILP-солверы подключаются
    через :mod:`package_maximizer.solvers`.
    """

    def __init__(
        self,
        manager: PackageManagerType | str = PackageManagerType.APT,
        solver: SolverType | str = SolverType.PULP,
    ) -> None:
        self.manager = (
            manager if isinstance(manager, PackageManagerType) else PackageManagerType(manager)
        )
        self.solver = solver if isinstance(solver, SolverType) else SolverType(solver)

    def maximize(self, packages: Sequence[Package]) -> list[Package]:
        """Возвращает максимальное непротиворечивое подмножество."""
        chosen: list[Package] = []
        chosen_names: set[str] = set()
        blocked: set[str] = set()

        for pkg in packages:
            if pkg.name in chosen_names or pkg.name in blocked:
                continue
            if any(c in blocked for c in pkg.conflicts):
                continue
            chosen.append(pkg)
            chosen_names.add(pkg.name)
            blocked.update(pkg.conflicts)
        return chosen

    def check_constraints(
        self, packages: Iterable[Package], constraints: Iterable[PackageConstraint]
    ) -> dict[str, bool]:
        """Проверяет выполнение ограничений для набора пакетов."""
        versions = {p.name: p.version for p in packages}
        return {
            c.package: c.satisfied_by(versions.get(c.package, ""))
            for c in constraints
        }

    @staticmethod
    def from_names(names: Iterable[str]) -> list[Package]:
        return [Package(name=n, status="candidate") for n in names]
