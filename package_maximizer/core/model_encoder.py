"""Model encoder — преобразует Package-объекты в набор ограничений для солверов.

Формат ограничений:
- conflicts: список пар (A, B) — A и B не могут быть выбраны вместе
- dependencies: словарь {A: [B, C]} — если выбран A, должны быть выбраны B и C
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .package import Package


@dataclass
class ModelConstraints:
    """Нормализованный набор ограничений для солверов."""

    # Множество всех пакетов
    packages: list[str] = field(default_factory=list)

    # Конфликтные пары: A и B не могут быть выбраны вместе
    conflicts: list[tuple[str, str]] = field(default_factory=list)

    # Зависимости: если выбран A, должны быть выбраны B, C, ...
    dependencies: dict[str, list[str]] = field(default_factory=dict)

    def add_conflict(self, a: str, b: str) -> None:
        """Добавить конфликт между пакетами a и b."""
        if a == b:
            return
        pair = (min(a, b), max(a, b))
        if pair not in self.conflicts:
            self.conflicts.append(pair)

    def add_dependency(self, pkg: str, dep: str) -> None:
        """Добавить зависимость: pkg требует dep."""
        if pkg == dep:
            return
        if pkg not in self.dependencies:
            self.dependencies[pkg] = []
        if dep not in self.dependencies[pkg]:
            self.dependencies[pkg].append(dep)
        if pkg not in self.packages:
            self.packages.append(pkg)
        if dep not in self.packages:
            self.packages.append(dep)


def encode_packages(packages: list[Package]) -> ModelConstraints:
    """
    Преобразовать список Package в ModelConstraints.

    Args:
        packages: Список пакетов с depends и conflicts

    Returns:
        ModelConstraints с нормализованными ограничениями
    """
    constraints = ModelConstraints()

    # Регистрируем все пакеты
    for pkg in packages:
        if pkg.name not in constraints.packages:
            constraints.packages.append(pkg.name)

    # Кодируем конфликты
    conflict_pairs: set[tuple[str, str]] = set()
    for pkg in packages:
        for conflict in pkg.conflicts or []:
            if conflict in constraints.packages:
                pair = (min(pkg.name, conflict), max(pkg.name, conflict))
                conflict_pairs.add(pair)
    constraints.conflicts = sorted(conflict_pairs)

    # Кодируем зависимости
    for pkg in packages:
        for dep in pkg.depends or []:
            if dep in constraints.packages:
                constraints.add_dependency(pkg.name, dep)

    return constraints
