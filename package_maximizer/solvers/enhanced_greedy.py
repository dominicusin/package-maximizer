"""
Enhanced Greedy Solver — улучшенный жадный алгоритм с поддержкой зависимостей.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from ..core.interfaces import ConstraintSolver
from ..core.model_encoder import encode_packages

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)


class EnhancedGreedySolver(ConstraintSolver):
    """Улучшенный жадный алгоритм для решения задачи максимизации пакетов."""

    def __init__(
        self,
        conflict_strategy: str = "remove",
        time_limit: int = 10000,
    ) -> None:
        self.conflict_strategy = conflict_strategy
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        package_list = list(packages)
        if not package_list:
            return []

        constraints = encode_packages(package_list)
        selected: list[str] = []
        selected_set: set[str] = set()
        blocked: set[str] = set()

        # Сортируем по количеству зависимостей (убывание)
        sorted_packages = sorted(
            constraints.packages,
            key=lambda n: -len(constraints.dependencies.get(n, [])),
        )

        for name in sorted_packages:
            if name in selected_set or name in blocked:
                continue

            # Проверяем конфликты
            has_conflict = any(
                (name == a and b in selected_set) or (name == b and a in selected_set)
                for a, b in constraints.conflicts
            )

            if has_conflict:
                if self.conflict_strategy == "skip":
                    continue
                elif self.conflict_strategy == "remove":
                    # Удаляем конфликтующие
                    to_remove = set()
                    for a, b in constraints.conflicts:
                        if name == a and b in selected_set:
                            to_remove.add(b)
                        elif name == b and a in selected_set:
                            to_remove.add(a)
                    for r in to_remove:
                        selected.remove(r)
                        selected_set.remove(r)

            # Добавляем пакет
            selected.append(name)
            selected_set.add(name)

            # Блокируем конфликтующие
            for a, b in constraints.conflicts:
                if a == name:
                    blocked.add(b)
                elif b == name:
                    blocked.add(a)

            # Автоматически включаем зависимости
            for dep in constraints.dependencies.get(name, []):
                if dep not in selected_set and dep not in blocked:
                    selected.append(dep)
                    selected_set.add(dep)

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
        selected_set: set[str] = set()
        blocked: set[str] = set()

        sorted_packages = sorted(
            constraints.packages,
            key=lambda n: weights.get(n, 1.0),
            reverse=True,
        )

        for name in sorted_packages:
            if name in selected_set or name in blocked:
                continue

            has_conflict = any(
                (name == a and b in selected_set) or (name == b and a in selected_set)
                for a, b in constraints.conflicts
            )

            if has_conflict:
                if self.conflict_strategy == "skip":
                    continue
                elif self.conflict_strategy == "remove":
                    if weights:
                        pkg_w = weights.get(name, 1.0)
                        heavier_conflict = any(
                            weights.get(c, 1.0) > pkg_w
                            for c in _get_conflicts(name, constraints.conflicts)
                            if c in selected_set
                        )
                        if heavier_conflict:
                            continue
                    to_remove = set()
                    for a, b in constraints.conflicts:
                        if name == a and b in selected_set:
                            to_remove.add(b)
                        elif name == b and a in selected_set:
                            to_remove.add(a)
                    for r in to_remove:
                        selected.remove(r)
                        selected_set.remove(r)

            selected.append(name)
            selected_set.add(name)

            for a, b in constraints.conflicts:
                if a == name:
                    blocked.add(b)
                elif b == name:
                    blocked.add(a)

            for dep in constraints.dependencies.get(name, []):
                if dep not in selected_set and dep not in blocked:
                    selected.append(dep)
                    selected_set.add(dep)

        return selected


def _get_conflicts(name: str, conflicts: list[tuple[str, str]]) -> list[str]:
    """Получить список пакетов, конфликтующих с name."""
    result = []
    for a, b in conflicts:
        if a == name:
            result.append(b)
        elif b == name:
            result.append(a)
    return result
