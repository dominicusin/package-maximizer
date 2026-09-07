"""
Tests for the new CLI commands: analyze and compare.

These commands provide conflict analysis and multi-solver comparison.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from package_maximizer.cli.main import cli

# --- Analyze command tests -------------------------------------------------


def test_analyze_basic_text():
    """analyze with two packages prints summary."""
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "pkg1", "pkg2"])
    assert result.exit_code == 0, result.output
    assert "Package Analysis" in result.output
    assert "pkg1" in result.output


def test_analyze_json_output():
    """analyze --output json returns JSON."""
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "pkg1", "pkg2", "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["total_packages"] == 2
    assert "selected" in data
    assert "bottlenecks" in data
    assert "solver" in data


def test_analyze_empty_packages():
    """analyze with no packages exits with error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze"])
    assert result.exit_code != 0


def test_analyze_invalid_manager():
    """analyze with unknown manager exits with error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "pkg1", "--manager", "nonexistent"])
    assert result.exit_code != 0


def test_analyze_with_conflicts():
    """analyze with conflicting packages shows exclusion reasons."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["analyze", "pkg1", "pkg2", "-c", "pkg1", "pkg2", "--output", "json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["conflict_count"] == 1
    assert data["excluded_count"] == 1


def test_analyze_with_dependencies():
    """analyze with dependencies shows dependency info."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["analyze", "pkg1", "pkg2", "-d", "pkg1", "pkg2", "--output", "json"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["dependency_count"] >= 1


def test_analyze_bottleneck_detection():
    """analyze detects bottleneck packages."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "analyze",
            "pkg1",
            "pkg2",
            "pkg3",
            "pkg4",
            "-c",
            "pkg1",
            "pkg2",
            "-c",
            "pkg1",
            "pkg3",
            "-c",
            "pkg1",
            "pkg4",
            "--output",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    bottlenecks = data["bottlenecks"]
    if bottlenecks:
        assert bottlenecks[0]["name"] == "pkg1"
        assert bottlenecks[0]["conflict_count"] == 3


def test_analyze_with_metadata_flag():
    """analyze --metadata attempts adapter fetch."""
    runner = CliRunner()
    mock_adapter = MagicMock()
    mock_meta = MagicMock()
    mock_meta.name = "pkg1"
    mock_meta.depends = ["libc6"]
    mock_meta.conflicts = []
    mock_adapter.fetch.return_value = mock_meta

    with patch("package_maximizer.adapters.get_adapter", return_value=mock_adapter):
        result = runner.invoke(cli, ["analyze", "pkg1", "--metadata"])
    assert result.exit_code == 0, result.output
    assert mock_adapter.fetch.called


def test_analyze_no_metadata_adapter():
    """analyze --metadata with no adapter warns but continues."""
    runner = CliRunner()
    with patch("package_maximizer.adapters.get_adapter", return_value=None):
        result = runner.invoke(cli, ["analyze", "pkg1", "--metadata"])
    assert result.exit_code == 0, result.output
    assert "No metadata adapter" in result.output or "Warning" in result.output


# --- Compare command tests -------------------------------------------------


def test_compare_basic():
    """compare runs all solvers on package set."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "pkg1", "pkg2", "pkg3"])
    assert result.exit_code == 0, result.output
    assert "Solver Comparison" in result.output


def test_compare_json_output():
    """compare --output json returns JSON with all solvers."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "pkg1", "pkg2", "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "results" in data
    assert len(data["results"]) > 0
    # Check structure of result entries
    for r in data["results"]:
        assert "solver" in r
        assert "avg_time" in r
        assert "selected_count" in r
        assert "success" in r


def test_compare_empty_packages():
    """compare with no packages exits with error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compare"])
    assert result.exit_code != 0


def test_compare_invalid_manager():
    """compare with unknown manager exits with error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "pkg1", "--manager", "nonexistent"])
    assert result.exit_code != 0


def test_compare_results_sorted_by_time():
    """compare results are sorted by avg_time (fastest first)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "pkg1", "pkg2", "pkg3", "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    times = [r["avg_time"] for r in data["results"]]
    assert times == sorted(times)


def test_compare_best_solver_reported():
    """compare reports the best (fastest) solver."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "pkg1", "pkg2"])
    assert result.exit_code == 0, result.output
    assert "Best:" in result.output


def test_compare_with_metadata_flag():
    """compare --metadata attempts adapter fetch."""
    runner = CliRunner()
    mock_adapter = MagicMock()
    mock_meta = MagicMock()
    mock_meta.name = "pkg1"
    mock_meta.depends = []
    mock_meta.conflicts = []
    mock_adapter.fetch.return_value = mock_meta

    with patch("package_maximizer.adapters.get_adapter", return_value=mock_adapter):
        result = runner.invoke(cli, ["compare", "pkg1", "--metadata"])
    assert result.exit_code == 0, result.output
    assert mock_adapter.fetch.called
