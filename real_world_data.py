"""
Real-world data extractor and benchmark runner.

Extracts ACTUAL package dependencies from the NixOS store using
nix-store -qR (the same dependency resolution mechanism nixpkgs uses).
Then runs all solvers against real package data from multiple platforms.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from package_maximizer.core.enums import PackageManagerType
from package_maximizer.core.maximizer import PackageMaximizer
from package_maximizer.core.model_encoder import encode_packages
from package_maximizer.core.package import Package
from package_maximizer.solvers import SOLVER_REGISTRY


# ─── Real Data Extraction ────────────────────

def nix_store_qr(store_path: str) -> list[str]:
    """Get recursive dependencies of a Nix store path using nix-store -qR."""
    result = subprocess.run(
        ["nix-store", "-qR", store_path],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def nix_profile_list() -> list[dict[str, Any]]:
    """Get installed packages from nix profile list --json."""
    result = subprocess.run(
        ["nix", "profile", "list", "--json"],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
        elements = data.get("elements", {})
        packages = []
        for name, info in elements.items():
            store_paths = info.get("storePaths", [])
            packages.append({
                "name": name,
                "version": info.get("version", "unknown"),
                "store_paths": store_paths,
                "active": info.get("active", False),
            })
        return packages
    except json.JSONDecodeError:
        return []


def get_real_package_data() -> dict[str, Any]:
    """
    Extract REAL package data using nix-store -qR from actual packages.
    This is the mechanism that package managers themselves use.
    """
    print("=" * 70)
    print("  REAL-WORLD DATA EXTRACTOR")
    print("  Using nix-store -qR (same mechanism as package managers)")
    print("=" * 70)

    # 1. Get installed packages
    installed = nix_profile_list()
    print(f"\n[1/4] Found {len(installed)} installed packages via nix profile")

    # 2. Build package data using nix-store -qR
    # These are real packages from nixpkgs with actual dependencies
    sample_packages = [
        ("bash", "bash"),
        ("coreutils", "coreutils"),
        ("git", "git"),
        ("curl", "curl"),
        ("firefox", "firefox"),
        ("python3", "python3"),
        ("gcc", "gcc"),
        ("vim", "vim"),
        ("neovim", "neovim"),
        ("nodejs", "nodejs"),
        ("nginx", "nginx"),
        ("postgresql", "postgresql"),
        ("redis", "redis"),
        ("perl", "perl"),
        ("ruby", "ruby"),
        ("go", "go"),
        ("rustc", "rustc"),
        ("clang", "clang"),
        ("systemd", "systemd"),
        ("openssl", "openssl"),
        ("zlib", "zlib"),
        ("glibc", "glibc"),
        ("bash-interactive", "bash-interactive"),
    ]

    real_packages: list[Package] = []
    real_deps_data: dict[str, Any] = {}

    print(f"[2/4] Extracting real dependencies using nix-store -qR...")
    for name, attr in sample_packages:
        try:
            # Build the package to get its store path
            build_result = subprocess.run(
                ["nix-build", "<nixpkgs>", "-A", attr, "--no-out-link"],
                capture_output=True, text=True, timeout=60
            )
            if build_result.returncode != 0 or not build_result.stdout.strip():
                continue

            store_path = build_result.stdout.strip()
            deps = nix_store_qr(store_path)

            # Parse version from store path
            import re
            version_match = re.search(r'-(\d+\.\d+[\d.]*)', store_path)
            version = version_match.group(1) if version_match else "0.0.0"

            pkg = Package(name=name, version=version)
            pkg.depends = [d.split("/")[-1] for d in deps if d != store_path][:20]
            pkg.conflicts = []  # Conflicts not available via nix-store -qR

            real_packages.append(pkg)
            real_deps_data[name] = {
                "store_path": store_path,
                "deps_count": len(deps) - 1,
                "dependencies": pkg.depends[:10],
            }
            print(f"  {name}: {len(deps)-1} real deps, version {version}")
        except Exception as e:
            print(f"  {name}: FAILED - {e}")

    print(f"\n[3/4] Extracted {len(real_packages)} real packages with actual dependencies")
    print(f"[4/4] Total dependency data points: {sum(len(v['dependencies']) for v in real_deps_data.values())}")

    result = {
        "platform": "nixos",
        "extraction_method": "nix-store -qR",
        "installed_packages": len(installed),
        "real_packages": len(real_packages),
        "total_dependency_edges": sum(len(v['dependencies']) for v in real_deps_data.values()),
        "packages": real_packages,
        "dependency_data": real_deps_data,
        "installed_detail": installed,
    }

    output = Path("/home/domini/package-maximizer/real_world_data.json")
    with open(output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Saved to {output}")

    return result


# ─── Benchmark Runner ────────────────────────

def run_benchmark(
    packages: list[Package],
    solver_names: list[str] | None = None,
) -> dict[str, Any]:
    """Run all solvers on a package set."""
    if solver_names is None:
        solver_names = list(SOLVER_REGISTRY.keys())

    results: dict[str, Any] = {"total_packages": len(packages), "solvers": {}}

    for solver_name in solver_names:
        if solver_name not in SOLVER_REGISTRY:
            continue
        maximizer = PackageMaximizer(manager="apt", solver=solver_name)
        start_time = time.perf_counter()
        try:
            selected = maximizer.maximize(packages)
            elapsed = time.perf_counter() - start_time
            selected_names = set(p.name for p in selected)
            selected_count = len(selected)
            accuracy = selected_count / len(packages) * 100 if len(packages) > 0 else 0

            constraints = encode_packages(packages)
            conflicts = sum(
                1 for a, b in constraints.conflicts
                if a in selected_names and b in selected_names
            )
            unmet = sum(
                1 for pkg in selected
                for dep in (pkg.depends or [])
                if dep not in selected_names
            )

            results["solvers"][solver_name] = {
                "status": "OK",
                "time_seconds": round(elapsed, 4),
                "packages_selected": selected_count,
                "selection_rate": round(accuracy, 1),
                "conflicts": conflicts,
                "unmet_dependencies": unmet,
                "correctness": round(
                    (1 - conflicts / max(1, selected_count))
                    * (1 - unmet / max(1, selected_count))
                    * 100, 1,
                ),
            }
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            results["solvers"][solver_name] = {
                "status": "ERROR", "time_seconds": round(elapsed, 4),
                "error": str(e)[:80],
            }

    return results


def run_full_real_world_benchmark(
    max_packages: int = 50,
) -> dict[str, Any]:
    """Run comprehensive benchmark using REAL package data."""
    print("\n" + "=" * 80)
    print("  REAL-WORLD PACKAGE MAXIMIZER BENCHMARK")
    print("  Data source: nix-store -qR (actual NixOS dependencies)")
    print("=" * 80)

    # Extract real data
    data = get_real_package_data()
    packages = data["packages"][:max_packages]

    print(f"\n{'='*80}")
    print(f"  BENCHMARKING {len(packages)} REAL PACKAGES WITH {len(SOLVER_REGISTRY)} SOLVERS")
    print(f"{'='*80}")

    all_results = run_benchmark(packages)
    all_results["extraction"] = {
        "method": data["extraction_method"],
        "installed_packages": data["installed_packages"],
        "total_dependency_edges": data["total_dependency_edges"],
    }

    # Print results
    print(f"\n{'='*80}")
    print("  SOLVER COMPARISON (REAL DATA)")
    print(f"{'='*80}")
    print(f"\n{'Solver':<20s} {'Status':<8s} {'Time':<10s} {'Selected':<10s} {'Correct':<10s} {'Conflicts':<10s}")
    print(f"{'-'*20} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    for name, sdata in sorted(all_results["solvers"].items(), key=lambda x: x[1].get("correctness", 0), reverse=True):
        if sdata["status"] == "OK":
            print(
                f"{name:<20s} {sdata['status']:<8s} "
                f"{sdata['time_seconds']:<10.4f} "
                f"{sdata['packages_selected']:<10d} "
                f"{sdata['correctness']:<10.1f} "
                f"{sdata['conflicts']:<10d}"
            )
        else:
            print(f"{name:<20s} {sdata['status']:<8s} {sdata.get('error','-')}")

    # Save
    output = Path("/home/domini/package-maximizer/real_world_benchmark.json")
    with open(output, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Results saved to {output}")

    return all_results


if __name__ == "__main__":
    results = run_full_real_world_benchmark(max_packages=20)
    solvers_ok = all(
        v.get("status") == "OK"
        for v in results["solvers"].values()
    )
    sys.exit(0 if solvers_ok else 1)
