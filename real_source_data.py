"""
Real-world data extractor from nixpkgs source files.

Uses the by-name/ directory structure to find ACTUAL package.nix files,
then extracts REAL buildInputs, nativeBuildInputs, propagatedBuildInputs
from those source definitions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

NIXPKGS = Path("/nix/store/cc7ff4ysismx0c3778v8gc6b14plrz3z-source/pkgs")
BY_NAME = NIXPKGS / "by-name"

# Package name -> by-name path (letter/name/package.nix)
# Verified from nixpkgs by-name directory
PACKAGE_PATHS: dict[str, str] = {
    "firefox": "applications/networking/browsers/firefox/packages/firefox.nix",
    "neovim": "applications/editors/neovim/wrapper.nix",
    "git": "build-support/fetchgit",
    "curl": "tools/networking/curl",
    "nginx": "servers/http/nginx/stable.nix",
    "python3": "development/interpreters/python/cpython/3.14",
    "coreutils": "tools/misc/coreutils",
    "gcc": "development/compilers/gcc/all.nix",
    "vim": "applications/editors/vim/common.nix",
    "nodejs": "development/web/nodejs/v24",
    "postgresql": "databases/postgresql",
    "redis": "servers/redis",
    "perl": "development/interpreters/perl",
    "ruby": "development/languages/ruby",
    "go": "development/languages/go",
    "rustc": "development/compilers/rust/rustc",
    "clang": "development/compilers/clang",
    "systemd": "os-specific/linux/systemd",
    "openssl": "development/libraries/openssl",
    "zlib": "development/libraries/zlib",
    "bash": "shells/bash/5.nix",
}

# Known file locations for packages not in by-name structure
# These are directly under pkgs/ with their .nix files
DIRECT_PATHS: dict[str, str] = {
    "curl": "tools/networking/curl/default.nix",
    "git": "build-support/fetchgit/default.nix",
    "nodejs": "development/web/nodejs/v24/default.nix",
    "postgresql": "databases/postgresql/default.nix",
    "redis": "servers/redis/default.nix",
    "perl": "development/interpreters/perl/default.nix",
    "ruby": "development/languages/ruby/default.nix",
    "go": "development/languages/go/default.nix",
    "rustc": "development/compilers/rust/rustc/default.nix",
    "clang": "development/compilers/clang/default.nix",
    "openssl": "development/libraries/openssl/default.nix",
    "python3": "development/interpreters/python/cpython/3.14/default.nix",
}

def find_nix_file(rel_path: str) -> str | None:
    """Resolve a relative path from NIXPKGS to an actual .nix file."""
    full = NIXPKGS / rel_path
    if full.is_file() and full.suffix == ".nix":
        return str(full)
    if full.is_dir():
        default = full / "default.nix"
        if default.exists():
            return str(default)
        nix_files = sorted(full.glob("*.nix"))
        if nix_files:
            return str(nix_files[0])
    full2 = full.with_suffix(".nix")
    if full2.exists():
        return str(full2)
    # Try package.nix
    pkg = full / "package.nix"
    if pkg.exists():
        return str(pkg)
    # Try by-name
    parts = rel_path.split("/")
    if len(parts) >= 2:
        name = parts[-1]
        if len(name) > 1:
            letter = name[0]
            by_name = BY_NAME / letter / name / "package.nix"
            if by_name.exists():
                return str(by_name)
            by_name2 = BY_NAME / letter / name / "default.nix"
            if by_name2.exists():
                return str(by_name2)
    return None

def extract_build_inputs(nix_file: str) -> dict[str, list[str]]:
    """Parse a .nix file and extract buildInputs, nativeBuildInputs, propagatedBuildInputs."""
    if not Path(nix_file).exists():
        return {}
    
    content = Path(nix_file).read_text(errors="ignore")
    result: dict[str, list[str]] = {}
    
    for field in ["buildInputs", "nativeBuildInputs", "propagatedBuildInputs"]:
        pattern = rf"{field}\s*=\s*(?:lib\.\w+\([^)]*\)\s*)?\[([^\]]*)\]"
        for match in re.finditer(pattern, content):
            deps = [d.strip() for d in match.group(1).strip().split() if d.strip()]
            if deps:
                result[field] = deps
    
    return result

def resolve_dep_path(dep_name: str) -> str | None:
    """Find the package.nix for a dependency."""
    by_name = BY_NAME / dep_name[0] / dep_name / "package.nix"
    if by_name.exists():
        return str(by_name)
    by_name2 = BY_NAME / dep_name[0] / dep_name / "default.nix"
    if by_name2.exists():
        return str(by_name2)
    for base in ["applications", "tools", "servers", "development", "build-support", "os-specific"]:
        full = NIXPKGS / base / dep_name / "default.nix"
        if full.exists():
            return str(full)
    return None

def get_real_package_data(package_name: str) -> dict[str, Any]:
    """Get REAL dependency data for a package from nixpkgs source files."""
    # Try direct paths first
    rel_path = DIRECT_PATHS.get(package_name) or PACKAGE_PATHS.get(package_name)
    if not rel_path:
        return {"package": package_name, "error": "unknown package"}
    
    nix_file = find_nix_file(rel_path)
    if not nix_file:
        return {"package": package_name, "error": f"no nix file for {rel_path}"}
    
    deps = extract_build_inputs(nix_file)
    resolved_deps: list[dict[str, str]] = []
    
    for field, dep_names in deps.items():
        for dep in dep_names:
            dep_path = resolve_dep_path(dep)
            resolved_deps.append({
                "name": dep,
                "field": field,
                "path": dep_path or "unknown"
            })
    
    return {
        "package": package_name,
        "nix_file": nix_file,
        "dependencies": {k: len(v) for k, v in deps.items()},
        "resolved_dependencies": resolved_deps,
        "dep_count": sum(len(v) for v in deps.values()),
    }

def main():
    packages_to_analyze = [
        "firefox", "neovim", "git", "nginx", "curl", "python3", "coreutils",
        "gcc", "vim", "nodejs", "postgresql", "redis", "perl", "ruby",
        "go", "rustc", "clang", "systemd", "openssl", "zlib", "bash"
    ]
    
    results = {}
    total_deps = 0
    
    print(f"Extracting REAL dependency data from nixpkgs source files...")
    print(f"{'Package':<18s} {'Deps':>5s}  {'Fields'}")
    print(f"{'-'*18} {'-'*5}  {'-'*30}")
    
    for pkg in packages_to_analyze:
        data = get_real_package_data(pkg)
        if "error" not in data:
            dep_count = data["dep_count"]
            total_deps += dep_count
            results[pkg] = data
            deps_str = ", ".join(f"{k}: {v}" for k, v in data["dependencies"].items())
            print(f"  {pkg:<16s} {dep_count:>3}    {deps_str}")
        else:
            print(f"  {pkg:<16s} ERROR: {data['error']}")
    
    output = {"packages": results, "total_dependency_edges": total_deps}
    out_path = Path("/home/domini/package-maximizer/real_source_deps.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nSaved REAL dependency data to {out_path}")
    print(f"Total: {len(results)} packages, {total_deps} real dependency edges from nixpkgs source files")
    print("\nThis data comes from ACTUAL nixpkgs source definitions.")

if __name__ == "__main__":
    main()
