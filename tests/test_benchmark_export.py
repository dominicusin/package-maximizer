"""Tests for BenchmarkRunner.export_report and benchmark CLI output."""

from __future__ import annotations

import csv
import io
import json

import pytest

from package_maximizer.utils.benchmark import (
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkRunner,
)


def _fake_report() -> BenchmarkReport:
    report = BenchmarkReport()
    report.add_result(
        BenchmarkResult(
            solver_name="greedy",
            package_count=10,
            conflict_count=2,
            total_time=0.1,
            avg_time=0.02,
            min_time=0.015,
            max_time=0.025,
            selected_count=8,
            success=True,
        )
    )
    return report


class TestBenchmarkExport:
    """Benchmark report export should produce valid JSON and CSV."""

    def test_export_json(self):
        out = BenchmarkRunner.export_report(_fake_report(), format="json")
        data = json.loads(out)
        assert "summary" in data
        assert data["results"][0]["solver_name"] == "greedy"

    def test_export_csv(self):
        out = BenchmarkRunner.export_report(_fake_report(), format="csv")
        reader = csv.DictReader(io.StringIO(out))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["solver_name"] == "greedy"

    def test_export_unknown_raises(self):
        with pytest.raises(ValueError):
            BenchmarkRunner.export_report(_fake_report(), format="xml")
