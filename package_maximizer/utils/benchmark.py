"""
Benchmark Runner - Запуск тестов производительности.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from ..core.package import Package
from ..solvers import SOLVER_REGISTRY

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class BenchmarkResult:
    """Результат бенчмарка."""

    solver_name: str
    package_count: int
    conflict_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    selected_count: int
    success: bool
    error: str | None = None


@dataclass
class BenchmarkReport:
    """Отчет о бенчмарках."""

    results: list[BenchmarkResult] = field(default_factory=list)
    best_solver: str | None = None
    worst_solver: str | None = None

    def add_result(self, result: BenchmarkResult) -> None:
        """Добавить результат бенчмарка."""
        self.results.append(result)

    def get_summary(self) -> dict[str, Any]:
        """Получить сводку отчета."""
        if not self.results:
            return {}

        # Сортируем по среднему времени
        sorted_results = sorted(self.results, key=lambda r: r.avg_time)

        # Находим лучший и худший
        self.best_solver = sorted_results[0].solver_name if sorted_results else None
        self.worst_solver = sorted_results[-1].solver_name if sorted_results else None

        return {
            "total_solvers": len(self.results),
            "best_solver": self.best_solver,
            "best_time": sorted_results[0].avg_time if sorted_results else 0,
            "worst_solver": self.worst_solver,
            "worst_time": sorted_results[-1].avg_time if sorted_results else 0,
            "average_time": sum(r.avg_time for r in self.results) / len(self.results),
        }


class BenchmarkRunner:
    """
    Запуск бенчмарков для солверов Package Maximizer.

    Поддерживает:
    - Тестирование разных солверов
    - Генерацию тестовых данных
    - Замеры времени выполнения
    - Сравнение результатов
    """

    def __init__(self, runs: int = 5, time_limit: int = 10000) -> None:
        """
        Инициализация runners бенчмарков.

        Args:
            runs: Количество запусков на каждый тест
            time_limit: Ограничение по времени в миллисекундах
        """
        self.runs = runs
        self.time_limit = time_limit

    def generate_test_packages(
        self, count: int, conflict_probability: float = 0.1, max_conflicts: int = 3
    ) -> list[Package]:
        """
        Сгенерировать тестовые пакеты.

        Args:
            count: Количество пакетов
            conflict_probability: Вероятность конфликта между пакетами
            max_conflicts: Максимальное количество конфликтов у пакета

        Returns:
            Список тестовых пакетов
        """
        import random

        packages = []
        for i in range(count):
            pkg = Package(
                name=f"test-pkg-{i:04d}", version=f"1.{i}.0", status="candidate"
            )

            # Добавление конфликтов
            if random.random() < conflict_probability:
                num_conflicts = random.randint(1, max_conflicts)
                conflicts = []

                for _ in range(num_conflicts):
                    # Выбираем случайный пакет для конфликта
                    conflict_idx = random.randint(0, count - 1)
                    conflict_name = f"test-pkg-{conflict_idx:04d}"
                    if conflict_name != pkg.name and conflict_name not in conflicts:
                        conflicts.append(conflict_name)

                pkg.conflicts = conflicts

            packages.append(pkg)

        return packages

    def run_benchmark(
        self,
        solver_name: str,
        packages: list[Package],
        weights: dict[str, float] | None = None,
    ) -> BenchmarkResult:
        """
        Запустить бенчмарк для одного солвера.

        Args:
            solver_name: Имя солвера
            packages: Список пакетов
            weights: Веса пакетов (опционально)

        Returns:
            Результат бенчмарка
        """
        if solver_name not in SOLVER_REGISTRY:
            return BenchmarkResult(
                solver_name=solver_name,
                package_count=len(packages),
                conflict_count=0,
                total_time=0,
                avg_time=0,
                min_time=0,
                max_time=0,
                selected_count=0,
                success=False,
                error=f"Solver '{solver_name}' not found",
            )

        solver_class = SOLVER_REGISTRY[solver_name]

        # Подсчет конфликтов
        conflict_count = sum(len(pkg.conflicts) for pkg in packages)

        times = []
        selected_counts = []
        error_msg = None

        for run in range(self.runs):
            try:
                solver = solver_class(time_limit=self.time_limit)

                start_time = time.time()

                if weights:
                    result = solver.solve_with_weights(packages, weights)
                else:
                    result = solver.solve(packages)

                end_time = time.time()

                elapsed = end_time - start_time
                times.append(elapsed)
                selected_counts.append(len(result))

            except Exception as e:
                error_msg = str(e)
                times.append(float("inf"))
                selected_counts.append(0)

        # Вычисляем статистику
        valid_times = [t for t in times if t != float("inf")]

        if not valid_times:
            return BenchmarkResult(
                solver_name=solver_name,
                package_count=len(packages),
                conflict_count=conflict_count,
                total_time=0,
                avg_time=0,
                min_time=0,
                max_time=0,
                selected_count=0,
                success=False,
                error=error_msg,
            )

        return BenchmarkResult(
            solver_name=solver_name,
            package_count=len(packages),
            conflict_count=conflict_count,
            total_time=sum(times),
            avg_time=sum(valid_times) / len(valid_times),
            min_time=min(valid_times),
            max_time=max(valid_times),
            selected_count=sum(selected_counts) // len(selected_counts),
            success=True,
            error=None,
        )

    def run_all_benchmarks(
        self,
        package_counts: list[int] = [10, 50, 100, 200],
        solver_names: list[str] | None = None,
        conflict_probability: float = 0.1,
    ) -> dict[int, BenchmarkReport]:
        """
        Запустить бенчмарки для всех солверов с разными размерами пакетов.

        Args:
            package_counts: Список размеров пакетов для тестирования
            solver_names: Список имен солверов (по умолчанию все)
            conflict_probability: Вероятность конфликтов

        Returns:
            Словарь отчетов по размерам пакетов
        """
        if solver_names is None:
            solver_names = list(SOLVER_REGISTRY.keys())

        reports = {}

        for count in package_counts:
            # Генерируем тестовые пакеты
            packages = self.generate_test_packages(count, conflict_probability)

            report = BenchmarkReport()

            for solver_name in solver_names:
                result = self.run_benchmark(solver_name, packages)
                report.add_result(result)

            reports[count] = report

        return reports

    def print_report(self, report: BenchmarkReport) -> None:
        """
        Вывести отчет о бенчмарке.

        Args:
            report: Отчет о бенчмарке
        """
        summary = report.get_summary()

        print(f"\n{'='*70}")
        print(f"Benchmark Report")
        print(f"{'='*70}")
        print(f"Total solvers: {summary['total_solvers']}")
        print(f"Best solver: {summary['best_solver']} ({summary['best_time']:.4f}s)")
        print(f"Worst solver: {summary['worst_solver']} ({summary['worst_time']:.4f}s)")
        print(f"Average time: {summary['average_time']:.4f}s")
        print(f"{'='*70}")

        print(
            f"\n{'Solver':<15} {'Avg Time':>12} {'Min':>12} {'Max':>12} {'Selected':>10} {'Status':>10}"
        )
        print("-" * 70)

        for result in report.results:
            status = "✓" if result.success else "✗"
            print(
                f"{result.solver_name:<15} {result.avg_time:>12.4f} {result.min_time:>12.4f} {result.max_time:>12.4f} {result.selected_count:>10} {status:>10}"
            )

        print("-" * 70)

    def print_full_report(self, reports: dict[int, BenchmarkReport]) -> None:
        """
        Вывести полный отчет о всех бенчмарках.

        Args:
            reports: Словарь отчетов
        """
        for count, report in sorted(reports.items()):
            print(f"\n{'#'*70}")
            print(f"# Packages: {count}")
            print(f"{'#'*70}")
            self.print_report(report)

    @staticmethod
    def export_report(report: BenchmarkReport, format: str = "json") -> str:
        """
        Экспортировать отчет в указанном формате.

        Args:
            report: Отчет о бенчмарке
            format: Формат экспорта ('json', 'csv')

        Returns:
            Строка с данными отчета
        """
        import json

        if format == "json":
            data = {
                "summary": report.get_summary(),
                "results": [
                    {
                        "solver_name": r.solver_name,
                        "package_count": r.package_count,
                        "conflict_count": r.conflict_count,
                        "avg_time": r.avg_time,
                        "min_time": r.min_time,
                        "max_time": r.max_time,
                        "selected_count": r.selected_count,
                        "success": r.success,
                        "error": r.error,
                    }
                    for r in report.results
                ],
            }
            return json.dumps(data, indent=2)

        elif format == "csv":
            lines = [
                "solver_name,package_count,conflict_count,avg_time,min_time,max_time,selected_count,success"
            ]
            for r in report.results:
                line = f"{r.solver_name},{r.package_count},{r.conflict_count},{r.avg_time},{r.min_time},{r.max_time},{r.selected_count},{r.success}"
                lines.append(line)
            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported format: {format}")
