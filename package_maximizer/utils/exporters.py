"""
Result exporters for Package Maximizer.

Serialize maximization results and dependency/conflict graphs to multiple
formats: JSON, CSV, and GraphML (for visualization in external tools such as
yEd, Gephi, or NetworkX).
"""

from __future__ import annotations

import csv
import io
import json
from typing import Iterable, Sequence

from ..core.package import Package


def to_json(
    packages: Sequence[Package],
    selected: Iterable[str],
    *,
    metadata: dict | None = None,
) -> str:
    """
    Export results as a JSON string.

    Args:
        packages: All candidate packages.
        selected: Names of selected (maximized) packages.
        metadata: Optional extra fields to include at top level.

    Returns:
        JSON-formatted string.
    """
    selected_set = set(selected)
    payload: dict = {
        "selected": sorted(selected_set),
        "rejected": sorted(p.name for p in packages if p.name not in selected_set),
        "packages": [
            {
                "name": p.name,
                "version": p.version,
                "selected": p.name in selected_set,
                "conflicts": list(p.conflicts),
                "depends": list(p.depends),
            }
            for p in packages
        ],
    }
    if metadata:
        payload["metadata"] = metadata
    return json.dumps(payload, indent=2, ensure_ascii=False)


def to_csv(packages: Sequence[Package], selected: Iterable[str]) -> str:
    """
    Export results as CSV (name,version,selected,conflicts,depends).

    Args:
        packages: All candidate packages.
        selected: Names of selected packages.

    Returns:
        CSV-formatted string.
    """
    selected_set = set(selected)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "version", "selected", "conflicts", "depends"])
    for p in packages:
        writer.writerow(
            [
                p.name,
                p.version,
                "true" if p.name in selected_set else "false",
                ";".join(p.conflicts),
                ";".join(p.depends),
            ]
        )
    return buf.getvalue()


def to_graphml(packages: Sequence[Package], selected: Iterable[str]) -> str:
    """
    Export the conflict/dependency graph as GraphML.

    Nodes are packages (``selected`` attribute marks the result set).
    Edges are conflicts (type="conflict") and dependencies (type="depends").

    Args:
        packages: All candidate packages.
        selected: Names of selected packages.

    Returns:
        GraphML-formatted XML string.
    """
    selected_set = set(selected)
    names = {p.name for p in packages}

    nodes: list[str] = []
    for p in packages:
        nodes.append(
            f'    <node id="{_esc(p.name)}">\n'
            f'      <data key="selected">{str(p.name in selected_set).lower()}</data>\n'
            f'      <data key="version">{_esc(p.version)}</data>\n'
            f'    </node>'
        )

    edges: list[str] = []
    edge_id = 0
    seen_edges: set[frozenset] = set()
    for p in packages:
        for dep in p.depends:
            if dep in names:
                key = frozenset({p.name, dep})
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(_edge(edge_id, p.name, dep, "depends"))
                    edge_id += 1
        for conflict in p.conflicts:
            if conflict in names:
                key = frozenset({p.name, conflict})
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(_edge(edge_id, p.name, conflict, "conflict"))
                    edge_id += 1

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
        '  <key id="selected" for="node" attr.name="selected" attr.type="boolean"/>\n'
        '  <key id="version" for="node" attr.name="version" attr.type="string"/>\n'
        '  <key id="etype" for="edge" attr.name="type" attr.type="string"/>\n'
        '  <graph id="package-maximizer" edgedefault="undirected">\n'
        f'{chr(10).join(nodes)}\n'
        f'{chr(10).join(edges)}\n'
        '  </graph>\n'
        '</graphml>\n'
    )


def _edge(edge_id: int, src: str, dst: str, etype: str) -> str:
    return (
        f'    <edge id="e{edge_id}" source="{_esc(src)}" target="{_esc(dst)}">\n'
        f'      <data key="etype">{etype}</data>\n'
        f'    </edge>'
    )


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
