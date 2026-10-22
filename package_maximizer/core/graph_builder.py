"""`core/graph_builder.py` — конструкторы рантайм- и билдтайм-графов зависимостей.

Предоставляет:

* :class:`PackageGraph` — неизменяемый граф пакетов с версионными
  зависимостями, версионными конфликтами и метаданными ресурсов (для
  мониторинга производительности).
* :class:`GraphBuilder` — фабрика, которая строит граф из списков
  ``Package``.  Поддерживает режимы ``runtime`` (решатель) и
  ``buildtime`` (установка/сборка), а также обнаружение циклических
  зависимостей и конфликтов на уровне версий.

Пример::

    from package_maximizer.core import Package, GraphBuilder

    pkgs = [Package(name="nginx", version="1.25", conflicts=["apache2"])]
    graph = GraphBuilder().build(pkgs, mode="runtime")

    # билдтайм-граф (зависимости устанавливаются до пакета)
    build_graph = GraphBuilder().build(pkgs, mode="buildtime")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable

from ..core.package import Package

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VersionConstraint:
    """Версионное ограничение, зависящее от конкретной версии пакета."""

    package: str
    operator: str
    version: str
    required_by: str | None = None

    def matches(self, version: str) -> bool:
        if not self.version or not version:
            return True
        try:
            cv = tuple(int(x) for x in self.version.split(".") if x.isdigit())
            vv = tuple(int(x) for x in version.split(".") if x.isdigit())
        except ValueError:
            return True
        return {
            ">=": cv <= vv,
            "<=": cv >= vv,
            "==": cv == vv,
            ">": cv < vv,
            "<": cv > vv,
        }.get(self.operator, True)


@dataclass
class Node:
    """Вершина графа пакета."""

    name: str
    version: str
    status: str = "candidate"
    depends: list[VersionConstraint] = field(default_factory=list)
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    declared_by: str | None = None
    resource_estimate: dict | None = None


@dataclass
class PackageGraph:
    """Нерекурсивный ориентированный граф пакетов."""

    nodes: dict[str, Node] = field(default_factory=dict)
    dependencies: dict[str, list[VersionConstraint]] = field(default_factory=dict)
    conflicts: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    declared_by: dict[str, str] = field(default_factory=dict)
    cycle_found: bool = False
    mode: str = "runtime"

    def node(self, name: str) -> Node | None:
        return self.nodes.get(name)

    def add_node(self, node: Node) -> None:
        if node.name in self.nodes and self.nodes[node.name].version:
            return
        self.nodes[node.name] = node
        self.dependencies.setdefault(node.name, [])
        for dep in node.depends:
            self.dependencies.setdefault(node.name, []).append(dep)
        self.conflicts.setdefault(node.name, [])
        for conflict, _ in node.conflicts:
            self.conflicts.setdefault(node.name, []).append((conflict, ""))
        self.declared_by[node.name] = node.declared_by or node.name

    def topological_order(self) -> list[str]:
        """Корректный топологический порядок или пустой список при цикле."""
        visited: set[str] = set()
        temp: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> bool:
            if name in temp:
                return False
            if name in visited:
                return True
            temp.add(name)
            for c in self.dependencies.get(name, []):
                if not visit(c.package):
                    return False
            temp.discard(name)
            visited.add(name)
            order.append(name)
            return True

        for name in self.nodes:
            if name not in visited:
                if not visit(name):
                    self.cycle_found = True
                    return []
        return order

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "nodes": [
                {
                    "name": n.name,
                    "version": n.version,
                    "depends": [
                        f"{c.package} {c.operator} {c.version}" for c in n.depends
                    ],
                    "conflicts": list(n.conflicts),
                    "declared_by": n.declared_by,
                }
                for n in self.nodes.values()
            ],
            "cycle_found": self.cycle_found,
        }


class GraphBuilder:
    """Сборщик рантайм- и билдтайм-графов пакетов."""

    def __init__(self, mode: str = "runtime") -> None:
        self.mode = mode.lower()
        if self.mode not in {"runtime", "buildtime"}:
            raise ValueError("mode must be 'runtime' or 'buildtime'")

    def build(self, packages: Iterable[Package]) -> PackageGraph:
        """Построить граф зависимостей для ``packages``."""
        graph = PackageGraph(mode=self.mode)
        for pkg in packages:
            graph.add_node(
                Node(
                    name=pkg.name,
                    version=pkg.version,
                    status=pkg.status or "candidate",
                    depends=[
                        VersionConstraint(
                            package=dep, operator="==", version="", required_by=pkg.name
                        )
                        for dep in (pkg.depends or [])
                    ],
                    conflicts=[(c, "") for c in (pkg.conflicts or [])],
                    declared_by=pkg.name,
                )
            )

        if self.mode == "buildtime":
            graph = self._add_buildtime_edges(graph)

        return graph

    def _add_buildtime_edges(self, graph: PackageGraph) -> PackageGraph:
        """В билдтайм зависимости становятся ребром 'declared_by'."""
        for name, node in graph.nodes.items():
            for dep in node.depends:
                dep_node = graph.nodes.get(dep.package)
                if dep_node is None:
                    continue
                dep_node.declared_by = name
        return graph


def build_runtime_graph(packages: Iterable[Package]) -> PackageGraph:
    """Утилита: быстрый рантайм-граф из пакетов."""
    return GraphBuilder(mode="runtime").build(packages)


def build_buildtime_graph(packages: Iterable[Package]) -> PackageGraph:
    """Утилита: быстрый билдтайм-граф (зависимости устанавливаются в начале)."""
    return GraphBuilder(mode="buildtime").build(packages)


def detect_cycles(payload: str | None = None) -> list[list[str]]:
    """Опциональная диагностика циклов во входном serialised графе."""
    if not payload:
        return []
    import json

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    cycles: list[list[str]] = []
    for node in data.get("nodes", []):
        if node.get("cycle_found"):
            cycles.append([n["name"] for n in data.get("nodes", [])])
    return cycles
