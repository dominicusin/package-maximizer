"""Package Maximizer Web API — Flask-based REST API with API-key authentication."""

from __future__ import annotations

import os
import time
from functools import wraps
from typing import Any

from flask import Flask, g, jsonify, request

from ..core.enums import PackageManagerType, SolverType
from ..core.maximizer import PackageMaximizer
from ..core.package import Package
from ..utils import BenchmarkRunner, CacheManager

app = Flask(__name__)

# ─── Configuration ───────────────────────────────────────────
try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _dist_version

    try:
        APP_VERSION = _dist_version("package-maximizer")
    except PackageNotFoundError:
        APP_VERSION = "0.6.1"
except ImportError:  # pragma: no cover
    APP_VERSION = "0.6.1"

API_KEY = os.environ.get("PM_API_KEY", "")
CACHE_ENABLED = os.environ.get("PM_CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.environ.get("PM_CACHE_TTL", "3600"))

cache = CacheManager() if CACHE_ENABLED else None


# ─── Rate limiting (in-memory, per API key) ────────────────
class RateLimiter:
    """Fixed-window rate limiter keyed by client identity."""

    def __init__(self, max_requests: int = 100, window: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window = window
        self._hits: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits.get(key, [])
        hits = [t for t in hits if now - t < self.window]
        if len(hits) >= self.max_requests:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


RATE_LIMITER = RateLimiter(
    max_requests=int(os.environ.get("PM_RATE_LIMIT", "100")),
    window=float(os.environ.get("PM_RATE_WINDOW", "60")),
)


# ─── Input validation ────────────────────────────────────────
MAX_PACKAGES = int(os.environ.get("PM_MAX_PACKAGES", "5000"))
MAX_NAME_LEN = int(os.environ.get("PM_MAX_NAME_LEN", "256"))


def validate_maximize_payload(data: Any) -> tuple[list[str], list, dict | None]:
    """
    Validate the JSON body for /api/v1/maximize.

    Returns ``(cleaned_pkgs, conflicts, weights)`` when valid, or raises a
    ``ValueError`` whose message is client-safe.
    """
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    if "packages" not in data:
        raise ValueError("Missing 'packages' field in request body")

    raw_packages = data.get("packages")
    if not isinstance(raw_packages, list):
        raise ValueError("'packages' must be a list of strings")

    cleaned: list[str] = []
    for pkg in raw_packages:
        if not isinstance(pkg, str):
            raise ValueError("Each package name must be a string")
        name = pkg.strip()
        if not name:
            raise ValueError("Package names must not be empty")
        if len(name) > MAX_NAME_LEN:
            raise ValueError(f"Package name too long (max {MAX_NAME_LEN} chars)")
        cleaned.append(name)

    if len(cleaned) > MAX_PACKAGES:
        raise ValueError(f"Too many packages (max {MAX_PACKAGES})")

    conflicts = data.get("conflicts", [])
    if conflicts is not None and not isinstance(conflicts, list):
        raise ValueError("'conflicts' must be a list of [a, b] pairs")

    weights = data.get("weights", None)
    if weights is not None:
        if not isinstance(weights, dict):
            raise ValueError("'weights' must be an object mapping name -> number")
        for k, v in weights.items():
            if not isinstance(k, str):
                raise ValueError("Weight keys must be strings")
            try:
                float(v)  # type: ignore[arg-type]
            except TypeError, ValueError:
                raise ValueError(f"Weight for '{k}' must be numeric")

    return cleaned, conflicts, weights  # type: ignore[return-value]


# ─── Request timing middleware ───────────────────────────────
@app.before_request
def before_request():
    g.start_time = time.time()


@app.after_request
def after_request(response):
    if hasattr(g, "start_time"):
        elapsed = time.time() - g.start_time
        response.headers["X-Response-Time"] = f"{elapsed:.4f}s"
    return response


# ─── Authentication decorator ────────────────────────────────
def require_api_key(f):
    """Simple API key authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth for health check
        if request.endpoint == "health":
            return f(*args, **kwargs)

        # Check API key
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not api_key or api_key != API_KEY:
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Missing or invalid API key. Provide X-API-Key header.",
                    }
                ),
                401,
            )
        # Rate limiting (per API key)
        if not RATE_LIMITER.is_allowed(api_key):
            return (
                jsonify(
                    {
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded ({RATE_LIMITER.max_requests} per "
                        f"{int(RATE_LIMITER.window)}s).",
                    }
                ),
                429,
            )

        return f(*args, **kwargs)

    return decorated


# ─── Health check ────────────────────────────────────────────
@app.get("/api/health")
def health() -> tuple[dict, int]:
    """Health check endpoint."""
    return (
        jsonify(
            {
                "status": "ok",
                "version": APP_VERSION,
                "cache_enabled": CACHE_ENABLED,
                "timestamp": time.time(),
            }
        ),
        200,
    )


# ─── List available solvers ──────────────────────────────────
@app.get("/api/v1/solvers")
@require_api_key
def list_solvers() -> tuple[dict, int]:
    """List all available solvers."""
    from ..solvers import SOLVER_REGISTRY

    solvers = []
    for name, cls in SOLVER_REGISTRY.items():
        doc = cls.__doc__ or "No description"
        solvers.append(
            {
                "name": name,
                "description": doc.strip().split("\n")[0],
                "class": cls.__name__,
            }
        )
    return jsonify({"solvers": solvers}), 200


# ─── List available parsers ──────────────────────────────────
@app.get("/api/v1/parsers")
@require_api_key
def list_parsers() -> tuple[dict, int]:
    """List all available parsers."""
    from ..parsers import PARSER_REGISTRY

    parsers = []
    for name, cls in PARSER_REGISTRY.items():
        doc = cls.__doc__ or "No description"
        parsers.append(
            {
                "name": name,
                "description": doc.strip().split("\n")[0],
                "class": cls.__name__,
            }
        )
    return jsonify({"parsers": parsers}), 200


# ─── List available managers (package managers) ──────────────
@app.get("/api/v1/managers")
@require_api_key
def list_managers() -> tuple[dict, int]:
    """List all available package managers (parsers)."""
    from ..parsers import PARSER_REGISTRY

    managers = []
    for name, cls in PARSER_REGISTRY.items():
        doc = cls.__doc__ or "No description"
        managers.append(
            {
                "name": name,
                "description": doc.strip().split("\n")[0],
                "class": cls.__name__,
            }
        )
    return jsonify({"managers": managers, "count": len(managers)}), 200


# ─── Maximize packages ───────────────────────────────────────
@app.post("/api/v1/maximize")
@require_api_key
def maximize_post() -> tuple[dict, int]:
    """
    Maximize packages from JSON body.

    Expected JSON body::

        {
            "packages": ["pkg1", "pkg2", "pkg3"],
            "manager": "apt",
            "solver": "greedy",
            "conflicts": [["pkg1", "pkg2"]],
            "depends": [["pkg1", "pkg2"]],
            "weights": {"pkg1": 2.0, "pkg2": 1.5},
            "explain": false
        }
    """
    data = request.get_json(force=True)
    try:
        packages, conflicts, weights = validate_maximize_payload(data)
    except ValueError as e:
        return (
            jsonify({"error": "Bad Request", "message": str(e)}),
            400,
        )

    manager = data.get("manager", "apt")
    solver = data.get("solver", "greedy")

    # Validate manager
    try:
        manager_enum = PackageManagerType(manager)
    except ValueError:
        valid = [m.value for m in PackageManagerType]
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": f"Unknown manager '{manager}'. Valid: {valid}",
                }
            ),
            400,
        )

    # Validate solver
    from ..solvers import SOLVER_REGISTRY

    if solver not in SOLVER_REGISTRY:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": f"Unknown solver '{solver}'. Valid: {list(SOLVER_REGISTRY.keys())}",
                }
            ),
            400,
        )

    # Build package objects
    package_objs = []
    conflict_map: dict[str, list[str]] = {}
    for pkg_name in packages:
        pkg = Package(name=pkg_name, status="candidate")
        package_objs.append(pkg)

    # Apply conflicts
    for c in conflicts:
        if isinstance(c, (list, tuple)) and len(c) == 2:
            conflict_map.setdefault(c[0], []).append(c[1])
            conflict_map.setdefault(c[1], []).append(c[0])

    for pkg in package_objs:
        if pkg.name in conflict_map:
            pkg.conflicts = conflict_map[pkg.name]

    # Apply dependencies from 'depends' field
    depends_raw = data.get("depends", [])
    dep_map: dict[str, list[str]] = {}
    for dep_entry in depends_raw:
        if isinstance(dep_entry, (list, tuple)) and len(dep_entry) == 2:
            pkg_name, dep_name = dep_entry
            dep_map.setdefault(pkg_name, []).append(dep_name)

    for pkg in package_objs:
        if pkg.name in dep_map:
            pkg.depends = dep_map[pkg.name]

    explain = data.get("explain", False)

    # Solve
    try:
        maximizer = PackageMaximizer(manager=manager_enum, solver=solver)

        if weights:
            result = maximizer.solve_with_weights(package_objs, weights)
        else:
            result = maximizer.solve(package_objs)
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    response_data = {
        "manager": manager,
        "solver": solver,
        "input_count": len(packages),
        "output_count": len(result),
        "selected": result,
        "input": packages,
    }

    if explain:
        from ..core.model_encoder import encode_packages

        constraints = encode_packages(package_objs)
        selected_set = set(result)
        all_names = {p.name for p in package_objs}
        excluded = all_names - selected_set

        excluded_reasons = {}
        for name in sorted(excluded):
            reasons = []
            for a, b in constraints.conflicts:
                if a == name and b in selected_set:
                    reasons.append(f"conflict with {b}")
                elif b == name and a in selected_set:
                    reasons.append(f"conflict with {a}")
            deps = constraints.dependencies.get(name, [])
            for dep in deps:
                if dep not in selected_set:
                    reasons.append(f"dependency not selected: {dep}")
            excluded_reasons[name] = reasons if reasons else ["not optimal"]

        response_data["excluded"] = excluded_reasons

    return (
        jsonify(response_data),
        200,
    )


# ─── Propose packages ─────────────────────────────────────────
@app.post("/api/v1/propose")
@require_api_key
def propose_post() -> tuple[dict, int]:
    """
    Propose optimal package set with automatic metadata extraction.

    Expected JSON body::

        {
            "packages": ["requests", "certifi"],
            "manager": "apt",
            "solver": "greedy",
            "explain": false
        }
    """
    data = request.get_json(force=True)
    if not isinstance(data, dict):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Request body must be a JSON object",
                }
            ),
            400,
        )
    if "packages" not in data:
        return (
            jsonify({"error": "Bad Request", "message": "Missing 'packages' field"}),
            400,
        )

    packages = data.get("packages")
    if not isinstance(packages, list):
        return (
            jsonify({"error": "Bad Request", "message": "'packages' must be a list"}),
            400,
        )

    manager = data.get("manager", "apt")
    solver = data.get("solver", "greedy")
    explain = data.get("explain", False)

    # Validate manager
    try:
        manager_enum = PackageManagerType(manager)
    except ValueError:
        valid = [m.value for m in PackageManagerType]
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": f"Unknown manager '{manager}'. Valid: {valid}",
                }
            ),
            400,
        )

    # Validate solver
    from ..solvers import SOLVER_REGISTRY

    if solver not in SOLVER_REGISTRY:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": f"Unknown solver '{solver}'. Valid: {list(SOLVER_REGISTRY.keys())}",
                }
            ),
            400,
        )

    # Get adapter for metadata extraction
    from ..adapters import get_adapter

    try:
        adapter = get_adapter(manager)
    except ValueError as e:
        return jsonify({"error": "Bad Request", "message": str(e)}), 400

    package_objs = []
    not_found = []
    metadata_summary = []
    for pkg_name in packages:
        if not isinstance(pkg_name, str):
            continue
        metadata = adapter.fetch(pkg_name)
        if metadata and metadata.name:
            package_objs.append(metadata.to_package())
            metadata_summary.append(
                {
                    "name": metadata.name,
                    "version": metadata.version,
                    "depends": metadata.depends,
                    "conflicts": metadata.conflicts,
                }
            )
        else:
            not_found.append(pkg_name)
            package_objs.append(Package(name=pkg_name, status="candidate"))
            metadata_summary.append({"name": pkg_name, "depends": [], "conflicts": []})

    if not package_objs:
        return (
            jsonify({"error": "Bad Request", "message": "No packages to process"}),
            400,
        )

    try:
        maximizer = PackageMaximizer(manager=manager_enum, solver=solver)
        result = maximizer.solve(package_objs)
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    response_data = {
        "manager": manager,
        "solver": solver,
        "input_count": len(packages),
        "output_count": len(result),
        "selected": result,
        "input": packages,
        "metadata_fetched": len(packages) - len(not_found),
        "metadata": metadata_summary,
    }

    if not_found:
        response_data["not_found"] = not_found

    if explain:
        from ..core.model_encoder import encode_packages

        constraints = encode_packages(package_objs)
        selected_set = set(result)
        all_names = {p.name for p in package_objs}
        excluded = all_names - selected_set

        excluded_reasons = {}
        for name in sorted(excluded):
            reasons = []
            for a, b in constraints.conflicts:
                if a == name and b in selected_set:
                    reasons.append(f"conflict with {b}")
                elif b == name and a in selected_set:
                    reasons.append(f"conflict with {a}")
            deps = constraints.dependencies.get(name, [])
            for dep in deps:
                if dep not in selected_set:
                    reasons.append(f"dependency not selected: {dep}")
            excluded_reasons[name] = reasons if reasons else ["not optimal"]
        response_data["excluded"] = excluded_reasons

    return jsonify(response_data), 200


# ─── GET version (for backward compat) ───────────────────────
@app.get("/api/maximize")
@require_api_key
def maximize_get() -> tuple[dict, int]:
    """GET /api/maximize?packages=vim,nano&manager=apt&solver=pulp"""
    raw = request.args.get("packages", "")
    names = [n.strip() for n in raw.split(",") if n.strip()]
    if not names:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Query parameter 'packages' is required",
                }
            ),
            400,
        )

    manager = request.args.get("manager", "apt")
    solver = request.args.get("solver", "greedy")
    weights_raw = request.args.get("weights")

    weights = None
    if weights_raw:
        weights = {}
        for item in weights_raw.split(","):
            parts = item.split(":")
            if len(parts) == 2:
                try:
                    weights[parts[0]] = float(parts[1])
                except ValueError:
                    pass

    # Forward to POST handler logic
    data = {"packages": names, "manager": manager, "solver": solver, "weights": weights}
    with app.test_request_context(
        method="POST", json=data, headers=dict(request.headers)
    ):
        return maximize_post()


# ─── Export endpoint ──────────────────────────────────────────
@app.post("/api/v1/export")
@require_api_key
def export_post() -> (
    tuple[dict, int] | tuple[str, int] | tuple[str, int, dict[str, str]]
):
    """
    Maximize packages and return the result in JSON/CSV/GraphML.

    Body is the same as /api/v1/maximize plus an ``format`` field
    (json | csv | graphml).
    """
    from ..utils.exporters import to_csv, to_graphml, to_json

    try:
        packages, conflicts, weights = validate_maximize_payload(
            request.get_json(force=True)
        )
    except ValueError as e:
        return jsonify({"error": "Bad Request", "message": str(e)}), 400

    data = request.get_json(force=True)
    manager = data.get("manager", "apt")
    solver = data.get("solver", "greedy")
    fmt = (data.get("format") or "json").lower()

    try:
        manager_enum = PackageManagerType(manager)
    except ValueError:
        return (
            jsonify(
                {"error": "Bad Request", "message": f"Unknown manager '{manager}'"}
            ),
            400,
        )

    from ..solvers import SOLVER_REGISTRY

    if solver not in SOLVER_REGISTRY:
        return (
            jsonify({"error": "Bad Request", "message": f"Unknown solver '{solver}'"}),
            400,
        )

    pkg_objs = [Package(name=n, status="candidate") for n in packages]
    conflict_map: dict[str, list[str]] = {}
    for c in conflicts:
        if isinstance(c, (list, tuple)) and len(c) == 2:
            conflict_map.setdefault(c[0], []).append(c[1])
            conflict_map.setdefault(c[1], []).append(c[0])
    for p in pkg_objs:
        if p.name in conflict_map:
            p.conflicts = conflict_map[p.name]

    try:
        maximizer = PackageMaximizer(manager=manager_enum, solver=solver)
        selected = (
            maximizer.solve(pkg_objs)
            if not weights
            else maximizer.solve_with_weights(pkg_objs, weights)
        )
    except Exception as e:  # pragma: no cover - defensive
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    if fmt == "csv":
        return to_csv(pkg_objs, selected), 200, {"Content-Type": "text/csv"}
    if fmt == "graphml":
        return to_graphml(pkg_objs, selected), 200, {"Content-Type": "application/xml"}
    return to_json(pkg_objs, selected), 200, {"Content-Type": "application/json"}


# ─── Benchmark endpoint ──────────────────────────────────────
@app.post("/api/v1/benchmark")
@require_api_key
def benchmark_post() -> tuple[dict, int]:
    """Run benchmark on specified solvers."""
    from ..solvers import SOLVER_REGISTRY

    data = request.get_json(force=True) or {}

    solver_names = data.get("solvers", list(SOLVER_REGISTRY.keys()))
    package_count = data.get("package_count", 100)
    runs = data.get("runs", 3)

    runner = BenchmarkRunner(runs=runs)
    packages = runner.generate_test_packages(package_count)

    results = []
    for solver_name in solver_names:
        result = runner.run_benchmark(solver_name, packages)
        results.append(
            {
                "solver": result.solver_name,
                "avg_time": result.avg_time,
                "min_time": result.min_time,
                "max_time": result.max_time,
                "selected": result.selected_count,
                "success": result.success,
                "error": result.error,
            }
        )

    # Sort by avg_time (use float() for type safety)
    results.sort(key=lambda r: float(r["avg_time"]))

    return (
        jsonify(
            {
                "results": results,
                "package_count": package_count,
                "runs_per_solver": runs,
                "best_solver": results[0]["solver"] if results else None,
            }
        ),
        200,
    )


# ─── Cache stats endpoint ────────────────────────────────────
@app.get("/api/v1/cache/stats")
@require_api_key
def cache_stats() -> tuple[dict, int]:
    """Get cache statistics."""
    if cache is None:
        return jsonify({"cache_enabled": False}), 200
    return jsonify(cache.get_stats()), 200


@app.delete("/api/v1/cache")
@require_api_key
def cache_clear() -> tuple[dict, int]:
    """Clear the cache."""
    if cache is None:
        return jsonify({"cache_enabled": False}), 200
    count = cache.clear()
    return jsonify({"cleared": count}), 200


# ─── Error handlers ──────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return (
        jsonify(
            {"error": "Not Found", "message": "The requested resource was not found"}
        ),
        404,
    )


@app.errorhandler(405)
def method_not_allowed(e):
    return (
        jsonify(
            {
                "error": "Method Not Allowed",
                "message": "The HTTP method is not allowed for this endpoint",
            }
        ),
        405,
    )


@app.errorhandler(500)
def internal_error(e):
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            }
        ),
        500,
    )


# ─── OpenAPI / API docs (self-documenting, no extra deps) ──
@app.get("/api/v1/openapi.json")
def openapi_spec() -> tuple[dict, int]:
    """Machine-readable API description (OpenAPI 3.0 subset)."""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Package Maximizer API",
            "version": APP_VERSION,
            "description": "Maximize a consistent set of packages across managers.",
        },
        "security": [{"ApiKeyAuth": []}],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            }
        },
        "paths": {
            "/api/v1/maximize": {
                "post": {
                    "summary": "Maximize a set of packages",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "packages": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "manager": {"type": "string"},
                                        "solver": {"type": "string"},
                                        "conflicts": {"type": "array"},
                                        "weights": {"type": "object"},
                                    },
                                    "required": ["packages"],
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Maximized package set"}},
                }
            },
            "/api/v1/export": {
                "post": {
                    "summary": "Maximize and export (json|csv|graphml)",
                    "responses": {"200": {"description": "Exported result"}},
                }
            },
            "/api/v1/benchmark": {
                "post": {
                    "summary": "Run solver benchmarks",
                    "responses": {"200": {"description": "Benchmark results"}},
                }
            },
            "/api/v1/solvers": {
                "get": {
                    "summary": "List available solvers",
                    "responses": {"200": {"description": "Solver list"}},
                }
            },
            "/api/v1/parsers": {
                "get": {
                    "summary": "List available parsers",
                    "responses": {"200": {"description": "Parser list"}},
                }
            },
            "/api/v1/cache/stats": {
                "get": {
                    "summary": "Cache statistics",
                    "responses": {"200": {"description": "Cache stats"}},
                }
            },
        },
    }
    return jsonify(spec), 200


@app.get("/api/v1/docs")
def api_docs() -> tuple[str, int]:
    """Minimal human-readable API documentation page."""
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Package Maximizer API</title></head><body>"
        "<h1>Package Maximizer API</h1>"
        "<p>All endpoints require header <code>X-API-Key</code>.</p>"
        "<ul>"
        "<li><b>POST /api/v1/maximize</b> — maximize a package set</li>"
        "<li><b>POST /api/v1/export</b> — maximize &amp; export (json/csv/graphml)</li>"
        "<li><b>POST /api/v1/benchmark</b> — run solver benchmarks</li>"
        "<li><b>GET /api/v1/solvers</b> — list solvers</li>"
        "<li><b>GET /api/v1/parsers</b> — list parsers</li>"
        "<li><b>GET /api/v1/cache/stats</b> — cache statistics</li>"
        "<li><b>GET /api/v1/openapi.json</b> — OpenAPI spec</li>"
        "</ul>"
        "<p>See <a href='/api/v1/openapi.json'>openapi.json</a>.</p>"
        "</body></html>"
    )
    return html, 200, {"Content-Type": "text/html"}


# ─── Run app ─────────────────────────────────────────────────
def run_app(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Run the Flask application."""
    if not API_KEY:
        import sys

        print(
            "ERROR: PM_API_KEY environment variable is required to start the web server.\n"
            "Set it with: export PM_API_KEY=your-secret-key\n"
            "Or start with: PM_API_KEY=xxx pm-web",
            file=sys.stderr,
        )
        sys.exit(1)
    app.run(host=host, port=port, debug=debug)


# Backward compatibility
run = run_app
