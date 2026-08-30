"""Tests for newly added package-manager parsers (snap/flatpak/cargo/npm)."""

from __future__ import annotations

from package_maximizer.parsers import (
    SnapParser,
    FlatpakParser,
    CargoParser,
    NpmParser,
)
from package_maximizer.parsers import PARSER_REGISTRY, get_parser


SNAP_LIST = """Name           Version          Rev    Tracking         Publisher
core           16-2.58.3        14936  latest/stable    canonical*
lxd            5.0.2            24322  latest/stable    canonical*
"""

FLATPAK_LIST = """Application                       Version
org.gnome.Platform              44.0
com.spotify.Client              1.2.13
"""

CARGO_META = r'''{
  "packages": [
    {"name": "serde", "version": "1.0.0", "dependencies": [{"name": "serde_derive"}]},
    {"name": "serde_derive", "version": "1.0.0", "dependencies": []}
  ]
}'''

NPM_LS = r'''{
  "dependencies": {
    "lodash": {"version": "4.17.21"},
    "react": {"version": "18.2.0", "dependencies": {"scheduler": {"version": "0.23.0"}}}
  }
}'''


class TestNewParsers:
    """New parsers should produce correct Package objects from real output."""

    def test_snap_parser(self):
        pkgs = SnapParser().parse(SNAP_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "core"
        assert pkgs[0].version == "16-2.58.3"
        assert pkgs[0].status == "installed"

    def test_flatpak_parser(self):
        pkgs = FlatpakParser().parse(FLATPAK_LIST)
        assert {p.name for p in pkgs} == {"org.gnome.Platform", "com.spotify.Client"}
        assert any(p.version == "1.2.13" for p in pkgs)

    def test_cargo_json(self):
        pkgs = CargoParser().parse(CARGO_META)
        names = {p.name for p in pkgs}
        assert names == {"serde", "serde_derive"}
        serde = next(p for p in pkgs if p.name == "serde")
        assert serde.depends == ["serde_derive"]

    def test_cargo_text_fallback(self):
        pkgs = CargoParser().parse("tokio v1.0.0\nrand 0.8.5\n")
        assert {p.name for p in pkgs} == {"tokio", "rand"}

    def test_npm_json(self):
        pkgs = NpmParser().parse(NPM_LS)
        names = {p.name for p in pkgs}
        assert names == {"lodash", "react", "scheduler"}
        react = next(p for p in pkgs if p.name == "react")
        assert react.depends == ["scheduler"]

    def test_npm_text_fallback(self):
        pkgs = NpmParser().parse("lodash@4.17.21\nreact@18.2.0\n")
        assert {p.name for p in pkgs} == {"lodash", "react"}

    def test_registry_includes_new_parsers(self):
        for key in ("snap", "flatpak", "cargo", "npm"):
            assert key in PARSER_REGISTRY
            assert isinstance(get_parser(key), PackageParser := __import__(
                "package_maximizer.core.interfaces", fromlist=["PackageParser"]
            ).PackageParser)
