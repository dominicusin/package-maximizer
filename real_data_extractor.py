"""
Real-World Data Extractor for package-maximizer.

Extracts ACTUAL package dependency data from the NixOS store using
nix-store -qR (the same mechanism nixpkgs uses for dependency resolution).
This provides real package dependency graphs from actual NixOS packages.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


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


def get_all_packages_nixpkgs() -> list[dict[str, str]]:
    """Extract package names from nixpkgs all-packages.nix."""
    nixpkgs = Path("/nix/store/cc7ff4ysismx0c3778v8gc6b14plrz3z-source")
    all_packages = nixpkgs / "pkgs" / "top-level" / "all-packages.nix"
    
    if not all_packages.exists():
        return []
    
    content = all_packages.read_text(errors="replace")
    
    # Parse: name = callPackage ./path { ... };  or name = { ... }: ...
    # Extract package name and version
    packages = []
    # Pattern: alias = packageName;  (aliases)

    import re
    aliases = re.findall(r'^\s*(\w+)\s*=\s*(\w+)\s*;', content, re.MULTILINE)
    
    # Match package definitions with versions
    # Pattern: name = package { version = "x.y.z"; ... }
    pkg_defs = re.findall(
        r'^\s*(\w+)\s*=\s*(?:stdenv|lib).*?version\s*=\s*"([^"]+)"',
        content, re.MULTILINE | re.DOTALL
    )
    
    # Also match: name = callPackage ./path/name { version = "x.y.z"; }
    call_pkg = re.findall(
        r'^\s*(\w+)\s*=\s*callPackage\s*\.?/([^;]+)\s*\{[^}]*version\s*=\s*"([^"]+)"',
        content, re.MULTILINE | re.DOTALL
    )
    
    for name, version in pkg_defs[:500]:
        if len(name) > 1 and not name.startswith("_") and len(name) < 50:
            packages.append({"name": name, "version": version})
    
    for alias, real_name in aliases[:500]:
        if len(alias) > 1 and not alias.startswith("_"):
            packages.append({"name": alias, "version": real_name})
    
    for name, _, version in call_pkg[:500]:
        if len(name) > 1 and not name.startswith("_"):
            packages.append({"name": name, "version": version})
    
    return packages[:1000]


def extract_real_dependencies(
    package_name: str, 
    nixpkgs_path: str = "/nix/store/cc7ff4ysismx0c3778v8gc6b14plrz3z-source"
) -> dict[str, Any]:
    """Extract real dependency data for a specific package from nixpkgs."""
    result = subprocess.run(
        ["nix-build", "<nixpkgs>", "-A", package_name, "--no-out-link"],
        capture_output=True, text=True, timeout=60,
        env={**dict(os.environ), "NIXPKGS_ALLOW_UNFREE": "1"}
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {"name": package_name, "depends": [], "conflicts": []}
    
    store_path = result.stdout.strip()
    deps = nix_store_qr(store_path)
    
    # Map store paths back to package names using nix-store --query --requisites
    # and nix-store --query --graph
    return {
        "name": package_name,
        "store_path": store_path,
        "dependencies": [d for d in deps if d != store_path][:20],
        "total_deps": len(deps) - 1,
    }


def build_real_package_database() -> dict[str, Any]:
    """Build a complete database of real packages with actual dependencies."""
    print("=" * 70)
    print("  REAL-WORLD DATA EXTRACTOR")
    print("  Extracting actual dependency data from NixOS store")
    print("=" * 70)
    
    # 1. Get installed packages
    installed = nix_profile_list()
    print(f"\n[1/3] Found {len(installed)} installed packages via nix profile")
    
    # 2. Get all nixpkgs packages
    all_pkgs = get_all_packages_nixpkgs()
    print(f"[2/3] Found {len(all_pkgs)} package definitions in nixpkgs")
    
    # 3. Extract real dependencies for sample packages
    sample_packages = ["bash", "coreutils", "git", "curl", "firefox", "python3", "gcc", "vim", "neovim", "nodejs", "nginx", "postgresql", "redis"]
    
    real_deps = {}
    print(f"[3/3] Extracting real dependencies for {len(sample_packages)} packages...")
    for pkg in sample_packages:
        try:
            data = extract_real_dependencies(pkg)
            if data.get("store_path"):
                real_deps[pkg] = data
                print(f"  {pkg}: {data['total_deps']} deps, store: {data['store_path'][:40]}...")
        except Exception as e:
            print(f"  {pkg}: FAILED - {e}")
    
    result = {
        "platform": "nixos",
        "extraction_method": "nix-store -qR",
        "installed_packages": len(installed),
        "nixpkgs_packages": len(all_pkgs),
        "real_dependency_samples": len(real_deps),
        "packages": all_pkgs[:500],
        "real_dependencies": real_deps,
        "installed_detail": installed,
    }
    
    # Save
    output = Path("/home/domini/package-maximizer/real_world_data.json")
    with open(output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Saved to {output}")
    
    return result


if __name__ == "__main__":
    import os
    result = build_real_package_database()
    print(f"\nExtracted {result['nixpkgs_packages']} packages with {result['real_dependency_samples']} real dependency samples")
    sys.exit(0)
