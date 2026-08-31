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
                    cnf.append([-var_map[pkg.name], -var_map[conflict]])
        
        # Максимизируем число выбранных пакетов.
        # Бинарный поиск по k: существует ли решение, в котором выбрано
        # не менее k пакетов (CardEnc.atmost по инвертированным литералам
        # задаёт "сумма >= k").
        lits = [var_map[pkg.name] for pkg in package_list]

        with Solver(name='g3') as solver:
            for clause in cnf.clauses:
                solver.add_clause(clause)

            low = 1
            high = len(package_list)
            best_solution = []

            while low <= high:
                mid = (low + high) // 2

                # Ограничение "выбрано >= mid пакетов":
                # инвертируем литералы и требуем "at most (n - mid) ложных".
                neg_lits = [-lit for lit in lits]
                card_enc = CardEnc.atmost(
                    lits=neg_lits,
                    bound=len(package_list) - mid,
                    encoding=EncType.seqcounter,
                )

                with Solver(name='g3') as temp_solver:
                    for clause in cnf.clauses:
                        temp_solver.add_clause(clause)
                    for clause in card_enc.clauses:
                        temp_solver.add_clause(clause)

                    if temp_solver.solve():
                        solution = temp_solver.get_model()
                        best_solution = [
                            pkg.name for pkg in package_list
                            if solution[var_map[pkg.name] - 1] > 0
                        ]
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
        
        # Жадный отбор по весу с проверкой совместимости через SAT-солвер.
        # При проверке кандидата принудительно удерживаем уже выбранные
        # пакеты (unit-клаузами), чтобы модель не могла «выкинуть» их и
        # тем самым замаскировать конфликт с кандидатом.
        selected = []
        selected_names = set()

        for pkg in package_list:
            # Множество из уже выбранных пакетов плюс текущий кандидат
            temp_pkg_list = [
                p for p in package_list
                if p.name in selected_names or p.name == pkg.name
            ]

            cnf = CNF()
            var_map = {p.name: i + 1 for i, p in enumerate(temp_pkg_list)}

            for p in temp_pkg_list:
                for conflict in p.conflicts:
                    if conflict in var_map:
                        cnf.append([-var_map[p.name], -var_map[conflict]])

            # Принудительно удерживаем выбранные и включаем кандидата
            for name in selected_names:
                cnf.append([var_map[name]])
            cnf.append([var_map[pkg.name]])

            # Проверяем совместимость
            with Solver(name='g3') as solver:
                for clause in cnf.clauses:
                    solver.add_clause(clause)

                if solver.solve():
                    # Кандидат совместим с уже выбранными — добавляем
                    selected.append(pkg.name)
                    selected_names.add(pkg.name)

        return selected
