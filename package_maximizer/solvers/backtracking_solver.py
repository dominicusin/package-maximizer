"""`solvers/backtracking_solver.py` — бэктрекинг-алгоритм решения задачи
максимизации непротиворечивого множества пакетов.

Традиционный рекурсивный перебор со ветвлениями: для каждого пакета решатель
рассматривает два варианта (выбрать / не выбрать), отсекает ветки, когда
появляются конфликты или независящие зависимости не могут быть удовлетворены,
и сохраняет наилучшее по целевой функции найденное подмножество.

Параметры:

* ``conflict_strategy`` — то, делать ли при конфликте: пропускать пакет
  (``skip``) или выталкивать уже выбранный (``remove``).
* ``time_limit`` — верхняя граница в мс; превышение превращает задачу в
  greedy-резервный результат.

Этот солвер дополняет жадные и эвристические (SAT/ILP): он гарантирует
оптимальность по числу выбранных пакетов на графах сравнительно небольшого
размера и служит «золотым стандартом» для бенчмарков.
"""

from __future__ import annotations

import logging
import time
from typing import Iterable

from ..core.interfaces import ConstraintSolver
from ..core.model_encoder import encode_packages

logger = logging.getLogger(__name__)


class BacktrackingSolver(ConstraintSolver):
    """Поиск с возвратом для задачи выбора максимального подмножества пакетов."""

    def __init__(
        self,
        conflict_strategy: str = "skip",
        time_limit: int = 30000,
        objective: str = "count",
    ) -> None:
        self.conflict_strategy = conflict_strategy
        self.time_limit = time_limit
        self.objective = objective

    def _build(self, package_list, weights: dict | None = None):
        constraints = encode_packages(package_list)
        index = {name: i for i, name in enumerate(constraints.packages)}
        names = constraints.packages
        n = len(names)

        # конфликтная матрица: (i, j) = True, если i и j не могут быть верно вместе
        conflict = [[False] * n for _ in range(n)]
        for a, b in constraints.conflicts:
            ia, ib = index.get(a), index.get(b)
            if ia is not None and ib is not None:
                conflict[ia][ib] = conflict[ib][ia] = True

        # зависимости: i => j
        depends: dict[int, list[int]] = {}
        for pkg, deps in constraints.dependencies.items():
            pi = index.get(pkg)
            if pi is None:
                continue
            depends[pi] = [idx for dep in deps if (idx := index.get(dep)) is not None]

        # целевая функция
        if self.objective == "weighted":
            weights_list = (
                [float(weights.get(name, 1.0)) for name in names]
                if weights
                else [1.0] * n
            )
        else:
            weights_list = [1.0] * n

        return names, n, conflict, depends, weights_list

    @staticmethod
    def _conflicts_chosen(
        i: int, chosen: list[bool], conflict: list[list[bool]]
    ) -> bool:
        for j in range(i):
            if chosen[j] and conflict[i][j]:
                return True
        return False

    @staticmethod
    def _deps_satisfied_all(chosen: list[bool], depends: dict[int, list[int]]) -> bool:
        for i, sel in enumerate(chosen):
            if not sel:
                continue
            for d in depends.get(i, []):
                if not chosen[d]:
                    return False
        return True

    def _dfs(
        self,
        i: int,
        chosen: list[bool],
        score: float,
        conflict: list[list[bool]],
        depends: dict[int, list[int]],
        weights: list[float],
        best: list[bool],
        best_score: list[float],
        limit: float,
        start: float,
        time_limit: int,
    ) -> None:
        if time_limit and (time.perf_counter() - start) >= limit:
            return
        n = len(chosen)
        if i == n:
            # лист: валидация зависимостей (обрабатывает циклы корректно)
            if self._deps_satisfied_all(chosen, depends):
                if score > best_score[0]:
                    best_score[0] = score
                    best[:] = chosen[:]
            return

        # 1) пропускаем пакет i
        chosen[i] = False
        self._dfs(
            i + 1,
            chosen,
            score,
            conflict,
            depends,
            weights,
            best,
            best_score,
            limit,
            start,
            time_limit,
        )

        # 2) выбираем i — только если конфликта нет
        if not self._conflicts_chosen(i, chosen, conflict):
            chosen[i] = True
            self._dfs(
                i + 1,
                chosen,
                score + weights[i],
                conflict,
                depends,
                weights,
                best,
                best_score,
                limit,
                start,
                time_limit,
            )
            chosen[i] = False

    def solve(self, packages: Iterable) -> list:
        package_list = list(packages)
        if not package_list:
            return []

        names, n, conflict, depends, weights = self._build(package_list)
        best = [False] * n
        best_score = [-1.0]
        start = time.perf_counter()
        limit = self.time_limit / 1000.0 if self.time_limit else None
        if limit is None:
            limit = 1e30
        self._dfs(
            0,
            [False] * n,
            0.0,
            conflict,
            depends,
            weights,
            best,
            best_score,
            limit,
            start,
            self.time_limit,
        )
        return [names[i] for i in range(n) if best[i]]

    def solve_with_weights(
        self, packages: Iterable, weights: dict | None = None
    ) -> list:
        if weights is None:
            weights = {}
        package_list = list(packages)
        if not package_list:
            return []

        names, n, conflict, depends, w = self._build(package_list, weights=weights)
        best = [False] * n
        best_score = [-1.0]
        start = time.perf_counter()
        limit = self.time_limit / 1000.0 if self.time_limit else None
        if limit is None:
            limit = 1e30
        self._dfs(
            0,
            [False] * n,
            0.0,
            conflict,
            depends,
            w,
            best,
            best_score,
            limit,
            start,
            self.time_limit,
        )
        return [names[i] for i in range(n) if best[i]]
