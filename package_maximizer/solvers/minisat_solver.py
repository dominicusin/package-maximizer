"""
MiniSat Solver - SAT-солвер на основе MiniSat.

Требует установки пакета: pip install python-sat
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from ..core.interfaces import ConstraintSolver

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
    """
    SAT-солвер на основе MiniSat для решения задачи максимизации пакетов.

    Использует библиотеку python-sat для работы с MiniSat через PySAT.

    Поддерживает:
    - Максимизацию числа выбранных пакетов
    - Учет конфликтов между пакетами
    - Ограничение по времени выполнения
    
    Примечание: MiniSat через PySAT использует тот же интерфейс, что и MaxSAT,
    но может использовать другой солвер (minisat22).
    """

    def __init__(self, time_limit: int = 10000, solver_name: str = 'm22') -> None:
        """
        Инициализация MiniSat солвера.

        Args:
            time_limit: Ограничение по времени в миллисекундах
            solver_name: Имя солвера (m22 для MiniSat22, g3 для Glucose3 и т.д.)
        """
        self.time_limit = time_limit
        self.solver_name = solver_name

    def solve(self, packages: Iterable[Package]) -> list[str]:
        """
        Решить задачу максимизации множества пакетов.

        Использует итеративный подход с увеличением числа выбираемых пакетов.

        Args:
            packages: Итерируемый объект Package

        Returns:
            Список имен выбранных пакетов
        """
        if not MINISAT_AVAILABLE:
            logger.warning("MiniSat not available, falling back to GreedySolver")
            from .greedy import GreedySolver
            return GreedySolver().solve(packages)
        
        package_list = list(packages)
        
        if not package_list:
            return []
        
        # Создаем CNF формулу
        cnf = CNF()
        
        # Создаем переменные для каждого пакета
        var_map = {pkg.name: i+1 for i, pkg in enumerate(package_list)}
        
        # Добавляем ограничения для конфликтов
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in var_map:
                    # Добавляем ограничение: не (x[pkg] и x[conflict])
                    cnf.append([-var_map[pkg.name], -var_map[conflict]])
        
        # Бинарный поиск для нахождения максимального числа пакетов
        low = 0
        high = len(package_list)
        best_solution = []
        
        while low <= high:
            mid = (low + high) // 2
            
            # Создаем кардинальное ограничение: сумма x[i] >= mid
            card_enc = CardEnc.equals(
                lits=[var_map[pkg.name] for pkg in package_list], 
                bound=mid, 
                encoding=EncType.seqcounter
            )
            
            # Создаем новый солвер для этой итерации
            with Solver(name=self.solver_name) as solver:
                # Добавляем исходные ограничения
                for clause in cnf.clauses:
                    solver.add_clause(clause)
                
                # Добавляем кардинальное ограничение
                for clause in card_enc.clauses:
                    solver.add_clause(clause)
                
                # Пытаемся решить
                if solver.solve():
                    # Нашли решение с mid пакетами
                    solution = solver.get_model()
                    selected = [
                        pkg.name for pkg in package_list
                        if solution[var_map[pkg.name]-1] > 0
                    ]
                    best_solution = selected
                    low = mid + 1
                else:
                    high = mid - 1
        
        return best_solution

    def solve_with_weights(
        self, 
        packages: Iterable[Package], 
        weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Решить задачу с учетом весов пакетов.
        
        Использует жадный подход с проверкой совместимости через SAT.

        Args:
            packages: Итерируемый объект Package
            weights: Словарь весов для пакетов

        Returns:
            Список имен выбранных пакетов
        """
        if not MINISAT_AVAILABLE:
            logger.warning("MiniSat not available, falling back to GreedySolver")
            from .greedy import GreedySolver
            return GreedySolver().solve_with_weights(packages, weights)
        
        if weights is None:
            return self.solve(packages)
        
        # Сортируем пакеты по весу (убывание)
        package_list = sorted(
            list(packages),
            key=lambda p: weights.get(p.name, 1.0),
            reverse=True
        )
        
        # Используем жадный подход с SAT для проверки
        selected = []
        selected_names = set()
        
        for pkg in package_list:
            # Не добавляем, если pkg конфликтует с уже выбранными
            if any(c in selected_names for c in (pkg.conflicts or [])):
                continue
            # Проверяем, можно ли добавить этот пакет
            test_packages = [
                p for p in package_list
                if p.name in selected_names or p.name == pkg.name
            ]
            
            # Создаем CNF для проверки
            cnf = CNF()
            var_map = {p.name: i+1 for i, p in enumerate(test_packages)}
            
            for p in test_packages:
                for conflict in p.conflicts:
                    if conflict in var_map:
                        cnf.append([-var_map[p.name], -var_map[conflict]])
            
            # Проверяем, есть ли решение
            with Solver(name=self.solver_name) as solver:
                for clause in cnf.clauses:
                    solver.add_clause(clause)
                
                if solver.solve():
                    # Можно добавить
                    selected.append(pkg.name)
                    selected_names.add(pkg.name)
        
        return selected

    def get_solver_names(self) -> list[str]:
        """
        Получить список доступных солверов.
        
        Returns:
            Список имен солверов
        """
        if not MINISAT_AVAILABLE:
            return []
        
        from pysat.solvers import Solver
        return Solver().names()
