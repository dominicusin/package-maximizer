"""
Real-world benchmark using ACTUAL nix-store -qR dependency data.
This feeds real package/dependency graphs to all solvers.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from package_maximizer.core.maximizer import PackageMaximizer
from package_maximizer.core.model_encoder import encode_packages
from package_maximizer.core.package import Package
from package_maximizer.solvers import SOLVER_REGISTRY

# Load real dependency data
with open("/home/domini/package-maximizer/real_deps_data.json") as f:
    real_data = json.load(f)

# Build Package objects from real data
packages: list[Package] = []
for name, info in real_data["packages"].items():
    pkg = Package(name=name, version="0.0.0")
    pkg.depends = info["deps"][:10]  # Use first 10 deps as constraints
    pkg.conflicts = []  # Conflicts not available via nix-store -qR
    packages.append(pkg)

print(f"Loaded {len(packages)} real packages with {real_data['total_dependency_edges']} dependency edges")

# Run benchmark
results = {"packages": len(packages), "solvers": {}}

for solver_name in SOLVER_REGISTRY.keys():
    maximizer = PackageMaximizer(manager="apt", solver=solver_name)
    start = time.perf_counter()
    try:
        selected = maximizer.maximize(packages)
        elapsed = time.perf_counter() - start
        selected_names = set(p.name for p in selected)
        constraints = encode_packages(packages)
        conflicts = sum(1 for a, b in constraints.conflicts if a in selected_names and b in selected_names)
        unmet = sum(1 for p in selected for dep in (p.depends or []) if dep not in selected_names)
        results["solvers"][solver_name] = {
            "status": "OK",
            "time_seconds": round(elapsed, 4),
            "selected": len(selected),
            "selection_rate": round(len(selected) / len(packages) * 100, 1),
            "conflicts": conflicts,
            "unmet_deps": unmet,
        }
        print(f"  {solver_name}: {len(selected)}/{len(packages)} in {elapsed:.4f}s, {conflicts} conflicts, {unmet} unmet")
    except Exception as e:
        elapsed = time.perf_counter() - start
        results["solvers"][solver_name] = {"status": "ERROR", "time": round(elapsed, 4), "error": str(e)[:80]}
        print(f"  {solver_name}: ERROR - {e}")

# Print summary
print(f"\n{'='*60}")
print("  REAL-WORLD BENCHMARK RESULTS")
print(f"{'='*60}")
ok = {k:v for k,v in results["solvers"].items() if v["status"]=="OK"}
if ok:
    fastest = min(ok.items(), key=lambda x: x[1]["time_seconds"])
    most_correct = max(ok.items(), key=lambda x: x[1]["conflicts"] + x[1]["unmet_deps"] == 0)
    print(f"Fastest: {fastest[0]} ({fastest[1]['time_seconds']}s)")
    print(f"Most correct: {most_correct[0]}")
    print(f"\n{'Solver':<20s} {'Time':<10s} {'Selected':<10s} {'Rate%':<8s} {'Conflicts':<10s} {'Unmet':<8s}")
    print(f"{'-'*20} {'-'*10} {'-'*10} {'-'*8} {'-'*10} {'-'*8}")
    for name, data in sorted(ok.items(), key=lambda x: x[1]["time_seconds"]):
        print(f"{name:<20s} {data['time_seconds']:<10.4f} {data['selected']:<10d} {data['selection_rate']:<8.1f} {data['conflicts']:<10d} {data['unmet_deps']:<8d}")

with open("/home/domini/package-maximizer/real_world_benchmark_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to real_world_benchmark_results.json")
