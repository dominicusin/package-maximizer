"""
Parsers for additional package managers.

Supports the universal multi-manager platform goal by adding readers for:
- snap   (``snap list``)
- flatpak (``flatpak list --columns=...``)
- cargo  (``cargo metadata`` JSON / Cargo.lock)
- npm    (``npm ls --json`` / ``npm list`` text)

Each parser follows the ``PackageParser`` interface so it plugs into the
existing ``PARSER_REGISTRY`` and CLI without changes elsewhere.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from ..core.interfaces import PackageParser
from ..core.package import Package

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SnapParser(PackageParser):
    """
    Parser for ``snap list`` output.

    Example::

        Name           Version          Rev    Tracking         Publisher
        core           16-2.58.3        14936  latest/stable    canonical*
        lxd            5.0.2            ...
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        lines = raw.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("Name") or line.startswith("---"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0]
            version = parts[1] if len(parts) > 1 else ""
            packages.append(Package(name=name, version=version, status="installed"))
        return packages


class FlatpakParser(PackageParser):
    """
    Parser for ``flatpak list`` output.

    Example (``flatpak list --columns=application,version``)::

        org.gnome.Platform        44.0
        com.spotify.Client        1.2.13
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        lines = raw.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("Application") or line.startswith("---"):
                continue
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            version = parts[1] if len(parts) > 1 else ""
            packages.append(Package(name=name, version=version, status="installed"))
        return packages


class CargoParser(PackageParser):
    """
    Parser for Cargo outputs.

    Accepts:
    - ``cargo metadata --format-version 1`` JSON (preferred)
    - plain dependency list (one crate per line)

    Example JSON top-level ``packages`` entries carry ``name`` and
    ``version``; optional ``dependencies`` carry ``name``.
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        text = raw.strip()
        # Fast path: JSON metadata
        if text.startswith("{"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("CargoParser: invalid JSON, falling back to text")
            else:
                packages: list[Package] = []
                for pkg in data.get("packages", []):
                    name = pkg.get("name", "")
                    version = pkg.get("version", "")
                    deps = [d.get("name") for d in pkg.get("dependencies", []) if d.get("name")]
                    packages.append(
                        Package(name=name, version=version, status="candidate", depends=deps)
                    )
                return packages

        # Fallback: simple name (optionally with version) per line
        return self._parse_simple(text)

    @staticmethod
    def _parse_simple(text: str) -> list[Package]:
        packages: list[Package] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Accept "crate v1.2.3" or just "crate"
            m = re.match(r"^([A-Za-z0-9_\-]+)\s*(?:v?([0-9][\w.\-]*))?", line)
            if m:
                packages.append(
                    Package(name=m.group(1), version=m.group(2) or "", status="candidate")
                )
        return packages


class NpmParser(PackageParser):
    """
    Parser for npm outputs.

    Accepts:
    - ``npm ls --json`` output (recursive dependency tree)
    - plain ``npm list`` text (``package@version`` lines)

    Example JSON::

        {
          "dependencies": {
            "lodash": {"version": "4.17.21"},
            "react":  {"version": "18.2.0", "dependencies": {"scheduler": {...}}}
          }
        }
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        text = raw.strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("NpmParser: invalid JSON, falling back to text")
            else:
                seen: set[str] = set()
                packages: list[Package] = []

                def _walk(node: dict, parent: str | None = None) -> None:
                    for name, info in node.get("dependencies", {}).items():
                        if name in seen:
                            continue
                        seen.add(name)
                        version = info.get("version", "") if isinstance(info, dict) else ""
                        deps = (
                            [d for d in info.get("dependencies", {}) if isinstance(info, dict)]
                            if isinstance(info, dict)
                            else []
                        )
                        packages.append(
                            Package(
                                name=name,
                                version=version,
                                status="candidate",
                                depends=deps,
                            )
                        )
                        if isinstance(info, dict) and info.get("dependencies"):
                            _walk(info, name)

                _walk(data)
                return packages

        # Fallback: "name@version" text lines
        packages: list[Package] = []
        for line in text.split("\n"):
            line = line.strip()
            m = re.search(r"([A-Za-z0-9_@/.\-]+)@([0-9][\w.\-]*)", line)
            if m:
                packages.append(
                    Package(name=m.group(1), version=m.group(2), status="candidate")
                )
        return packages
