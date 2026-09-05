"""
Result Analyzer - Анализатор результатов максимизации пакетов.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..core.interfaces import ResultAnalyzer as ResultAnalyzerInterface

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ResultAnalyzer(ResultAnalyzerInterface):
    """
    Анализатор результатов максимизации пакетов.

    Предоставляет методы для анализа:
    - Сравнение установленных и предложенных пакетов
    - Статистика изменений
    - Выявление конфликтов и зависимостей
    """

    def __init__(self) -> None:
        """
        Инициализация анализатора.
        """
        pass

    def analyze(
        self, installed: list[str] | None, proposed: list[str] | None
    ) -> dict[str, Any]:
        """
        Проанализировать результаты максимизации.

        Args:
            installed: Список установленных пакетов
            proposed: Список предложенных пакетов

        Returns:
            Словарь с результатами анализа
        """
        result = {
            "summary": {},
            "changes": {},
            "statistics": {},
        }

        # Преобразуем в множества для удобства
        installed_set = set(installed or [])
        proposed_set = set(proposed or [])

        # Статистика
        result["statistics"]["installed_count"] = len(installed_set)
        result["statistics"]["proposed_count"] = len(proposed_set)

        # Изменения
        to_install = proposed_set - installed_set
        to_remove = installed_set - proposed_set
        unchanged = installed_set & proposed_set

        result["changes"]["to_install"] = sorted(list(to_install))
        result["changes"]["to_remove"] = sorted(list(to_remove))
        result["changes"]["unchanged"] = sorted(list(unchanged))

        result["changes"]["to_install_count"] = len(to_install)
        result["changes"]["to_remove_count"] = len(to_remove)
        result["changes"]["unchanged_count"] = len(unchanged)

        # Сводка
        result["summary"]["total_changes"] = len(to_install) + len(to_remove)
        result["summary"]["net_change"] = len(to_install) - len(to_remove)
        result["summary"]["change_percentage"] = (
            (len(to_install) + len(to_remove)) / len(installed_set) * 100
            if installed_set
            else 0.0
        )

        # Категоризация изменений
        result["summary"]["category"] = self._categorize_changes(
            len(to_install), len(to_remove), len(installed_set)
        )

        return result

    def _categorize_changes(
        self, to_install: int, to_remove: int, total_installed: int
    ) -> str:
        """
        Категоризировать изменения по уровню.

        Args:
            to_install: Количество пакетов для установки
            to_remove: Количество пакетов для удаления
            total_installed: Общее количество установленных пакетов

        Returns:
            Категория изменений
        """
        if total_installed == 0:
            return "fresh_install" if to_install > 0 else "empty"

        total_changes = to_install + to_remove
        percentage = (total_changes / total_installed) * 100

        if percentage == 0:
            return "no_changes"
        elif percentage < 5:
            return "minor"
        elif percentage < 20:
            return "moderate"
        elif percentage < 50:
            return "significant"
        else:
            return "major"

    def get_compatibility_matrix(
        self, proposed: list[str], conflict_graph: dict[str, list[str]]
    ) -> dict[str, Any]:
        """
        Построить матрицу совместимости для предложенных пакетов.

        Args:
            proposed: Список предложенных пакетов
            conflict_graph: Граф конфликтов (пакет -> список конфликтующих)

        Returns:
            Матрица совместимости и статистика
        """
        matrix = {}
        statistics = {
            "compatible_pairs": 0,
            "incompatible_pairs": 0,
            "total_pairs": 0,
        }

        # Создаем матрицу
        for pkg1 in proposed:
            matrix[pkg1] = {}
            for pkg2 in proposed:
                if pkg1 == pkg2:
                    matrix[pkg1][pkg2] = True
                    continue

                # Проверяем конфликты
                has_conflict = pkg2 in conflict_graph.get(
                    pkg1, []
                ) or pkg1 in conflict_graph.get(pkg2, [])

                compatible = not has_conflict
                matrix[pkg1][pkg2] = compatible

                if compatible:
                    statistics["compatible_pairs"] += 1
                else:
                    statistics["incompatible_pairs"] += 1

                statistics["total_pairs"] += 1

        # Вычисляем процент совместимости
        statistics["compatibility_percentage"] = (
            (statistics["compatible_pairs"] / statistics["total_pairs"]) * 100
            if statistics["total_pairs"] > 0
            else 100.0
        )

        return {"matrix": matrix, "statistics": statistics}

    def get_dependency_analysis(
        self, proposed: list[str], dependency_graph: dict[str, list[str]]
    ) -> dict[str, Any]:
        """
        Проанализировать зависимости предложенных пакетов.

        Args:
            proposed: Список предложенных пакетов
            dependency_graph: Граф зависимостей (пакет -> список зависимостей)

        Returns:
            Анализ зависимостей
        """
        analysis = {
            "total_dependencies": 0,
            "satisfied_dependencies": 0,
            "unsatisfied_dependencies": 0,
            "dependency_chain": {},
            "circular_dependencies": [],
        }

        proposed_set = set(proposed)

        # Подсчет зависимостей
        for pkg in proposed:
            deps = dependency_graph.get(pkg, [])
            analysis["total_dependencies"] += len(deps)

            for dep in deps:
                if dep in proposed_set:
                    analysis["satisfied_dependencies"] += 1
                else:
                    analysis["unsatisfied_dependencies"] += 1

        # Вычисление процента
        if analysis["total_dependencies"] > 0:
            analysis["satisfaction_percentage"] = (
                analysis["satisfied_dependencies"]
                / analysis["total_dependencies"]
                * 100
            )
        else:
            analysis["satisfaction_percentage"] = 100.0

        return analysis

    def compare_solvers(
        self, results: dict[str, list[str]], reference: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Сравнить результаты разных солверов.

        Args:
            results: Словарь {имя_солвера: список_пакетов}
            reference: Опциональный эталонный список для сравнения

        Returns:
            Сравнительный анализ
        """
        comparison: dict[str, Any] = {
            "solvers": list(results.keys()),
            "common_packages": [],
            "unique_packages": {},
            "statistics": {},
        }

        # Преобразуем в множества
        solver_sets = {name: set(pkgs) for name, pkgs in results.items()}

        # Общие пакеты
        if solver_sets:
            common = set.intersection(*solver_sets.values())
            comparison["common_packages"] = sorted(list(common))

        # Уникальные пакеты для каждого солвера
        for name, pkg_set in solver_sets.items():
            others = set.union(*[s for n, s in solver_sets.items() if n != name])
            unique = pkg_set - others
            comparison["unique_packages"][name] = sorted(list(unique))

        # Статистика
        comparison["statistics"]["num_solvers"] = len(solver_sets)
        comparison["statistics"]["common_count"] = len(common) if common else 0

        # Сравнение с эталоном
        if reference:
            reference_set = set(reference)
            comparison["reference_comparison"] = {}

            for name, pkg_set in solver_sets.items():
                matches = len(pkg_set & reference_set)
                precision = matches / len(pkg_set) if pkg_set else 0
                recall = matches / len(reference_set) if reference_set else 0

                comparison["reference_comparison"][name] = {
                    "matches": matches,
                    "precision": precision * 100,
                    "recall": recall * 100,
                    "f1_score": (
                        2 * (precision * recall) / (precision + recall) * 100
                        if (precision + recall) > 0
                        else 0
                    ),
                }

        return comparison
