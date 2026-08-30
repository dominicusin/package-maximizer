"""
Enhanced Greedy Solver - Улучшенный жадный алгоритм с обработкой версионных ограничений.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from ..core.interfaces import ConstraintSolver
from ..core.package import Package
from ..core.constraints import VersionConstraint, ConstraintParser

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EnhancedGreedySolver(ConstraintSolver):
    """
    Улучшенный жадный алгоритм для решения задачи максимизации пакетов.
    
    Отличия от базового GreedySolver:
    - Поддержка версионных ограничений
    - Умная обработка зависимостей
    - Поддержка приоритетов пакетов
    
    Алгоритм:
    1. Сортируем пакеты по приоритету (вес, количество зависимостей)
    2. Добавляем пакеты по одному, проверяя ограничения
    3. При конфликте пробуем удалить конфликтующие пакеты
    """

    def __init__(
        self, 
        conflict_strategy: str = "remove",
        time_limit: int = 10000,
        respect_version_constraints: bool = True
    ) -> None:
        """
        Инициализация улучшенного жадного солвера.
        
        Args:
            conflict_strategy: Стратегия разрешения конфликтов
                - 'skip': пропускать конфликтующие пакеты
                - 'remove': удалять ранее добавленные конфликтующие пакеты
            time_limit: Ограничение по времени в миллисекундах
            respect_version_constraints: Учитывать версионные ограничения
        """
        self.conflict_strategy = conflict_strategy
        self.time_limit = time_limit
        self.respect_version_constraints = respect_version_constraints

    def solve(self, packages: Iterable[Package]) -> list[str]:
        """
        Решить задачу максимизации множества пакетов.
        
        Args:
            packages: Итерируемый объект Package
            
        Returns:
            Список имен выбранных пакетов
        """
        package_list = list(packages)
        
        if not package_list:
            return []
        
        # Сортируем пакеты по приоритету
        sorted_packages = self._sort_packages(package_list)
        
        selected: list[str] = []
        selected_set: set[str] = set()
        selected_versions: dict[str, str] = {}
        
        for pkg in sorted_packages:
            # Проверяем конфликты
            if self._has_conflict(pkg, selected_set, selected_versions):
                if self.conflict_strategy == 'skip':
                    continue
                elif self.conflict_strategy == 'remove':
                    # Удаляем конфликтующие пакеты
                    selected = self._remove_conflicting(pkg, selected, selected_set, selected_versions)
            
            # Проверяем зависимости
            if self.respect_version_constraints:
                if not self._check_dependencies(pkg, selected_versions):
                    continue
            
            # Добавляем пакет
            selected.append(pkg.name)
            selected_set.add(pkg.name)
            selected_versions[pkg.name] = pkg.version or ''
        
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
            weights: Словарь весов для пакетов
            
        Returns:
            Список имен выбранных пакетов
        """
        package_list = list(packages)
        
        if not package_list:
            return []
        
        # Сортируем по весу (убывание)
        if weights:
            sorted_packages = sorted(
                package_list,
                key=lambda p: weights.get(p.name, 1.0),
                reverse=True
            )
        else:
            sorted_packages = self._sort_packages(package_list)
        
        selected: list[str] = []
        selected_set: set[str] = set()
        selected_versions: dict[str, str] = {}
        
        for pkg in sorted_packages:
            # Проверяем конфликты
            if self._has_conflict(pkg, selected_set, selected_versions):
                if self.conflict_strategy == 'skip':
                    continue
                elif self.conflict_strategy == 'remove':
                    # Удаляем конфликтующие пакеты
                    selected = self._remove_conflicting(pkg, selected, selected_set, selected_versions)
            
            # Проверяем зависимости
            if self.respect_version_constraints:
                if not self._check_dependencies(pkg, selected_versions):
                    continue
            
            # Добавляем пакет
            selected.append(pkg.name)
            selected_set.add(pkg.name)
            selected_versions[pkg.name] = pkg.version or ''
        
        return selected

    def _sort_packages(self, packages: list[Package]) -> list[Package]:
        """
        Сортировать пакеты по приоритету.
        
        Args:
            packages: Список пакетов
            
        Returns:
            Отсортированный список
        """
        # Приоритет: пакеты с большим количеством зависимостей идут первыми
        return sorted(
            packages,
            key=lambda p: (
                -len(p.depends or []),  # Больше зависимостей = выше приоритет
                p.name  # Алфавитный порядок для стабильности
            )
        )

    def _has_conflict(
        self, 
        pkg: Package, 
        selected_set: set[str],
        selected_versions: dict[str, str]
    ) -> bool:
        """
        Проверить, есть ли конфликт.
        
        Args:
            pkg: Пакет для проверки
            selected_set: Множество выбранных пакетов
            selected_versions: Словарь версий выбранных пакетов
            
        Returns:
            True, если есть конфликт
        """
        for conflict in pkg.conflicts or []:
            if conflict in selected_set:
                # Проверяем версионные ограничения
                if self.respect_version_constraints and pkg.version:
                    constraint = ConstraintParser.parse_conflict(conflict)
                    if constraint:
                        version = selected_versions.get(conflict, '')
                        if constraint.conflicts_with(conflict, version):
                            return True
                else:
                    return True
        
        return False

    def _remove_conflicting(
        self, 
        pkg: Package, 
        selected: list[str],
        selected_set: set[str],
        selected_versions: dict[str, str]
    ) -> list[str]:
        """
        Удалить конфликтующие пакеты.
        
        Args:
            pkg: Пакет, который хотим добавить
            selected: Список выбранных пакетов
            selected_set: Множество выбранных пакетов
            selected_versions: Словарь версий выбранных пакетов
            
        Returns:
            Обновленный список выбранных пакетов
        """
        to_remove = []
        
        for conflict in pkg.conflicts or []:
            if conflict in selected_set:
                to_remove.append(conflict)
        
        # Удаляем конфликтующие пакеты
        new_selected = [p for p in selected if p not in to_remove]
        new_selected_set = set(new_selected)
        new_versions = {k: v for k, v in selected_versions.items() if k not in to_remove}
        
        # Проверяем, что после удаления нет конфликтов
        if not self._has_conflict(pkg, new_selected_set, new_versions):
            return new_selected
        
        return selected

    def _check_dependencies(
        self, 
        pkg: Package, 
        selected_versions: dict[str, str]
    ) -> bool:
        """
        Проверить зависимости пакета.
        
        Args:
            pkg: Пакет для проверки
            selected_versions: Словарь версий выбранных пакетов
            
        Returns:
            True, если все зависимости удовлетворены
        """
        for dep in pkg.depends or []:
            # Разбираем зависимость
            constraint = ConstraintParser.parse_dependency(dep)
            if constraint:
                if constraint.package not in selected_versions:
                    return False
                
                if constraint.version_constraint:
                    version = selected_versions[constraint.package]
                    if not constraint.version_constraint.satisfied_by(version):
                        return False
        
        return True
