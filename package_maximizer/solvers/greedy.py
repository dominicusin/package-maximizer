"""
Greedy Solver - Базовый жадный алгоритм максимизации пакетов.

Этот солвер использует простой жадный подход для выбора максимального
числа неконфликтующих пакетов.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from ..core.interfaces import ConstraintSolver

if TYPE_CHECKING:
    from ..core.package import Package


class GreedySolver(ConstraintSolver):
    """
    Базовый жадный алгоритм максимизации множества пакетов.

    Решает задачу выбора максимального числа неконфликтующих пакетов
    с использованием простого жадного подхода.

    Принцип работы:
    - Проходит по списку пакетов в порядке сортировки
    - Добавляет пакет, если он не конфликтует с уже выбранными
    - Блокирует все пакеты, которые конфликтуют с текущим

    Сложность: O(n^2) в худшем случае, где n - количество пакетов.
    """

    def __init__(self, conflict_resolution: str = "skip", time_limit: int = 10000) -> None:
        """
        Инициализация солвера.

        Args:
            conflict_resolution: Стратегия разрешения конфликтов.
                'skip' - пропускать конфликтующие пакеты (по умолчанию)
                'remove' - удалять ранее выбранные конфликтующие пакеты
            time_limit: Ограничение по времени (не используется, для совместимости)
        """
        self.conflict_resolution = conflict_resolution
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        """
        Решить задачу максимизации множества пакетов.

        Args:
            packages: Итерируемый объект Package

        Returns:
            Список имен выбранных пакетов
        """
        # Convert to list to allow multiple iterations
        package_list = list(packages)
        
        # Track selected packages and conflicts
        selected: list[str] = []
        selected_names: set[str] = set()
        blocked: set[str] = set()
        
        # Sort packages by name for deterministic behavior
        package_list.sort(key=lambda p: p.name)
        
        for pkg in package_list:
            # Skip if already selected or blocked
            if pkg.name in selected_names or pkg.name in blocked:
                continue
            
            # Check if this package conflicts with any selected package
            has_conflict = any(
                conflict in selected_names 
                for conflict in pkg.conflicts
            )
            
            if has_conflict:
                if self.conflict_resolution == "remove":
                    # Remove conflicting packages
                    for conflict in pkg.conflicts:
                        if conflict in selected_names:
                            selected_names.remove(conflict)
                            selected.remove(conflict)
                    selected.append(pkg.name)
                    selected_names.add(pkg.name)
                # Default: skip this package
                continue
            
            # Add package to selection
            selected.append(pkg.name)
            selected_names.add(pkg.name)
            
            # Block all packages that conflict with this one
            blocked.update(pkg.conflicts)
        
        return selected

    def solve_with_weights(
        self, 
        packages: Iterable[Package], 
        weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Решить задачу с учетом весов пакетов.

        Args:
            packages: Итерируемый объект Package
            weights: Словарь весов для пакетов (по умолчанию 1.0 для всех)

        Returns:
            Список имен выбранных пакетов
        """
        if weights is None:
            weights = {}
        
        package_list = list(packages)
        
        # Assign default weight of 1.0
        for pkg in package_list:
            if pkg.name not in weights:
                weights[pkg.name] = 1.0
        
        # Sort by weight (descending) for greedy selection
        package_list.sort(key=lambda p: weights.get(p.name, 1.0), reverse=True)
        
        selected: list[str] = []
        selected_names: set[str] = set()
        blocked: set[str] = set()
        
        for pkg in package_list:
            if pkg.name in selected_names or pkg.name in blocked:
                continue
            
            has_conflict = any(
                conflict in selected_names 
                for conflict in pkg.conflicts
            )
            
            if has_conflict:
                if self.conflict_resolution == "remove":
                    for conflict in pkg.conflicts:
                        if conflict in selected_names:
                            selected_names.remove(conflict)
                            selected.remove(conflict)
                    selected.append(pkg.name)
                    selected_names.add(pkg.name)
                continue
            
            selected.append(pkg.name)
            selected_names.add(pkg.name)
            blocked.update(pkg.conflicts)
        
        return selected
