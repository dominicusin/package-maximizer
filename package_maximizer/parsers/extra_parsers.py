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
                    deps = [
                        d.get("name")
                        for d in pkg.get("dependencies", [])
                        if d.get("name")
                    ]
                    packages.append(
                        Package(
                            name=name, version=version, status="candidate", depends=deps
                        )
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
                    Package(
                        name=m.group(1), version=m.group(2) or "", status="candidate"
                    )
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
                        version = (
                            info.get("version", "") if isinstance(info, dict) else ""
                        )
                        deps = (
                            [
                                d
                                for d in info.get("dependencies", {})
                                if isinstance(info, dict)
                            ]
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


class CondaParser(PackageParser):
    """
    Parser for ``conda list`` output.

    Example::

        numpy              1.23.5  conda-forge
        pandas             2.0.0   defaults
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                packages.append(Package(name=name, version=version, status="installed"))
        return packages


class PortageParser(PackageParser):
    """
    Parser for ``emerge -p`` / portage output.

    Example::

        [ebuild   r] app-editors/vim-8.2.0
        [ebuild   r] sys-apps/less-590
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            if "[" in line and "]" in line:
                pkg_part = line.split("]")[-1].strip()
                if "/" in pkg_part:
                    name = pkg_part.split("/")[-1].split("-")[0]
                    version = pkg_part.split("/")[-1].split("-", 1)[-1]
                    packages.append(
                        Package(name=name, version=version, status="candidate")
                    )
        return packages


class ApkParser(PackageParser):
    """
    Parser for ``apk list`` output on Alpine Linux.

    Example::

        alpine-baselayout-3.14.0-r1 x86_64 3.14.0-r1 ~main
        busybox-1.32.1-r1 x86_64 1.32.1-r1 ~main
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("-"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            full_name = parts[0]
            # APK: name-version-release where version starts with digit
            # Split on first '-' that precedes a digit
            m = re.match(r"^([A-Za-z0-9_\-\.]+?)-([0-9][\w\.\-]*)$", full_name)
            if m:
                name = m.group(1)
                version = m.group(2)
            else:
                name = full_name
                version = ""
            packages.append(
                Package(name=name, version=version or "", status="installed")
            )
        return packages


class ZypperParser(PackageParser):
    """
    Parser for ``zypper search`` output on openSUSE/SUSE.

    Example::

        S | Name                  | Type   | Version       | Arch   | Repository
        --+-----------------------+-------+---------------+--------+-----------
          | vim                   | package | 8.2.3895-1.2 | x86_64 | Main
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("Loading") or line.startswith("Reading"):
                continue
            if "Name" in line or line.startswith("S |") or line.startswith("--+"):
                continue
            if "|" in line:
                cols = [c.strip() for c in line.split("|")]
                if len(cols) >= 4:
                    name = cols[1]
                    version = cols[3]
                    if name and not name.startswith("-") and version:
                        packages.append(
                            Package(name=name, version=version, status="candidate")
                        )
        return packages


class YumParser(PackageParser):
    """
    Parser for ``yum list installed`` output on RHEL/CentOS.

    Example::

        Installed Packages
        git.x86_64               1:2.23.1-1.el8                @baseos
        vim-enhanced.x86_64      2:8.0.1763-13.5.el8           @appstream
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("Loaded") or line.startswith("Installed"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                full_name = parts[0]
                if "." in full_name:
                    name = full_name.rsplit(".", 1)[0]
                else:
                    name = full_name
                version = parts[1].split(":")[-1] if ":" in parts[1] else parts[1]
                packages.append(Package(name=name, version=version, status="installed"))
        return packages


class PipParser(PackageParser):
    """
    Parser for ``pip list`` or ``pip freeze`` output.

    Examples::

        Package    Version
        ---------- -------
        certifi    2022.9.24
        requests   2.28.1

        certifi==2022.9.24
        requests>=2.28.1
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        in_table = False

        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if "Package" in line and "Version" in line:
                in_table = True
                continue
            if in_table:
                if line.startswith("---"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    packages.append(
                        Package(name=parts[0], version=parts[1], status="installed")
                    )
                continue
            m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=!~]+)\s*(.+)$", line)
            if m:
                packages.append(
                    Package(name=m.group(1), version=m.group(3), status="installed")
                )
        return packages


class GemParser(PackageParser):
    """
    Parser for ``gem list`` output.

    Example::

        *** LOCAL GEMS ***

        actioncable (6.1.4, 6.1.3, 6.0.4)
        actionmailbox (6.1.4)
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        in_gems = False

        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("***"):
                in_gems = True
                continue
            if in_gems and line.startswith("---"):
                continue
            if in_gems:
                m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*\(([^)]+)\)$", line)
                if m:
                    name = m.group(1)
                    versions = [v.strip() for v in m.group(2).split(",") if v.strip()]
                    version = versions[0] if versions else ""
                else:
                    m2 = re.match(r"^([A-Za-z0-9_\-\.]+)$", line)
                    if m2:
                        name = m2.group(1)
                        version = ""
                    else:
                        continue
                packages.append(Package(name=name, version=version, status="installed"))
        return packages


class YarnParser(PackageParser):
    """
    Parser for ``yarn list --depth=0`` output.

    Example::

        ├─ yarn@1.22.17
        ├─ lodash@4.17.21
        └─ react@18.2.0
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            clean = re.sub(r"^[├└│─\s]+", "", line.strip())
            if not clean:
                continue
            m = re.match(r"^([A-Za-z0-9_@/.\-]+)@([0-9][\w.\-]*)$", clean)
            if m:
                packages.append(
                    Package(name=m.group(1), version=m.group(2), status="installed")
                )
        return packages


class ComposerParser(PackageParser):
    """
    Parser for ``composer show --installed`` output.

    Example::

        name     : laravel/framework
        versions : * 8.83.26
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        current_name = None
        current_version = ""

        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                if current_name:
                    packages.append(
                        Package(
                            name=current_name,
                            version=current_version,
                            status="installed",
                        )
                    )
                    current_name = None
                continue
            m_name = re.match(r"^name\s*:\s*(.+)$", line)
            if m_name:
                if current_name:
                    packages.append(
                        Package(
                            name=current_name,
                            version=current_version,
                            status="installed",
                        )
                    )
                current_name = m_name.group(1).strip()
                current_version = ""
                continue
            m_version = re.match(r"^versions?\s*:\s*(.+)$", line)
            if m_version and current_name:
                m_ver = re.search(r"([\d\.]+)$", m_version.group(1))
                current_version = m_ver.group(1) if m_ver else ""

        if current_name:
            packages.append(
                Package(name=current_name, version=current_version, status="installed")
            )
        return packages


class VcpkgParser(PackageParser):
    """
    Parser for ``vcpkg list`` output.

    Example::

        bzip2:x64-windows         1.0.8         installed
        cmake:x64-windows         3.24.2        installed
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("-"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name_arch = parts[0]
                version = parts[1]
                name = name_arch.split(":")[0] if ":" in name_arch else name_arch
                if name and version:
                    packages.append(
                        Package(name=name, version=version, status="installed")
                    )
        return packages


class NuGetParser(PackageParser):
    """
    Parser for ``dotnet list package`` output.

    Example::

        Top-level Package      Version
        --------------------   -------
        Newtonsoft.Json        13.0.1
        Serilog                2.10.0
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        in_table = False

        for line in raw.strip().splitlines():
            line = line.strip()
            if "Package" in line and "Version" in line:
                in_table = True
                continue
            if in_table:
                if line.startswith("---"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    packages.append(
                        Package(name=parts[0], version=parts[1], status="installed")
                    )
        return packages


class WingetParser(PackageParser):
    """
    Parser for ``winget list`` output on Windows.

    Example::

        Name                     Id                            Version
        -----------------------  ----------------------------  -------
        7-Zip 21.70 (x64)        7zip.7zip                    21.07
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        lines = raw.strip().splitlines()
        start_idx = 0
        for i, line in enumerate(lines):
            if "Name" in line or "--" in line:
                start_idx = i + 1
                break
        for line in lines[start_idx:]:
            line = line.strip()
            if not line or line.startswith("---"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                version = parts[-1]
                name = " ".join(parts[:-2])
                name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
                if name and version:
                    packages.append(
                        Package(name=name, version=version, status="installed")
                    )
        return packages


class ScoopParser(PackageParser):
    """
    Parser for ``scoop list`` output on Windows.

    Example::

        Installed apps:

          7zip 22.01 : main
          git  2.38.1 : extras
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        in_list = False

        for line in raw.strip().splitlines():
            line = line.strip()
            if "Installed" in line and "apps" in line:
                in_list = True
                continue
            if in_list and line and ":" in line:
                pkg_part, _ = line.rsplit(":", 1)
                pkg_parts = pkg_part.strip().split()
                if len(pkg_parts) >= 2:
                    name = pkg_parts[0]
                    version = pkg_parts[-1]
                    packages.append(
                        Package(name=name, version=version, status="installed")
                    )
        return packages


class ChocoParser(PackageParser):
    """
    Parser for ``choco list`` output on Windows.

    Example::

        Chocolatey v1.2.1
        7zip 22.01
        git 2.38.1
        2 packages installed.
    """

    def parse(self, raw: str) -> list[Package]:
        if not raw.strip():
            return []

        packages: list[Package] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("Chocolatey") or "packages" in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and re.match(r"^\d", parts[-1]):
                name = parts[0]
                version = parts[1]
                packages.append(Package(name=name, version=version, status="installed"))
        return packages
