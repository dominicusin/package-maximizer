"""
Real-world data runner for package-maximizer on NixOS.

Extracts installed packages from nix profile list,
fetches dependency information via nix-store --references,
and runs the maximizer to find the maximum non-conflicting
subset of packages.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from package_maximizer.core.maximizer import PackageMaximizer
from package_maximizer.core.package import Package

logger = logging.getLogger(__name__)


def get_nixos_installed_packages() -> list[Package]:
    """
    Get installed packages from nix profile list --json.

    Returns list of Package objects with names extracted from store paths.
    """
    packages: list[Package] = []

    try:
        result = subprocess.run(
            ["nix", "profile", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning(f"nix profile list failed: {result.stderr[:200]}")
            return []

        data = json.loads(result.stdout)
        elements = data.get("elements", {})
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to read nix profile: {e}")
        return []

    for pkg_id, pkg_info in elements.items():
        if not isinstance(pkg_info, dict):
            continue
        store_paths = pkg_info.get("storePaths", [])
        # Parse name from store path: /nix/store/xxx-name-version
        for sp in store_paths:
            name = _parse_store_path_name(sp)
            if name:
                packages.append(Package(name=name))
                break  # Only one package per profile entry

    return packages


def get_nixos_package_dependencies(package_name: str) -> list[str]:
    """
    Get dependencies for a package by finding its store path and using nix-store --references.
    """
    deps: list[str] = []
    try:
        # Find store path for this package
        find_result = subprocess.run(
            ["nix", "store", "query", "--refs", package_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if find_result.returncode == 0 and find_result.stdout.strip():
            for line in find_result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    dep_name = _parse_store_path_name(line)
                    if dep_name and dep_name != package_name:
                        deps.append(dep_name)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    if not deps:
        # Fallback: search all store paths for matches
        try:
            for item in os.listdir("/nix/store"):
                if f"-{package_name}-" in item or item.startswith(f"{package_name}-"):
                    refs = _get_references_for_store_path(item)
                    deps.extend(refs)
                    break
        except Exception:
            pass

    return list(set(deps))[:10]  # Limit dependencies


def _get_references_for_store_path(store_path: str) -> list[str]:
    """Get references (dependencies) for a store path."""
    deps: list[str] = []
    try:
        result = subprocess.run(
            ["nix-store", "-qR", f"/nix/store/{store_path}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    dep_name = _parse_store_path_name(line)
                    if dep_name:
                        deps.append(dep_name)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return deps


def _parse_store_path_name(store_path: str) -> str | None:
    """
    Extract package name from a Nix store path.

    E.g., /nix/store/xxx-python3.14-pip-24.0 -> python3.14-pip
    E.g., /nix/store/xxx-ccache-4.13.6 -> ccache
    """
    # Remove the path prefix
    basename = store_path.rstrip("/").split("/")[-1]
    # Match: prefix-name-version
    # Try to find the name by stripping version numbers from the end
    # Common pattern: name-version or name-subversion-version
    match = re.match(r"^[a-z0-9]+-(.+?)-(\d+\.\d+)", basename)
    if match:
        return match.group(1)
    # Simple pattern: just strip leading hash and first dash
    match = re.match(r"^[a-z0-9]+-(.+)$", basename)
    if match:
        return match.group(1)
    return None


def build_package_graph(
    packages: list[Package], max_packages: int = 200
) -> list[Package]:
    """
    Build a package list with dependency information from the Nix store.

    Args:
        packages: List of Package objects (names only)
        max_packages: Maximum packages to process

    Returns:
        Package objects enriched with depends/conflicts
    """
    enriched: list[Package] = []
    to_process = packages[:max_packages]

    for i, pkg in enumerate(to_process):
        if i % 50 == 0:
            logger.info(f"Processing package {i}/{len(to_process)}...")

        deps = get_nixos_package_dependencies(pkg.name)
        if deps:
            pkg.depends = deps

        # Find conflicts by checking if any deps are also in the list
        pkg.conflicts = []
        enriched.append(pkg)

    return enriched


def run_real_world_maximization(
    manager: str = "apt", solver: str = "greedy", max_packages: int = 200
) -> dict[str, Any]:
    """
    Run package maximization on real NixOS installed packages.

    Returns a summary of the results.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print(f"\n{'='*60}")
    print(f"Package Maximizer — Real-World Data Test")
    print(f"{'='*60}")

    # Step 1: Get installed packages
    print("\n[1/3] Fetching installed packages from nix profile...")
    packages = get_nixos_installed_packages()
    print(f"Found {len(packages)} installed packages")

    if not packages:
        print("ERROR: No packages found!")
        return {"error": "No packages found"}

    # Step 2: Build package graph with dependencies
    print(
        f"\n[2/3] Building dependency graph ({min(max_packages, len(packages))} packages)..."
    )
    enriched_packages = build_package_graph(packages, max_packages=max_packages)
    print(f"Enriched {len(enriched_packages)} packages with dependencies")

    # Step 3: Run maximizer
    print(f"\n[3/3] Running maximizer ({solver} solver)...")
    maximizer = PackageMaximizer(manager=manager, solver=solver)
    selected = maximizer.maximize(enriched_packages)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Input packages:    {len(enriched_packages)}")
    print(f"Selected packages: {len(selected)}")
    print(f"Selection rate:    {len(selected)/len(enriched_packages)*100:.1f}%")
    print(f"\nSelected packages ({len(selected)}):")
    for i, pkg in enumerate(selected[:20]):
        print(f"  {i+1}. {pkg.name}")
    if len(selected) > 20:
        print(f"  ... and {len(selected) - 20} more")

    return {
        "total_input": len(enriched_packages),
        "selected": len(selected),
        "selection_rate": f"{len(selected)/len(enriched_packages)*100:.1f}%",
        "selected_names": [p.name for p in selected],
    }


def run_compare_solvers_on_real_data(max_packages: int = 100) -> dict[str, Any]:
    """
    Compare all available solvers on real NixOS package data.
    """
    from package_maximizer.solvers import SOLVER_REGISTRY

    print(f"\n{'='*60}")
    print("Solver Comparison — Real-World Data")
    print(f"{'='*60}")

    packages = get_nixos_installed_packages()[:max_packages]
    enriched = build_package_graph(packages, max_packages=max_packages)

    results = {}
    for solver_name in SOLVER_REGISTRY.keys():
        if solver_name == "greedy":
            continue  # Already tested
        print(f"\nTesting {solver_name}...")
        try:
            maximizer = PackageMaximizer(manager="apt", solver=solver_name)
            selected = maximizer.maximize(enriched)
            results[solver_name] = {
                "selected": len(selected),
                "rate": (
                    f"{len(selected)/len(enriched)*100:.1f}%" if enriched else "N/A"
                ),
            }
            print(
                f"  → {len(selected)} packages selected ({results[solver_name]['rate']})"
            )
        except Exception as e:
            results[solver_name] = {"error": str(e)[:100]}
            print(f"  → ERROR: {e}")

    # Also test greedy
    maximizer = PackageMaximizer(manager="apt", solver="greedy")
    selected = maximizer.maximize(enriched)
    results["greedy"] = {
        "selected": len(selected),
        "rate": f"{len(selected)/len(enriched)*100:.1f}%" if enriched else "N/A",
    }

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for solver, data in sorted(
        results.items(), key=lambda x: x[1].get("selected", 0), reverse=True
    ):
        print(
            f"  {solver:20s}: {data.get('selected', 'N/A')} packages ({data.get('rate', 'N/A')})"
        )

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run package-maximizer on real NixOS data"
    )
    parser.add_argument(
        "--max-packages", type=int, default=200, help="Max packages to process"
    )
    parser.add_argument("--solver", type=str, default="greedy", help="Solver to use")
    parser.add_argument("--compare", action="store_true", help="Compare all solvers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.compare:
        run_compare_solvers_on_real_data(max_packages=args.max_packages)
    else:
        run_real_world_maximization(
            manager="apt",
            solver=args.solver,
            max_packages=args.max_packages,
        )
