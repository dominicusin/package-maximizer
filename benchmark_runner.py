"""Comprehensive real-world solver benchmark for package-maximizer."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from package_maximizer.core.maximizer import PackageMaximizer
from package_maximizer.core.model_encoder import encode_packages
from package_maximizer.core.package import Package
from package_maximizer.solvers import SOLVER_REGISTRY

NIXPKGS_ALL_PACKAGES = (
    "/nix/store/cc7ff4ysismx0c3778v8gc6b14plrz3z-source/pkgs/top-level/all-packages.nix"
)


def parse_nixpkgs_packages() -> list[dict[str, str]]:
    """Parse nixpkgs all-packages.nix for package definitions."""
    packages: list[dict[str, str]] = []
    if not os.path.exists(NIXPKGS_ALL_PACKAGES):
        return packages
    with open(NIXPKGS_ALL_PACKAGES, errors="ignore") as f:
        content = f.read()
    for pattern in [
        r"(\w+)\s*=\s*lib\.callPackage\s*\(",
        r"(\w+)\s*=\s*callPackage\s*\(",
    ]:
        for match in re.finditer(pattern, content):
            name = match.group(1)
            if name and not name.startswith("_") and len(name) > 2:
                packages.append({"name": name, "version": ""})
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for pkg in packages:
        if pkg["name"] not in seen:
            seen.add(pkg["name"])
            unique.append(pkg)
    return unique


def get_nix_store_packages() -> list[dict[str, str]]:
    """Get packages from the Nix store with versions."""
    packages: list[dict[str, str]] = []
    for item in os.listdir("/nix/store"):
        if "-" not in item or item.endswith(".drv") or item.endswith(".patch"):
            continue
        parts = item.split("-")
        if len(parts) >= 2:
            for i in range(len(parts) - 1, 0, -1):
                if re.match(r"^\d", parts[i]):
                    name = "-".join(parts[:i])
                    version = parts[i]
                    packages.append({"name": name, "version": version})
                    break
    return packages


def get_dependencies_for_package(package_name: str) -> list[str]:
    """Get dependencies for a package via nix-store --references."""
    deps: list[str] = []
    try:
        result = subprocess.run(
            ["nix-store", "-qR", f"/nix/store/{package_name}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    dep = _parse_store_path(line)
                    if dep and dep != package_name:
                        deps.append(dep)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return list(dict.fromkeys(deps))[:10]


def _parse_store_path(path: str) -> str | None:
    """Extract package name from store path."""
    basename = path.rstrip("/").split("/")[-1]
    match = re.match(r"^[a-z0-9]+-(.+?)-(\d+\.\d+)", basename)
    if match:
        return match.group(1)
    return None


def build_real_package_set(max_packages: int = 50) -> list[Package]:
    """Build a real package set from nixpkgs with dependencies."""
    packages: list[Package] = []
    all_names: set[str] = set()
    for pkg_info in parse_nixpkgs_packages()[:max_packages]:
        name = pkg_info["name"]
        if name not in all_names and len(name) < 100:
            all_names.add(name)
            packages.append(Package(name=name))
    for pkg_info in get_nix_store_packages()[:max_packages]:
        name = pkg_info["name"]
        if name not in all_names and len(name) < 100:
            all_names.add(name)
            packages.append(Package(name=name, version=pkg_info["version"]))
    for pkg in packages[: min(20, len(packages))]:
        deps = get_dependencies_for_package(pkg.name)
        if deps:
            pkg.depends = deps
    return packages


def run_benchmark(
    packages: list[Package],
    solver_names: list[str] | None = None,
    max_packages: int = 50,
) -> dict[str, Any]:
    """Run all solvers and collect metrics."""
    if solver_names is None:
        solver_names = list(SOLVER_REGISTRY.keys())
    results: dict[str, Any] = {}
    comparison: dict[str, dict] = {}
    total_input = len(packages)
    for solver_name in solver_names:
        if solver_name not in SOLVER_REGISTRY:
            comparison[solver_name] = {"status": "SKIPPED", "reason": f"Unknown solver"}
            continue
        maximizer = PackageMaximizer(manager="apt", solver=solver_name)
        start_time = time.perf_counter()
        try:
            selected = maximizer.maximize(packages[:max_packages])
            elapsed = time.perf_counter() - start_time
            selected_names = set(p.name for p in selected)
            selected_count = len(selected)
            accuracy = selected_count / max_packages * 100 if max_packages > 0 else 0
            constraints = encode_packages(packages[:max_packages])
            conflicts_in_selected = sum(
                1
                for a, b in constraints.conflicts
                if a in selected_names and b in selected_names
            )
            deps_unmet = sum(
                1
                for pkg in selected
                for dep in (pkg.depends or [])
                if dep not in selected_names
            )
            comparison[solver_name] = {
                "status": "OK",
                "time_seconds": round(elapsed, 4),
                "packages_selected": selected_count,
                "selection_rate": round(accuracy, 1),
                "conflicts_in_selected": conflicts_in_selected,
                "unmet_dependencies": deps_unmet,
                "correctness_score": round(
                    (1 - conflicts_in_selected / max(1, selected_count))
                    * (1 - deps_unmet / max(1, selected_count))
                    * 100,
                    1,
                ),
                "accuracy": round(accuracy, 1),
            }
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            comparison[solver_name] = {
                "status": "ERROR",
                "time_seconds": round(elapsed, 4),
                "error": str(e)[:100],
            }
    successful = {k: v for k, v in comparison.items() if v.get("status") == "OK"}
    if successful:
        fastest = min(successful.items(), key=lambda x: x[1]["time_seconds"])
        most_accurate = max(successful.items(), key=lambda x: x[1]["accuracy"])
        most_correct = max(successful.items(), key=lambda x: x[1]["correctness_score"])
        highest_selection = max(
            successful.items(), key=lambda x: x[1]["packages_selected"]
        )
        results["summary"] = {
            "fastest_solver": fastest[0],
            "fastest_time": fastest[1]["time_seconds"],
            "most_accurate_solver": most_accurate[0],
            "most_accurate_rate": most_accurate[1]["accuracy"],
            "most_correct_solver": most_correct[0],
            "most_correct_score": most_correct[1]["correctness_score"],
            "highest_selection_solver": highest_selection[0],
            "highest_selection_count": highest_selection[1]["packages_selected"],
            "total_input_packages": total_input,
            "solvers_tested": len(successful),
        }
    results["solvers"] = comparison
    return results


def print_report(results: dict[str, Any]) -> None:
    """Print a formatted benchmark report."""
    print(f"\n{'='*70}")
    print("  PACKAGE MAXIMIZER — SOLVER BENCHMARK REPORT")
    print(f"{'='*70}")
    if "summary" in results:
        s = results["summary"]
        print(f"\n  Total Input Packages: {s['total_input_packages']}")
        print(f"  Solvers Tested:       {s['solvers_tested']}")
        print(f"\n  Fastest:              {s['fastest_solver']} ({s['fastest_time']}s)")
        print(
            f"  Most Accurate:        {s['most_accurate_solver']} ({s['most_accurate_rate']}%)"
        )
        print(
            f"  Most Correct:         {s['most_correct_solver']} ({s['most_correct_score']}%)"
        )
        print(
            f"  Highest Selection:    {s['highest_selection_solver']} ({s['highest_selection_count']} pkgs)"
        )
    print(f"\n{'='*70}")
    print(f"  DETAILED RESULTS")
    print(f"{'='*70}")
    print(
        f"\n  {'Solver':<20s} {'Status':<8s} {'Time':<10s} {'Selected':<10s} {'Accuracy':<10s} {'Correct':<10s}"
    )
    print(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for name, data in results["solvers"].items():
        status = data.get("status", "?")
        if status == "OK":
            print(
                f"  {name:<20s} {status:<8s} "
                f"{data['time_seconds']:<10.4f} "
                f"{data['packages_selected']:<10d} "
                f"{data['accuracy']:<10.1f} "
                f"{data['correctness_score']:<10.1f}"
            )
        else:
            print(
                f"  {name:<20s} {status:<8s} {'-':<10s} {'-':<10s} {'-':<10s} {'-':<10s}"
            )
    print(f"\n{'='*70}")
    print(f"  DEPENDENCY ANALYSIS")
    print(f"{'='*70}")
    for name, data in results["solvers"].items():
        if data.get("status") == "OK":
            print(
                f"  {name:<20s}: {data['conflicts_in_selected']} conflicts, "
                f"{data['unmet_dependencies']} unmet deps"
            )
    print()


def run_full_benchmark(
    max_packages: int = 50,
    solver_names: list[str] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Full benchmark: build real package set, run all solvers, report."""
    print(f"\n{'='*70}")
    print("  REAL-WORLD DATA BENCHMARK")
    print(f"{'='*70}")
    print(f"\n[1/2] Building package set from nixpkgs...")
    packages = build_real_package_set(max_packages)
    print(f"  Built {len(packages)} packages with real dependencies")
    print(f"\n[2/2] Running solvers...")
    results = run_benchmark(packages, solver_names, max_packages)
    print_report(results)
    output_path = Path("/home/domini/package-maximizer/benchmark_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results saved to {output_path}")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark package-maximizer solvers on real data"
    )
    parser.add_argument("--max-packages", type=int, default=50)
    parser.add_argument("--solvers", nargs="+", default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    results = run_full_benchmark(
        max_packages=args.max_packages,
        solver_names=args.solvers,
        verbose=args.verbose,
    )
    solvers_ok = all(v.get("status") == "OK" for v in results["solvers"].values())
    sys.exit(0 if solvers_ok else 1)
