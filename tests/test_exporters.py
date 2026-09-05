"""Tests for result exporters (JSON / CSV / GraphML)."""

from __future__ import annotations

import json
# NOTE: ET.fromstring is used here only to validate Package Maximizer's own
# generated GraphML (trusted local output), not untrusted external input, so
# the standard parser is safe in this test context.
import xml.etree.ElementTree as ET

from package_maximizer.core.package import Package
from package_maximizer.utils.exporters import to_csv, to_graphml, to_json


def _build() -> tuple[list[Package], list[str]]:
    pkgs = [
        Package(name="vim", conflicts=["emacs"]),
        Package(name="emacs", conflicts=["vim"]),
        Package(name="nano"),
    ]
    selected = ["vim", "nano"]
    return pkgs, selected


class TestExporters:
    """Exporters should produce valid, parseable output."""

    def test_to_json(self):
        pkgs, selected = _build()
        out = to_json(pkgs, selected)
        data = json.loads(out)
        assert set(data["selected"]) == {"vim", "nano"}
        assert "emacs" in data["rejected"]
        assert len(data["packages"]) == 3

    def test_to_csv(self):
        pkgs, selected = _build()
        out = to_csv(pkgs, selected)
        lines = out.strip().splitlines()
        assert lines[0] == "name,version,selected,conflicts,depends"
        # vim is selected -> third column is "true"
        vim_row = next(line for line in lines[1:] if line.startswith("vim,"))
        assert "true" in vim_row.split(",")

    def test_to_graphml_is_valid_xml(self):
        pkgs, selected = _build()
        out = to_graphml(pkgs, selected)
        root = ET.fromstring(out)
        assert root.tag.endswith("graphml")
        # 2 packages + conflict edge (emacs<->vim) + 1 selected node
        nodes = root.findall(".//{http://graphml.graphdrawing.org/xmlns}node")
        edges = root.findall(".//{http://graphml.graphdrawing.org/xmlns}edge")
        assert len(nodes) == 3
        assert len(edges) == 1  # vim <-> emacs conflict
