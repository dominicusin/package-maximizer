"""Metadata adapters — парсеры метаданных пакетных менеджеров.

Каждый адаптер преобразует вывод конкретного менеджера в единый формат
Package с заполненными depends и conflicts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PackageMetadata:
    """Единый формат метаданных пакета."""

    name: str
    version: str = ""
    description: str = ""
    depends: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    size: int = 0
    homepage: str = ""

    def to_package(self) -> "Package":
        from ..core.package import Package

        return Package(
            name=self.name,
            version=self.version,
            depends=self.depends,
            conflicts=self.conflicts,
            status="candidate",
        )


class APTMetadataAdapter:
    """Парсер метаданных APT (apt-cache show / dpkg -s)."""

    def parse(self, raw: str) -> PackageMetadata | None:
        """Разобрать вывод apt-cache show или dpkg -s."""
        if not raw.strip():
            return None

        metadata = PackageMetadata(name="")
        lines = raw.strip().split("\n")
        current_field = None
        current_value = []

        for line in lines:
            line = line.rstrip()

            # Новое поле (не продолжение)
            if line and not line.startswith(" ") and not line.startswith("\t"):
                # Сохраняем предыдущее поле
                if current_field:
                    self._set_field(metadata, current_field, "\n".join(current_value))

                if ":" in line:
                    current_field, value = line.split(":", 1)
                    current_field = current_field.strip()
                    current_value = [value.strip()]
                else:
                    current_field = None
                    current_value = []
            elif line.strip() and current_field:
                # Продолжение поля
                current_value.append(line.strip())

        # Последнее поле
        if current_field:
            self._set_field(metadata, current_field, "\n".join(current_value))

        if not metadata.name:
            return None

        return metadata

    def _set_field(self, metadata: PackageMetadata, field: str, value: str) -> None:
        field_lower = field.lower()

        if field_lower == "package":
            metadata.name = value.strip()
        elif field_lower == "version":
            metadata.version = value.strip()
        elif field_lower == "description":
            # Берём только первую строку
            metadata.description = value.split("\n")[0].strip()
        elif field_lower == "depends" or field_lower == "pre-depends":
            metadata.depends.extend(self._parse_apt_deps(value))
        elif field_lower == "conflicts" or field_lower == "breaks":
            metadata.conflicts.extend(self._parse_apt_deps(value))
        elif field_lower == "provides":
            metadata.provides.extend(self._parse_apt_deps(value))
        elif field_lower == "installed-size":
            try:
                metadata.size = int(value.split()[0])
            except ValueError, IndexError:
                pass
        elif field_lower == "homepage":
            metadata.homepage = value.strip()

    def _parse_apt_deps(self, raw: str) -> list[str]:
        """Разбрать зависимости APT: 'libc6 (>= 2.27), libgcc-s1' -> ['libc6', 'libgcc-s1']."""
        deps = []
        for dep_group in raw.split(","):
            dep_group = dep_group.strip()
            if not dep_group:
                continue

            # Убираем альтернативы (pkg1 | pkg2) — берём первый
            if "|" in dep_group:
                dep_group = dep_group.split("|")[0].strip()

            # Убираем ограничение версии: 'libc6 (>= 2.27)' -> 'libc6'
            match = re.match(r"^(\S+)", dep_group)
            if match:
                deps.append(match.group(1))

        return deps

    def parse_multi(self, raw: str) -> list[PackageMetadata]:
        """Разобрать вывод с несколькими пакетами (apt-cache show pkg1 pkg2)."""
        if not raw.strip():
            return []

        packages = []
        # Разделяем по пустой строке между пакетами
        blocks = re.split(r"\n\n+", raw.strip())

        for block in blocks:
            pkg = self.parse(block)
            if pkg and pkg.name:
                packages.append(pkg)

        return packages


class PipMetadataAdapter:
    """Парсер метаданных pip (pip show / METADATA)."""

    def parse(self, raw: str) -> PackageMetadata | None:
        """Разобрать вывод pip show."""
        if not raw.strip():
            return None

        metadata = PackageMetadata(name="")
        lines = raw.strip().split("\n")
        current_field = None
        current_value = []

        for line in lines:
            line = line.rstrip()

            if line and not line.startswith(" ") and not line.startswith("\t"):
                if current_field:
                    self._set_field(metadata, current_field, "\n".join(current_value))

                if ":" in line:
                    current_field, value = line.split(":", 1)
                    current_field = current_field.strip()
                    current_value = [value.strip()]
                else:
                    current_field = None
                    current_value = []
            elif line.strip() and current_field:
                current_value.append(line.strip())

        if current_field:
            self._set_field(metadata, current_field, "\n".join(current_value))

        if not metadata.name:
            return None

        return metadata

    def _set_field(self, metadata: PackageMetadata, field: str, value: str) -> None:
        field_lower = field.lower()

        if field_lower == "name":
            metadata.name = value.strip()
        elif field_lower == "version":
            metadata.version = value.strip()
        elif field_lower == "summary":
            metadata.description = value.strip()
        elif field_lower == "requires":
            metadata.depends.extend(self._parse_pip_deps(value))
        elif field_lower == "requires-dist":
            metadata.depends.extend(self._parse_pip_deps(value))
        elif field_lower == "conflicts":
            metadata.conflicts.extend(self._parse_pip_deps(value))
        elif field_lower == "home-page":
            metadata.homepage = value.strip()

    def _parse_pip_deps(self, raw: str) -> list[str]:
        """Разбрать зависимости pip: 'requests (>=2.0), certifi' -> ['requests', 'certifi']."""
        if not raw.strip():
            return []

        deps = []
        for dep in raw.split(","):
            dep = dep.strip()
            if not dep:
                continue

            # Убираем ограничение версии
            match = re.match(r"^([A-Za-z0-9_\-\.]+)", dep)
            if match:
                deps.append(match.group(1))

        return deps


class PacmanMetadataAdapter:
    """Парсер метаданных pacman (pacman -Si / -Qi)."""

    def parse(self, raw: str) -> PackageMetadata | None:
        """Разобрать вывод pacman -Si или -Qi."""
        if not raw.strip():
            return None

        metadata = PackageMetadata(name="")
        lines = raw.strip().split("\n")
        current_field = None
        current_value = []

        for line in lines:
            line = line.rstrip()

            if line and not line.startswith(" "):
                if current_field:
                    self._set_field(metadata, current_field, "\n".join(current_value))

                if ":" in line:
                    current_field, value = line.split(":", 1)
                    current_field = current_field.strip()
                    current_value = [value.strip()]
                else:
                    current_field = None
                    current_value = []
            elif line.strip() and current_field:
                current_value.append(line.strip())

        if current_field:
            self._set_field(metadata, current_field, "\n".join(current_value))

        if not metadata.name:
            return None

        return metadata

    def _set_field(self, metadata: PackageMetadata, field: str, value: str) -> None:
        field_lower = field.lower()

        if field_lower == "name":
            metadata.name = value.strip()
        elif field_lower == "version":
            metadata.version = value.strip()
        elif field_lower == "description":
            metadata.description = value.strip()
        elif field_lower == "depends on":
            metadata.depends.extend(self._parse_pacman_deps(value))
        elif field_lower == "conflicts with":
            metadata.conflicts.extend(self._parse_pacman_deps(value))
        elif field_lower == "provides":
            metadata.provides.extend(self._parse_pacman_deps(value))

    def _parse_pacman_deps(self, raw: str) -> list[str]:
        """Разбрать зависимости pacman: 'libc python' -> ['libc', 'python']."""
        if not raw.strip() or raw.strip().lower() == "none":
            return []

        deps = []
        for dep in raw.split():
            dep = dep.strip()
            if dep:
                deps.append(dep)

        return deps
