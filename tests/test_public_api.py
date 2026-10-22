"""Tests for the top-level public API surface of ``package_maximizer``.

Guards the lazy registries and the newly added modules (graph builder,
objective, backtracking solver, manifest loader, resource monitor) so a
regression that drops an export fails CI instead of silently breaking
callers.
"""

from __future__ import annotations

import importlib

import pytest


def test_top_level_import_never_requires_optional_solver_deps():
    """``import package_maximizer`` must work without z3/pulp/ortools."""
    import package_maximizer as pm

    # All these names resolve without the optional solver libraries.
    for name in ("GreedySolver", "BacktrackingSolver", "PackageMaximizer"):
        assert hasattr(pm, name), f"{name} missing from top-level exports"


@pytest.mark.parametrize(
    "name",
    [
        "BacktrackingSolver",
        "PackageGraph",
        "GraphBuilder",
        "build_runtime_graph",
        "build_buildtime_graph",
        "detect_cycles",
        "Objective",
        "get_default_weights",
        "ResourceMonitor",
        "ResourceSnapshot",
        "ManifestLoader",
        "RemoteManifestSource",
        "ManifestParseException",
    ],
)
def test_top_level_exports_resolve(name):
    """Every declared export is importable from the top-level package."""
    import package_maximizer as pm

    assert hasattr(pm, name), f"{name} missing from top-level exports"
    assert name in pm.__all__, f"{name} missing from __all__"


def test_all_names_are_importable_from_module():
    """``__all__`` must not reference names the package cannot provide."""
    import package_maximizer as pm

    module = importlib.import_module("package_maximizer")
    for name in pm.__all__:
        assert hasattr(module, name), f"__all__ references missing name {name!r}"


def test_backtracking_solver_is_registered():
    """The backtracking solver is listed in the lazy solver registry."""
    import package_maximizer.solvers as s

    assert "backtracking" in s.SOLVER_REGISTRY
    cls = s.SOLVER_REGISTRY["backtracking"]
    assert cls is not None and cls.__name__ == "BacktrackingSolver"


def test_parsing_module_exports_manifest_loader():
    """``package_maximizer.parsing`` exposes the manifest loader API."""
    import package_maximizer.parsing as p

    for name in ("ManifestLoader", "RemoteManifestSource", "ManifestParseException"):
        assert name in p.__all__
        assert hasattr(p, name)


def test_utils_module_exports_monitor():
    """``package_maximizer.utils`` exposes the resource monitor."""
    import package_maximizer.utils as u

    assert "ResourceMonitor" in u.__all__
    assert "ResourceSnapshot" in u.__all__
    assert u.ResourceMonitor is not None
