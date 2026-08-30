"""
Constraints module - Работа с ограничениями пакетов.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VersionConstraint:
    """
    Ограничение версии пакета.
    
    Поддерживает операторы:
    - == (равно)
    - != (не равно)
    - > (больше)
    - >= (больше или равно)
    - < (меньше)
    - <= (меньше или равно)
    - ~ (совместимая версия)
    """
    package: str
    operator: str
    version: str
    
    def __post_init__(self) -> None:
        # Нормализуем оператор
        self.operator = self.operator.strip()
        
    def satisfied_by(self, version: str) -> bool:
        """
        Проверить, удовлетворяет ли версия ограничению.
        
        Args:
            version: Версия для проверки
            
        Returns:
            True, если версия удовлетворяет ограничению
        """
        if not version:
            return False
        
        # Разбираем версии
        constraint_version = self._parse_version(self.version)
        target_version = self._parse_version(version)
        
        if constraint_version is None or target_version is None:
            # Если не можем разобрать, считаем что удовлетворяет
            return True
        
        # Проверяем оператор
        if self.operator == '==':
            return constraint_version == target_version
        elif self.operator == '!=':
            return constraint_version != target_version
        elif self.operator == '>':
            return target_version > constraint_version
        elif self.operator == '>=':
            return target_version >= constraint_version
        elif self.operator == '<':
            return target_version < constraint_version
        elif self.operator == '<=':
            return target_version <= constraint_version
        elif self.operator == '~':
            # Совместимая версия (например, ~1.2.3 означает >=1.2.3, <1.3.0)
            return (target_version >= constraint_version and 
                   target_version < self._get_next_major(constraint_version))
        else:
            # Неизвестный оператор - считаем что удовлетворяет
            return True
    
    def _parse_version(self, version: str) -> tuple | None:
        """
        Разобрать строку версии в кортеж чисел.
        
        Args:
            version: Строка версии
            
        Returns:
            Кортеж чисел или None
        """
        # Убираем префиксы и суффиксы
        version = re.sub(r'^[^0-9]*', '', version)
        version = re.sub(r'[^0-9.]*$', '', version)
        
        if not version:
            return None
        
        # Разбиваем по точкам
        parts = version.split('.')
        
        try:
            return tuple(int(p) for p in parts)
        except ValueError:
            return None
    
    def _get_next_major(self, version: tuple) -> tuple:
        """
        Получить следующую мажорную версию.
        
        Args:
            version: Текущая версия
            
        Returns:
            Следующая мажорная версия
        """
        if len(version) == 1:
            return (version[0] + 1,)
        elif len(version) == 2:
            return (version[0] + 1, 0)
        else:
            return (version[0] + 1, 0, 0)


@dataclass
class DependencyConstraint:
    """
    Ограничение зависимости пакета.
    """
    package: str
    version_constraint: VersionConstraint | None = None
    
    def satisfied_by(self, installed_packages: dict[str, str]) -> bool:
        """
        Проверить, удовлетворяет ли зависимость установленным пакетам.
        
        Args:
            installed_packages: Словарь {имя_пакета: версия}
            
        Returns:
            True, если зависимость удовлетворена
        """
        if self.package not in installed_packages:
            return False
        
        if self.version_constraint:
            return self.version_constraint.satisfied_by(
                installed_packages[self.package]
            )
        
        return True


@dataclass
class ConflictConstraint:
    """
    Ограничение конфликта пакетов.
    """
    package: str
    version_constraint: VersionConstraint | None = None
    
    def conflicts_with(self, package_name: str, version: str = '') -> bool:
        """
        Проверить, конфликтует ли пакет.
        
        Args:
            package_name: Имя пакета для проверки
            version: Версия пакета для проверки
            
        Returns:
            True, если есть конфликт
        """
        if self.package != package_name:
            return False
        
        if self.version_constraint:
            return self.version_constraint.satisfied_by(version)
        
        return True


class ConstraintParser:
    """
    Парсер ограничений пакетов.
    
    Поддерживает форматы:
    - pkg1
    - pkg1 == 1.2.3
    - pkg1 >= 1.2.3
    - pkg1 < 2.0.0
    - pkg1 ~1.2.3
    """
    
    @staticmethod
    def parse_version_constraint(constraint_str: str) -> VersionConstraint | None:
        """
        Разобрать строку ограничения версии.
        
        Args:
            constraint_str: Строка ограничения
            
        Returns:
            Объект VersionConstraint или None
        """
        constraint_str = constraint_str.strip()
        
        if not constraint_str:
            return None
        
        # Пробуем найти оператор
        operators = ['==', '!=', '>=', '<=', '~=', '>', '<', '~']
        
        for op in operators:
            if op in constraint_str:
                parts = constraint_str.split(op, 1)
                if len(parts) == 2:
                    return VersionConstraint(
                        package='',
                        operator=op,
                        version=parts[1].strip()
                    )
        
        return None
    
    @staticmethod
    def parse_dependency(constraint_str: str) -> DependencyConstraint | None:
        """
        Разобрать строку зависимости.
        
        Args:
            constraint_str: Строка зависимости
            
        Returns:
            Объект DependencyConstraint или None
        """
        constraint_str = constraint_str.strip()
        
        if not constraint_str:
            return None
        
        # Разделяем имя пакета и ограничение версии
        # Формат: package_name [operator version]
        
        # Ищем первый оператор
        operators = ['==', '!=', '>=', '<=', '~=', '>', '<', '~']
        
        op_pos = -1
        op_found = None
        
        for op in operators:
            pos = constraint_str.find(op)
            if pos > 0 and (op_pos == -1 or pos < op_pos):
                op_pos = pos
                op_found = op
        
        if op_found and op_pos > 0:
            package_name = constraint_str[:op_pos].strip()
            version_part = constraint_str[op_pos + len(op_found):].strip()
            
            return DependencyConstraint(
                package=package_name,
                version_constraint=VersionConstraint(
                    package='',
                    operator=op_found,
                    version=version_part
                )
            )
        
        return DependencyConstraint(package=constraint_str)
    
    @staticmethod
    def parse_conflict(constraint_str: str) -> ConflictConstraint | None:
        """
        Разобрать строку конфликта.
        
        Args:
            constraint_str: Строка конфликта
            
        Returns:
            Объект ConflictConstraint или None
        """
        constraint_str = constraint_str.strip()
        
        if not constraint_str:
            return None
        
        # Разделяем имя пакета и ограничение версии
        operators = ['==', '!=', '>=', '<=', '~=', '>', '<', '~']
        
        op_pos = -1
        op_found = None
        
        for op in operators:
            pos = constraint_str.find(op)
            if pos > 0 and (op_pos == -1 or pos < op_pos):
                op_pos = pos
                op_found = op
        
        if op_found and op_pos > 0:
            package_name = constraint_str[:op_pos].strip()
            version_part = constraint_str[op_pos + len(op_found):].strip()
            
            return ConflictConstraint(
                package=package_name,
                version_constraint=VersionConstraint(
                    package='',
                    operator=op_found,
                    version=version_part
                )
            )
        
        return ConflictConstraint(package=constraint_str)
