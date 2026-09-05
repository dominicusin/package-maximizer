"""
Greedy Solver — базовый жадный алгоритм с поддержкой зависимостей.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from ..core.interfaces import ConstraintSolver
from ..core.model_encoder import encode_packages

if TYPE_CHECKING:
    from ..core.package import Package


class GreedySolver(ConstraintSolver):
    """Базовый жадный алгоритм максимизации множества пакетов."""

    def __init__(self, conflict_resolution: str = "skip", time_limit: int = 10000) -> None:
        self.conflict_resolution = conflict_resolution
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        selected: list[str] = []
        selected_names: set[str] = set()
        blocked: set[str] = set()

        # Сортируем по имени для детерминированности
        sorted_packages = sorted(constraints.packages)

        for name in sorted_packages:
            if name in selected_names or name in blocked:
                continue

            # Добавляем пакет
            selected.append(name)
            selected_names.add(name)

            # Блокируем конфликтующие
            for a, b in constraints.conflicts:
                if a == name:
                    blocked.add(b)
                elif b == name:
                    blocked.add(a)

            # Автоматически включаем зависимости
            for dep in constraints.dependencies.get(name, []):
                if dep not in selected_names and dep not in blocked:
                    selected.append(dep)
                    selected_names.add(dep)

        return selected

    def solve_with_weights(
        self,
        packages: Iterable[Package],
        weights: dict[str, float] | None = None,
    ) -> list[str]:
        if weights is None:
            weights = {}

        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        selected: list[str] = []
        selected_names: set[str] = set()
        blocked: set[str] = set()

        # Сортируем по весу (убывание)
        sorted_packages = sorted(
            constraints.packages,
            key=lambda n: weights.get(n, 1.0),
            reverse=True,
        )

        for name in sorted_packages:
            if name in selected_names or name in blocked:
                continue

            selected.append(name)
            selected_names.add(name)

            for a, b in constraints.conflicts:
                if a == name:
                    blocked.add(b)
                elif b == name:
                    blocked.add(a)

            for dep in constraints.dependencies.get(name, []):
                if dep not in selected_names and dep not in blocked:
                    selected.append(dep)
                    selected_names.add(dep)

        return selected
