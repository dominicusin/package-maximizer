"""
MaxSAT Solver - SAT-солвер на основе MaxSAT.

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
    MAXSAT_AVAILABLE = True
except ImportError:
    MAXSAT_AVAILABLE = False


class MaxSatSolver(ConstraintSolver):
    """
    SAT-солвер на основе MaxSAT для решения задачи максимизации пакетов.

    Использует библиотеку python-sat для создания и решения
    задач удовлетворения ограничений в форме CNF.

    Поддерживает:
    - Максимизацию числа выбранных пакетов
    - Учет конфликтов между пакетами
    - Ограничение по времени выполнения
    """

    def __init__(self, time_limit: int = 10000) -> None:
        """
        Инициализация MaxSAT солвера.

        Args:
            time_limit: Ограничение по времени в миллисекундах
        """
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        """
        Решить задачу максимизации множества пакетов.

        Args:
            packages: Итерируемый объект Package

        Returns:
            Список имен выбранных пакетов
        """
        if not MAXSAT_AVAILABLE:
            logger.warning("MaxSAT not available, falling back to GreedySolver")
            from .greedy import GreedySolver
            return GreedySolver().solve(packages)
        
        package_list = list(packages)
        
        if not package_list:
            return []
        
        # Создаем CNF формулу
        cnf = CNF()
        
        # Создаем переменные для каждого пакета
        # x[i] = i+1 (индексация с 1)
        var_map = {pkg.name: i+1 for i, pkg in enumerate(package_list)}
        
        # Добавляем ограничения для конфликтов
        # Если pkg1 конфликтует с pkg2, то не могут быть выбраны оба
        for pkg in package_list:
            for conflict in pkg.conflicts:
                if conflict in var_map:
                    # Добавляем ограничение: не (x[pkg] и x[conflict])
                    # Это эквивалентно: (-x[pkg] или -x[conflict])
                    cnf.add_clause([-var_map[pkg.name], -var_map[conflict]])
        
        # Создаем кардинальное ограничение для максимизации
        # Мы хотим максимизировать сумму x[i], поэтому добавляем
        # ограничение, что сумма >= k для увеличивающегося k
        
        # Используем бинарный поиск для нахождения максимального k
        with Solver(name='g3') as solver:
            # Добавляем CNF ограничения
            solver.add_clause([-var_map[pkg.name]] * len(package_list))  # Пустое ограничение
            
            for clause in cnf.clauses:
                solver.add_clause(clause)
            
            # Пытаемся найти решение с максимальным числом пакетов
            # Используем бинарный поиск
            low = 0
            high = len(package_list)
            best_solution = []
            
            while low <= high:
                mid = (low + high) // 2
                
                # Создаем новое ограничение: сумма x[i] >= mid
                # Это кардинальное ограничение
                card_enc = CardEnc.equals(lits=[var_map[pkg.name] for pkg in package_list], 
                                          bound=mid, 
                                          encoding=EncType.seqcounter)
                
                # Создаем новый солвер для этой итерации
                with Solver(name='g3') as temp_solver:
                    # Добавляем исходные ограничения
                    for clause in cnf.clauses:
                        temp_solver.add_clause(clause)
                    
                    # Добавляем кардинальное ограничение
                    for clause in card_enc.clauses:
                        temp_solver.add_clause(clause)
                    
                    # Пытаемся решить
                    if temp_solver.solve():
                        # Нашли решение с mid пакетами
                        solution = temp_solver.get_model()
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
        
        Для MaxSAT с весами используем подход с последовательным добавлением
        пакетов по убыванию веса.

        Args:
            packages: Итерируемый объект Package
            weights: Словарь весов для пакетов

        Returns:
            Список имен выбранных пакетов
        """
        if not MAXSAT_AVAILABLE:
            logger.warning("MaxSAT not available, falling back to GreedySolver")
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
        
        # Используем жадный подход с MaxSAT для проверки
        selected = []
        selected_names = set()
        
        for pkg in package_list:
            # Проверяем, можно ли добавить этот пакет
            test_packages = selected + [pkg]
            
            # Создаем временный список пакетов
            temp_pkg_list = [
                p for p in package_list
                if p.name in selected_names or p.name == pkg.name
            ]
            
            # Проверяем совместимость
            cnf = CNF()
            var_map = {p.name: i+1 for i, p in enumerate(temp_pkg_list)}
            
            for p in temp_pkg_list:
                for conflict in p.conflicts:
                    if conflict in var_map:
                        cnf.add_clause([-var_map[p.name], -var_map[conflict]])
            
            # Проверяем, есть ли решение
            with Solver(name='g3') as solver:
                for clause in cnf.clauses:
                    solver.add_clause(clause)
                
                if solver.solve():
                    # Можно добавить
                    selected.append(pkg.name)
                    selected_names.add(pkg.name)
        
        return selected
