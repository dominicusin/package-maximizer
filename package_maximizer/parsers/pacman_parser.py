"""
Pacman Parser - Парсер для пакетов Pacman (Arch Linux).
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


class PacmanParser(PackageParser):
    """
    Парсер для работы с пакетами Pacman (Arch Linux).

    Поддерживает разбор различных форматов вывода:
    - pacman -Q (установленные пакеты)
    - pacman -Ss (поиск пакетов)
    - pacman -Si (информация о пакете)
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
        # Проверяем более специфичные форматы сначала
        if "Name" in raw and "Version" in raw and "Depends On" in raw:
            packages.extend(self._parse_pacman_si(raw))
        elif "core/" in raw or "extra/" in raw or "community/" in raw:
            packages.extend(self._parse_pacman_q(raw))
        elif "Repository" in raw and "Name" in raw:
            packages.extend(self._parse_pacman_ss(raw))
        else:
            packages.extend(self._parse_simple_list(raw))

        return packages

    def _parse_pacman_q(self, raw: str) -> list[Package]:
        """
        Разобрать формат pacman -Q.

        Пример:
        core/linux 6.6.10.arch1-1
        extra/vim 9.1.0000-1
        """
        packages = []
        lines = raw.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Формат: repo/name version
            parts = line.split()
            if len(parts) >= 2:
                repo_name = parts[0]
                version = parts[1]
                name = repo_name.split("/")[-1] if "/" in repo_name else repo_name

                packages.append(Package(name=name, version=version, status="installed"))

        return packages

    def _parse_pacman_ss(self, raw: str) -> list[Package]:
        """
        Разобрать формат pacman -Ss.

        Пример:
        core/linux 6.6.10.arch1-1 [installed]
        extra/vim 9.1.0000-1
        """
        packages = []
        lines = raw.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("Repository"):
                continue

            # Формат: repo/name version [status]
            parts = line.split()
            if len(parts) >= 2:
                repo_name = parts[0]
                version = parts[1]
                name = repo_name.split("/")[-1] if "/" in repo_name else repo_name

                # Проверка статуса
                if "[installed]" in line:
                    status = "installed"
                else:
                    status = "candidate"

                packages.append(Package(name=name, version=version, status=status))

        return packages

    def _parse_pacman_si(self, raw: str) -> list[Package]:
        """
        Разобрать формат pacman -Si.

        Пример:
        Repository     : core
        Name            : linux
        Version        : 6.6.10.arch1-1
        Depends On     : coreutils  glibc
        Conflicts With : linux-lts
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
            elif current_pkg and line.startswith("Depends On"):
                depends = line.split(":", 1)[1].strip()
                deps = [d.strip() for d in depends.split() if d.strip()]
                current_pkg.depends = deps
            elif current_pkg and line.startswith("Conflicts With"):
                conflicts = line.split(":", 1)[1].strip()
                conflicts_list = [c.strip() for c in conflicts.split() if c.strip()]
                current_pkg.conflicts = conflicts_list
            elif current_pkg and line.startswith("Status"):
                status_line = line.split(":", 1)[1].strip()
                if "installed" in status_line:
                    current_pkg.status = "installed"

        if current_pkg:
            packages.append(current_pkg)

        # Фильтруем пакеты с пустыми именами
        packages = [p for p in packages if p.name]

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
