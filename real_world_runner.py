"""
Real-world data runner for package-maximizer on Debian Sid / Fedora Rawhide.

Uses nixpkgs as the real package source (since this is NixOS).
Parses nixpkgs all-packages.nix for package names, then uses
nix-store --references to fetch real dependency data.
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

# Path to nixpkgs all-packages.nix
NIXPKGS_ALL_PACKAGES = (
    "/nix/store/cc7ff4ysismx0c3778v8gc6b14plrz3z-source/pkgs/top-level/all-packages.nix"
)


def parse_nixpkgs_packages() -> list[dict[str, str]]:
    """
    Parse nixpkgs all-packages.nix for package definitions.

    Returns a list of package dicts with name and version info.
    """
    packages = []
    if not os.path.exists(NIXPKGS_ALL_PACKAGES):
        logger.warning(f"File not found: {NIXPKGS_ALL_PACKAGES}")
        return packages

    with open(NIXPKGS_ALL_PACKAGES, errors="ignore") as f:
        content = f.read()

    # Find all package definitions: name = callPackage(...) or name = lib.callPackage(...)
    # Also match simpler patterns
    patterns = [
        r"(\w+)\s*=\s*lib\.callPackage\s*\(",
        r"(\w+)\s*=\s*callPackage\s*\(",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            name = match.group(1)
            if name and not name.startswith("_") and len(name) > 2:
                packages.append({"name": name, "version": ""})

    # Deduplicate
    seen = set()
    unique = []
    for pkg in packages:
        if pkg["name"] not in seen:
            seen.add(pkg["name"])
            unique.append(pkg)

    return unique


def get_nix_store_packages() -> list[dict[str, str]]:
    """Get packages from the Nix store with versions."""
    packages = []
    for item in os.listdir("/nix/store"):
        if "-" not in item or item.endswith(".drv") or item.endswith(".patch"):
            continue
        parts = item.split("-")
        if len(parts) >= 2:
            # Find the version (first numeric part from the end)
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


def build_real_package_set(max_packages: int = 100) -> list[Package]:
    """
    Build a real package set from nixpkgs with dependencies.

    Args:
        max_packages: Maximum number of packages to include

    Returns:
        List of Package objects with dependencies filled in
    """
    print(f"\n{'='*60}")
    print("Real-World Data: NixOS/nixpkgs Package Analysis")
    print(f"{'='*60}")

    # Step 1: Get packages from nixpkgs
    print("\n[1/3] Parsing nixpkgs all-packages.nix...")
    nixpkgs_pkgs = parse_nixpkgs_packages()
    print(f"Found {len(nixpkgs_pkgs)} packages in nixpkgs")

    # Step 2: Get packages from store
    store_pkgs = get_nix_store_packages()
    print(f"Found {len(store_pkgs)} packages in Nix store")

    # Use a combined set
    all_names = set()
    packages: list[Package] = []

    # Add nixpkgs packages first
    for pkg_info in nixpkgs_pkgs[:max_packages]:
        name = pkg_info["name"]
        if name not in all_names and len(name) < 100:
            all_names.add(name)
            pkg = Package(name=name)
            packages.append(pkg)

    # Add store packages if we need more
    for pkg_info in store_pkgs[:max_packages]:
        name = pkg_info["name"]
        if name not in all_names and len(name) < 100:
            all_names.add(name)
            pkg = Package(name=name, version=pkg_info["version"])
            packages.append(pkg)

    print(f"Combined package set: {len(packages)} packages")

    # Step 3: Add dependencies for a sample
    print(f"\n[2/3] Fetching dependencies for {min(20, len(packages))} packages...")
    for i, pkg in enumerate(packages[:20]):
        deps = get_dependencies_for_package(pkg.name)
        if deps:
            pkg.depends = deps
        if i % 5 == 0:
            logger.info(f"Processing {i}/{min(20, len(packages))}...")

    print(f"\n[3/3] Running maximizer...")
    return packages


def run_debian_sid_analysis(max_packages: int = 50) -> dict[str, Any]:
    """
    Run maximizer on packages resembling Debian Sid.

    Uses nixpkgs as a proxy for Debian package data.
    """
    print(f"\n{'='*60}")
    print("Package Maximizer — Debian Sid Simulation")
    print(f"{'='*60}")

    packages = build_real_package_set(max_packages)

    if not packages:
        print("ERROR: No packages found!")
        return {"error": "No packages found"}

    # Run with greedy solver first
    maximizer = PackageMaximizer(manager="apt", solver="greedy")
    selected = maximizer.maximize(packages)

    print(f"\n{'='*60}")
    print("RESULTS (Debian Sid Simulation)")
    print(f"{'='*60}")
    print(f"Input packages:    {len(packages)}")
    print(f"Selected packages: {len(selected)}")
    print(f"Selection rate:    {len(selected)/len(packages)*100:.1f}%")
    print(f"\nSelected packages ({len(selected)}):")
    for i, pkg in enumerate(selected[:20]):
        print(f"  {i+1}. {pkg.name}")
    if len(selected) > 20:
        print(f"  ... and {len(selected) - 20} more")

    # Compare solvers
    print(f"\n{'='*60}")
    print("SOLVER COMPARISON")
    print(f"{'='*60}")
    from package_maximizer.solvers import SOLVER_REGISTRY

    for solver_name in SOLVER_REGISTRY.keys():
        try:
            maximizer = PackageMaximizer(manager="apt", solver=solver_name)
            selected = maximizer.maximize(packages[:50])
            print(f"  {solver_name:20s}: {len(selected)} packages selected")
        except Exception as e:
            print(f"  {solver_name:20s}: ERROR - {str(e)[:50]}")

    return {
        "total_input": len(packages),
        "selected": len(selected),
        "selection_rate": f"{len(selected)/len(packages)*100:.1f}%",
    }


def run_fedora_rawhide_analysis(max_packages: int = 50) -> dict[str, Any]:
    """
    Run maximizer on packages resembling Fedora Rawhide.

    Uses nixpkgs as a proxy for Fedora package data.
    """
    print(f"\n{'='*60}")
    print("Package Maximizer — Fedora Rawhide Simulation")
    print(f"{'='*60}")

    # Fedora uses RPM/dnf, but we'll use nixpkgs data
    # and simulate the package set
    packages = build_real_package_set(max_packages)

    if not packages:
        return {"error": "No packages found"}

    # Fedora typically has more strict dependency resolution
    # Try with z3 solver for better results
    maximizer = PackageMaximizer(manager="apt", solver="z3")
    selected = maximizer.maximize(packages)

    print(f"\n{'='*60}")
    print("RESULTS (Fedora Rawhide Simulation)")
    print(f"{'='*60}")
    print(f"Input packages:    {len(packages)}")
    print(f"Selected packages: {len(selected)}")
    print(f"Selection rate:    {len(selected)/len(packages)*100:.1f}%")

    return {
        "total_input": len(packages),
        "selected": len(selected),
        "selection_rate": f"{len(selected)/len(packages)*100:.1f}%",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run package-maximizer on real-world package data"
    )
    parser.add_argument(
        "--max-packages", type=int, default=50, help="Max packages to process"
    )
    parser.add_argument(
        "--distro",
        type=str,
        default="debian",
        choices=["debian", "fedora", "nixos"],
        help="Target distribution",
    )
    parser.add_argument("--compare", action="store_true", help="Compare all solvers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.compare:
        run_debian_sid_analysis(max_packages=args.max_packages)
        run_fedora_rawhide_analysis(max_packages=args.max_packages)
    elif args.distro == "fedora":
        run_fedora_rawhide_analysis(max_packages=args.max_packages)
    else:
        run_debian_sid_analysis(max_packages=args.max_packages)
