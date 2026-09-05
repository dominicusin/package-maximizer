"""Tests for utils.benchmark — BenchmarkRunner and BenchmarkReport."""

from __future__ import annotations

import pytest

from package_maximizer.core.package import Package
from package_maximizer.utils.benchmark import (BenchmarkReport,
                                               BenchmarkResult,
                                               BenchmarkRunner)


class TestBenchmarkResult:
    """BenchmarkResult dataclass."""

    def test_creation(self):
        result = BenchmarkResult(
            solver_name="greedy",
            package_count=10,
            conflict_count=2,
            total_time=0.5,
            avg_time=0.1,
            min_time=0.05,
            max_time=0.15,
            selected_count=8,
            success=True,
        )
        assert result.solver_name == "greedy"
        assert result.success is True
        assert result.error is None


class TestBenchmarkReport:
    """BenchmarkReport methods."""

    def test_add_result(self):
        report = BenchmarkReport()
        result = BenchmarkResult(
            solver_name="greedy",
            package_count=10,
            conflict_count=2,
            total_time=0.5,
            avg_time=0.1,
            min_time=0.05,
            max_time=0.15,
            selected_count=8,
            success=True,
        )
        report.add_result(result)
        assert len(report.results) == 1

    def test_get_summary_empty(self):
        report = BenchmarkReport()
        summary = report.get_summary()
        assert summary == {}

    def test_get_summary_with_results(self):
        report = BenchmarkReport()
        report.add_result(
            BenchmarkResult(
                solver_name="greedy",
                package_count=10,
                conflict_count=2,
                total_time=0.5,
                avg_time=0.1,
                min_time=0.05,
                max_time=0.15,
                selected_count=8,
                success=True,
            )
        )
        report.add_result(
            BenchmarkResult(
                solver_name="z3",
                package_count=10,
                conflict_count=2,
                total_time=1.0,
                avg_time=0.2,
                min_time=0.1,
                max_time=0.3,
                selected_count=8,
                success=True,
            )
        )
        summary = report.get_summary()
        assert summary["total_solvers"] == 2
        assert summary["best_solver"] == "greedy"
        assert summary["worst_solver"] == "z3"


class TestBenchmarkRunner:
    """BenchmarkRunner methods."""

    def test_init_defaults(self):
        runner = BenchmarkRunner()
        assert runner.runs == 5
        assert runner.time_limit == 10000

    def test_init_custom(self):
        runner = BenchmarkRunner(runs=3, time_limit=5000)
        assert runner.runs == 3
        assert runner.time_limit == 5000

    def test_generate_test_packages(self):
        runner = BenchmarkRunner()
        pkgs = runner.generate_test_packages(10)
        assert len(pkgs) == 10
        assert all(isinstance(p, Package) for p in pkgs)

    def test_generate_test_packages_with_conflicts(self):
        runner = BenchmarkRunner()
        pkgs = runner.generate_test_packages(20, conflict_probability=0.5)
        assert len(pkgs) == 20
        has_conflicts = any(p.conflicts for p in pkgs)
        assert has_conflicts

    def test_generate_test_packages_no_conflicts(self):
        runner = BenchmarkRunner()
        pkgs = runner.generate_test_packages(10, conflict_probability=0.0)
        assert len(pkgs) == 10
        assert all(not p.conflicts for p in pkgs)

    def test_print_report(self):
        runner = BenchmarkRunner(runs=1)
        report = BenchmarkReport()
        report.add_result(
            BenchmarkResult(
                solver_name="greedy",
                package_count=10,
                conflict_count=2,
                total_time=0.5,
                avg_time=0.1,
                min_time=0.05,
                max_time=0.15,
                selected_count=8,
                success=True,
            )
        )
        runner.print_report(report)

    def test_print_full_report(self):
        runner = BenchmarkRunner(runs=1)
        reports = {10: BenchmarkReport()}
        reports[10].add_result(
            BenchmarkResult(
                solver_name="greedy",
                package_count=10,
                conflict_count=2,
                total_time=0.5,
                avg_time=0.1,
                min_time=0.05,
                max_time=0.15,
                selected_count=8,
                success=True,
            )
        )
        runner.print_full_report(reports)

    def test_export_report_json(self):
        report = BenchmarkReport()
        report.add_result(
            BenchmarkResult(
                solver_name="greedy",
                package_count=10,
                conflict_count=2,
                total_time=0.5,
                avg_time=0.1,
                min_time=0.05,
                max_time=0.15,
                selected_count=8,
                success=True,
            )
        )
        result = BenchmarkRunner.export_report(report, format="json")
        assert isinstance(result, str)
        assert "greedy" in result

    def test_export_report_csv(self):
        report = BenchmarkReport()
        report.add_result(
            BenchmarkResult(
                solver_name="greedy",
                package_count=10,
                conflict_count=2,
                total_time=0.5,
                avg_time=0.1,
                min_time=0.05,
                max_time=0.15,
                selected_count=8,
                success=True,
            )
        )
        result = BenchmarkRunner.export_report(report, format="csv")
        assert isinstance(result, str)
