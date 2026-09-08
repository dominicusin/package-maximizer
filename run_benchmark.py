import json, sys, time
from package_maximizer.core.maximizer import PackageMaximizer
from package_maximizer.core.model_encoder import encode_packages
from package_maximizer.core.package import Package
from package_maximizer.solvers import SOLVER_REGISTRY

with open("real_deps_data.json") as f:
    data = json.load(f)

packages = []
for name, info in data["packages"].items():
    pkg = Package(name=name, version="0.0.0")
    pkg.depends = info["deps"][:10]
    pkg.conflicts = []
    packages.append(pkg)

print(f"Loaded {len(packages)} REAL packages from nix-store -qR")
print(f"Total dependency edges: {data['total_dependency_edges']}\n")

results = {"total_packages": len(packages), "solvers": {}}
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
        accuracy = len(selected) / len(packages) * 100
        results["solvers"][solver_name] = {"status": "OK", "time_seconds": round(elapsed, 4), "selected": len(selected), "accuracy": round(accuracy, 1), "conflicts": conflicts, "unmet_deps": unmet}
        print(f"  {solver_name:<20s}: {len(selected):>3}/{len(packages)} in {elapsed:.4f}s | {accuracy:.1f}% | {conflicts} conflicts | {unmet} unmet")
    except Exception as e:
        elapsed = time.perf_counter() - start
        results["solvers"][solver_name] = {"status": "ERROR", "time": round(elapsed, 4), "error": str(e)[:80]}
        print(f"  {solver_name:<20s}: ERROR - {e}")

ok = {k:v for k,v in results["solvers"].items() if v["status"]=="OK"}
if ok:
    fastest = min(ok.items(), key=lambda x: x[1]["time_seconds"])
    print(f"\nFastest: {fastest[0]} ({fastest[1]['time_seconds']}s)")
    print(f"\n{'Solver':<20s} {'Time':<10s} {'Selected':<10s} {'Accuracy':<10s} {'Conflicts':<10s} {'Unmet':<8s}")
    print(f"{'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    for name, d in sorted(ok.items(), key=lambda x: x[1]["time_seconds"]):
        print(f"{name:<20s} {d['time_seconds']:<10.4f} {d['selected']:<10d} {d['accuracy']:<10.1f} {d['conflicts']:<10d} {d['unmet_deps']:<8d}")

with open("real_world_benchmark_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved to real_world_benchmark_results.json")
