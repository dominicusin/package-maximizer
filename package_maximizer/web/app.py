"""Минимальный веб-интерфейс Package Maximizer (Flask)."""

from __future__ import annotations

from flask import Flask, jsonify, request

from ..core.enums import PackageManagerType, SolverType
from ..core.maximizer import PackageMaximizer
from ..core.package import Package

app = Flask(__name__)


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/maximize")
def maximize():
    """GET /api/maximize?packages=vim,nano&manager=apt&solver=pulp"""
    raw = request.args.get("packages", "")
    names = [n.strip() for n in raw.split(",") if n.strip()]
    if not names:
        return jsonify(error="параметр 'packages' обязателен"), 400
    try:
        manager = PackageManagerType(request.args.get("manager", "apt"))
        solver = SolverType(request.args.get("solver", "pulp"))
    except ValueError as e:
        return jsonify(error=str(e)), 400

    engine = PackageMaximizer(manager=manager, solver=solver)
    chosen = engine.maximize(PackageMaximizer.from_names(names))
    return jsonify(
        manager=manager.value,
        solver=solver.value,
        input=names,
        maximized=[p.name for p in chosen],
    )


def run(host: str = "127.0.0.1", port: int = 5000) -> None:
    app.run(host=host, port=port)
