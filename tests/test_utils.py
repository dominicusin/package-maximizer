"""
Tests for utils module
"""

import tempfile
import time
from pathlib import Path

import pytest

from package_maximizer.core.package import Package
from package_maximizer.utils import CacheManager
from package_maximizer.utils.benchmark import (
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkRunner,
)


class TestCacheManager:
    """Tests for CacheManager"""

    def test_get_set_cache(self):
        """Test basic cache get/set operations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # Test set and get
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

            # Test non-existent key
            assert cache.get("nonexistent") is None

    def test_cache_with_ttl(self):
        """Test cache with TTL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir, default_ttl=1)

            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

            # Wait for TTL to expire
            time.sleep(1.1)
            # Value should be expired
            assert cache.get("key1") is None

    def test_cache_custom_ttl(self):
        """Test cache with custom TTL per item"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir, default_ttl=10)

            cache.set("key1", "value1", ttl=1)
            assert cache.get("key1") == "value1"

            # Wait for custom TTL to expire
            time.sleep(1.1)
            assert cache.get("key1") is None

    def test_delete_cache(self):
        """Test cache deletion"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

            assert cache.delete("key1") == True
            assert cache.get("key1") is None
            assert cache.delete("nonexistent") == False

    def test_clear_cache(self):
        """Test cache clearing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            cache.set("key1", "value1")
            cache.set("key2", "value2")

            count = cache.clear()
            assert count == 2
            assert cache.get("key1") is None
            assert cache.get("key2") is None

    def test_cache_decorator(self):
        """Test cache decorator"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            call_count = 0

            @cache.cached()
            def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y

            # First call
            result1 = expensive_function(1, 2)
            assert result1 == 3
            assert call_count == 1

            # Second call with same args - should use cache
            result2 = expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 1  # Not incremented

            # Different args - should not use cache
            result3 = expensive_function(3, 4)
            assert result3 == 7
            assert call_count == 2

    def test_get_stats(self):
        """Test cache statistics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            cache.set("key1", "value1")
            cache.set("key2", "value2")

            stats = cache.get_stats()

            assert "memory_entries" in stats
            assert "file_entries" in stats
            assert "total_entries" in stats
            assert stats["total_entries"] >= 2

    def test_cleanup_expired(self):
        """Test cleanup of expired entries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir, default_ttl=1)

            cache.set("key1", "value1")
            cache.set("key2", "value2")

            # Wait for TTL to expire
            time.sleep(1.1)

            count = cache.cleanup_expired()
            assert count >= 2


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner"""

    def test_generate_test_packages(self):
        """Test generation of test packages"""
        runner = BenchmarkRunner()

        packages = runner.generate_test_packages(10)
        assert len(packages) == 10

        # Check that all are Package instances
        for pkg in packages:
            assert isinstance(pkg, Package)

    def test_generate_test_packages_with_conflicts(self):
        """Test generation of test packages with conflicts"""
        runner = BenchmarkRunner()

        packages = runner.generate_test_packages(100, conflict_probability=0.5)

        # Check that some packages have conflicts
        packages_with_conflicts = [p for p in packages if p.conflicts]
        assert len(packages_with_conflicts) > 0

    def test_run_benchmark_greedy(self):
        """Test running benchmark with greedy solver"""
        runner = BenchmarkRunner(runs=3)
        packages = runner.generate_test_packages(10)

        result = runner.run_benchmark("greedy", packages)

        assert isinstance(result, BenchmarkResult)
        assert result.solver_name == "greedy"
        assert result.package_count == 10
        assert result.success == True
        assert result.avg_time >= 0
        assert result.selected_count >= 0

    def test_run_benchmark_invalid_solver(self):
        """Test running benchmark with invalid solver"""
        runner = BenchmarkRunner()
        packages = runner.generate_test_packages(10)

        result = runner.run_benchmark("invalid_solver", packages)

        assert isinstance(result, BenchmarkResult)
        assert result.solver_name == "invalid_solver"
        assert result.success == False
        assert result.error is not None

    def test_run_all_benchmarks(self):
        """Test running all benchmarks"""
        runner = BenchmarkRunner(runs=2)

        reports = runner.run_all_benchmarks(
            package_counts=[5, 10], solver_names=["greedy"], conflict_probability=0.1
        )

        assert len(reports) == 2
        assert 5 in reports
        assert 10 in reports

        for count, report in reports.items():
            assert isinstance(report, BenchmarkReport)
            assert len(report.results) == 1
            assert report.results[0].solver_name == "greedy"

    def test_benchmark_report(self):
        """Test benchmark report generation"""
        report = BenchmarkReport()

        result1 = BenchmarkResult(
            solver_name="greedy",
            package_count=10,
            conflict_count=0,
            total_time=0.1,
            avg_time=0.01,
            min_time=0.005,
            max_time=0.02,
            selected_count=10,
            success=True,
        )

        result2 = BenchmarkResult(
            solver_name="z3",
            package_count=10,
            conflict_count=0,
            total_time=0.2,
            avg_time=0.02,
            min_time=0.01,
            max_time=0.03,
            selected_count=10,
            success=True,
        )

        report.add_result(result1)
        report.add_result(result2)

        summary = report.get_summary()

        assert summary["total_solvers"] == 2
        assert summary["best_solver"] == "greedy"
        assert summary["worst_solver"] == "z3"

    def test_export_report_json(self):
        """Test export report to JSON"""
        report = BenchmarkReport()
        result = BenchmarkResult(
            solver_name="greedy",
            package_count=10,
            conflict_count=0,
            total_time=0.1,
            avg_time=0.01,
            min_time=0.005,
            max_time=0.02,
            selected_count=10,
            success=True,
        )
        report.add_result(result)

        json_str = BenchmarkRunner.export_report(report, format="json")

        assert isinstance(json_str, str)
        assert "greedy" in json_str
        assert "avg_time" in json_str

    def test_export_report_csv(self):
        """Test export report to CSV"""
        report = BenchmarkReport()
        result = BenchmarkResult(
            solver_name="greedy",
            package_count=10,
            conflict_count=0,
            total_time=0.1,
            avg_time=0.01,
            min_time=0.005,
            max_time=0.02,
            selected_count=10,
            success=True,
        )
        report.add_result(result)

        csv_str = BenchmarkRunner.export_report(report, format="csv")

        assert isinstance(csv_str, str)
        assert "solver_name" in csv_str
        assert "greedy" in csv_str
