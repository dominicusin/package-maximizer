"""
DNF Parser - Парсер для пакетов DNF (Fedora/RHEL).
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import TYPE_CHECKING

from ..core.interfaces import PackageParser
from ..core.package import Package

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DNFParser(PackageParser):
    """
    Парсер для работы с пакетами DNF (Fedora/RHEL/CentOS).

    Поддерживает разбор различных форматов вывода:
    - dnf list installed
    - dnf info
    - dnf search
    - Простой список имен пакетов
    """

    def __init__(self, use_cache: bool = True) -> None:
        """
        Инициализация парсера.

        Args:
            use_cache: Использовать кэширование
        """
        self.use_cache = use_cache

    def parse(self, raw: str) -> list[Package]:
        """
        Разобрать сырые данные в объекты Package.

        Args:
            raw: Сырые текстовые данные

        Returns:
            Список объектов Package
        """
        if not raw.strip():
            return []

        packages = []

        # Определяем формат данных
        if "Installed Packages" in raw or "Available Packages" in raw:
            packages.extend(self._parse_dnf_list(raw))
        elif "Name" in raw and "Version" in raw and "Release" in raw:
            packages.extend(self._parse_dnf_info(raw))
        elif ":" in raw and any(
            "x86_64" in line or ":" in line for line in raw.split("\n")
        ):
            packages.extend(self._parse_dnf_search(raw))
        else:
            packages.extend(self._parse_simple_list(raw))

        return packages

    def _parse_dnf_list(self, raw: str) -> list[Package]:
        """
        Разобрать формат dnf list installed.

        Пример:
        Installed Packages
        kernel-core.x86_64  6.6.10-100.fc39  @updates
        vim-enhanced.x86_64  2:9.1.0000-1.fc39  @fedora

        Available Packages
        python3.x86_64  3.11.0-1.fc39  fedora
        """
        packages = []
        lines = raw.strip().split("\n")

        current_section = None

        for line in lines:
            line = line.strip()

            if line == "Installed Packages":
                current_section = "installed"
                continue
            elif line == "Available Packages":
                current_section = "available"
                continue

            if not line or line.startswith("-") or line.startswith("Last"):
                continue

            # Формат: name.arch version repo
            parts = line.split()
            if len(parts) >= 2:
                # Извлекаем имя (без архитектуры)
                full_name = parts[0]
                name = full_name.split(".")[0] if "." in full_name else full_name
                version = parts[1]

                status = "installed" if current_section == "installed" else "candidate"

                packages.append(Package(name=name, version=version, status=status))

        return packages

    def _parse_dnf_info(self, raw: str) -> list[Package]:
        """
        Разобрать формат dnf info.

        Пример:
        Name         : kernel-core
        Version      : 6.6.10
        Release      : 100.fc39
        Architecture : x86_64
        Depends On   : kernel = 6.6.10-100.fc39
        Conflicts With: kernel < 6.6.10
        """
        packages = []
        current_pkg = None
        lines = raw.strip().split("\n")

        for line in lines:
            line = line.strip()

            if line.startswith("Name"):
                if current_pkg:
                    packages.append(current_pkg)
                current_pkg = Package(name=line.split(":", 1)[1].strip())
            elif current_pkg and line.startswith("Version"):
                current_pkg.version = line.split(":", 1)[1].strip()
            elif current_pkg and line.startswith("Release"):
                # Добавляем release к версии
                release = line.split(":", 1)[1].strip()
                if current_pkg.version:
                    current_pkg.version = f"{current_pkg.version}-{release}"
                else:
                    current_pkg.version = release
            elif current_pkg and line.startswith("Depends On"):
                depends = line.split(":", 1)[1].strip()
                deps = [d.strip().split()[0] for d in depends.split(",") if d.strip()]
                current_pkg.depends = deps
            elif current_pkg and line.startswith("Conflicts With"):
                conflicts = line.split(":", 1)[1].strip()
                conflicts_list = [
                    c.strip().split()[0] for c in conflicts.split(",") if c.strip()
                ]
                current_pkg.conflicts = conflicts_list
            elif current_pkg and line.startswith("Installed"):
                if "Yes" in line:
                    current_pkg.status = "installed"

        if current_pkg:
            packages.append(current_pkg)

        return packages

    def _parse_dnf_search(self, raw: str) -> list[Package]:
        """
        Разобрать формат dnf search.

        Пример:
        kernel-core.x86_64 : The Linux kernel
        vim-enhanced.x86_64 : A version of the VIM editor
        """
        packages = []
        lines = raw.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("Last"):
                continue

            # Формат: name.arch : description
            if ":" in line:
                name_arch, description = line.split(":", 1)
                name = (
                    name_arch.strip().split(".")[0]
                    if "." in name_arch
                    else name_arch.strip()
                )

                packages.append(Package(name=name.strip(), status="candidate"))

        return packages

    def _parse_simple_list(self, raw: str) -> list[Package]:
        """
        Разобрать простой список имен пакетов.
        """
        packages = []
        lines = raw.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line:
                packages.append(Package(name=line, status="candidate"))

        return packages
