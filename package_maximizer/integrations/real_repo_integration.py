"""
Real Repository Integration - Интеграция с реальными репозиториями пакетов.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..core.package import Package
from ..parsers import APTParser, PacmanParser, DNFParser, BrewParser

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class RepoConfig:
    """Конфигурация репозитория."""
    name: str
    url: str
    package_manager: str
    enabled: bool = True
    
    def get_parser(self):
        """Получить парсер для этого репозитория."""
        parsers = {
            "apt": APTParser,
            "pacman": PacmanParser,
            "dnf": DNFParser,
            "brew": BrewParser,
        }
        return parsers.get(self.package_manager, APTParser)()


@dataclass
class PackageInfo:
    """Информация о пакете из репозитория."""
    name: str
    version: str = ""
    description: str = ""
    depends: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    size: int = 0
    installed: bool = False
    
    def to_package(self) -> Package:
        """Преобразовать в объект Package."""
        return Package(
            name=self.name,
            version=self.version,
            depends=self.depends,
            conflicts=self.conflicts,
            status="installed" if self.installed else "candidate"
        )


class RealRepoIntegration:
    """
    Интеграция с реальными репозиториями пакетов.
    
    Поддерживает:
    - Получение списка пакетов из репозитория
    - Поиск пакетов
    - Получение информации о пакете
    - Проверка установленных пакетов
    """

    def __init__(self, package_manager: str = "apt") -> None:
        """
        Инициализация интеграции.
        
        Args:
            package_manager: Тип пакетного менеджера
        """
        self.package_manager = package_manager
        self.parser = self._get_parser()

    def _get_parser(self):
        """Получить парсер для текущего менеджера."""
        parsers = {
            "apt": APTParser,
            "pacman": PacmanParser,
            "dnf": DNFParser,
            "brew": BrewParser,
        }
        return parsers.get(self.package_manager, APTParser)()

    def get_installed_packages(self) -> list[Package]:
        """
        Получить список установленных пакетов.
        
        Returns:
            Список установленных пакетов
        """
        if self.package_manager == "apt":
            return self._get_installed_apt()
        elif self.package_manager == "pacman":
            return self._get_installed_pacman()
        elif self.package_manager == "dnf":
            return self._get_installed_dnf()
        elif self.package_manager == "brew":
            return self._get_installed_brew()
        else:
            return []

    def _get_installed_apt(self) -> list[Package]:
        """Получить установленные пакеты через APT."""
        try:
            result = subprocess.run(
                ['dpkg', '-l'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get installed APT packages: {e}")
        return []

    def _get_installed_pacman(self) -> list[Package]:
        """Получить установленные пакеты через Pacman."""
        try:
            result = subprocess.run(
                ['pacman', '-Q'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get installed Pacman packages: {e}")
        return []

    def _get_installed_dnf(self) -> list[Package]:
        """Получить установленные пакеты через DNF."""
        try:
            result = subprocess.run(
                ['dnf', 'list', 'installed'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get installed DNF packages: {e}")
        return []

    def _get_installed_brew(self) -> list[Package]:
        """Получить установленные пакеты через Brew."""
        try:
            result = subprocess.run(
                ['brew', 'list', '--formula', '--cask'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get installed Brew packages: {e}")
        return []

    def search_packages(self, query: str, limit: int = 20) -> list[Package]:
        """
        Поиск пакетов по запросу.
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных пакетов
        """
        if self.package_manager == "apt":
            return self._search_apt(query, limit)
        elif self.package_manager == "pacman":
            return self._search_pacman(query, limit)
        elif self.package_manager == "dnf":
            return self._search_dnf(query, limit)
        elif self.package_manager == "brew":
            return self._search_brew(query, limit)
        else:
            return []

    def _search_apt(self, query: str, limit: int) -> list[Package]:
        """Поиск пакетов через APT."""
        try:
            result = subprocess.run(
                ['apt-cache', 'search', query],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                packages = self.parser.parse(result.stdout)
                return packages[:limit]
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to search APT packages: {e}")
        return []

    def _search_pacman(self, query: str, limit: int) -> list[Package]:
        """Поиск пакетов через Pacman."""
        try:
            result = subprocess.run(
                ['pacman', '-Ss', query],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                packages = self.parser.parse(result.stdout)
                return packages[:limit]
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to search Pacman packages: {e}")
        return []

    def _search_dnf(self, query: str, limit: int) -> list[Package]:
        """Поиск пакетов через DNF."""
        try:
            result = subprocess.run(
                ['dnf', 'search', query],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                packages = self.parser.parse(result.stdout)
                return packages[:limit]
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to search DNF packages: {e}")
        return []

    def _search_brew(self, query: str, limit: int) -> list[Package]:
        """Поиск пакетов через Brew."""
        try:
            result = subprocess.run(
                ['brew', 'search', query],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                packages = self.parser.parse(result.stdout)
                return packages[:limit]
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to search Brew packages: {e}")
        return []

    def get_package_info(self, package_name: str) -> PackageInfo | None:
        """
        Получить информацию о пакете.
        
        Args:
            package_name: Имя пакета
            
        Returns:
            Информация о пакете или None
        """
        if self.package_manager == "apt":
            return self._get_package_info_apt(package_name)
        elif self.package_manager == "pacman":
            return self._get_package_info_pacman(package_name)
        elif self.package_manager == "dnf":
            return self._get_package_info_dnf(package_name)
        elif self.package_manager == "brew":
            return self._get_package_info_brew(package_name)
        else:
            return None

    def _get_package_info_apt(self, package_name: str) -> PackageInfo | None:
        """Получить информацию о пакете через APT."""
        try:
            result = subprocess.run(
                ['apt-cache', 'show', package_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # Разбираем вывод
                info = PackageInfo(name=package_name)
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Version:'):
                        info.version = line.split(':', 1)[1].strip()
                    elif line.startswith('Description:'):
                        info.description = line.split(':', 1)[1].strip()
                    elif line.startswith('Depends:'):
                        deps = line.split(':', 1)[1].strip()
                        info.depends = [d.strip().split()[0] for d in deps.split(',') if d.strip()]
                    elif line.startswith('Conflicts:'):
                        conflicts = line.split(':', 1)[1].strip()
                        info.conflicts = [c.strip().split()[0] for c in conflicts.split(',') if c.strip()]
                    elif line.startswith('Installed-Size:'):
                        size_str = line.split(':', 1)[1].strip()
                        try:
                            info.size = int(size_str.split()[0])
                        except ValueError:
                            pass
                return info
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get APT package info: {e}")
        return None

    def _get_package_info_pacman(self, package_name: str) -> PackageInfo | None:
        """Получить информацию о пакете через Pacman."""
        try:
            result = subprocess.run(
                ['pacman', '-Si', package_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                info = PackageInfo(name=package_name)
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Version'):
                        info.version = line.split(':', 1)[1].strip()
                    elif line.startswith('Description'):
                        info.description = line.split(':', 1)[1].strip()
                    elif line.startswith('Depends On'):
                        deps = line.split(':', 1)[1].strip()
                        info.depends = [d.strip() for d in deps.split() if d.strip()]
                    elif line.startswith('Conflicts With'):
                        conflicts = line.split(':', 1)[1].strip()
                        info.conflicts = [c.strip() for c in conflicts.split() if c.strip()]
                return info
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get Pacman package info: {e}")
        return None

    def _get_package_info_dnf(self, package_name: str) -> PackageInfo | None:
        """Получить информацию о пакете через DNF."""
        try:
            result = subprocess.run(
                ['dnf', 'info', package_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                info = PackageInfo(name=package_name)
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Version'):
                        info.version = line.split(':', 1)[1].strip().split()[0]
                    elif line.startswith('Summary'):
                        info.description = line.split(':', 1)[1].strip()
                    elif line.startswith('Requires'):
                        deps = line.split(':', 1)[1].strip()
                        info.depends = [d.strip().split()[0] for d in deps.split(',') if d.strip()]
                    elif line.startswith('Conflicts'):
                        conflicts = line.split(':', 1)[1].strip()
                        info.conflicts = [c.strip().split()[0] for c in conflicts.split(',') if c.strip()]
                return info
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get DNF package info: {e}")
        return None

    def _get_package_info_brew(self, package_name: str) -> PackageInfo | None:
        """Получить информацию о пакете через Brew."""
        try:
            result = subprocess.run(
                ['brew', 'info', package_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                info = PackageInfo(name=package_name)
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if 'Stable version:' in line or 'Version:' in line:
                        info.version = line.split(':', 1)[1].strip()
                    elif line.startswith('Dependencies:'):
                        deps = line.split(':', 1)[1].strip()
                        info.depends = [d.strip() for d in deps.split(',') if d.strip()]
                    elif line.startswith('Conflicts with:'):
                        conflicts = line.split(':', 1)[1].strip()
                        info.conflicts = [c.strip() for c in conflicts.split(',') if c.strip()]
                return info
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get Brew package info: {e}")
        return None

    def check_package_installed(self, package_name: str) -> bool:
        """
        Проверить, установлен ли пакет.
        
        Args:
            package_name: Имя пакета
            
        Returns:
            True, если пакет установлен
        """
        installed = self.get_installed_packages()
        return any(p.name == package_name for p in installed)

    def get_available_updates(self) -> list[Package]:
        """
        Получить список доступных обновлений.
        
        Returns:
            Список пакетов с обновлениями
        """
        if self.package_manager == "apt":
            return self._get_available_updates_apt()
        elif self.package_manager == "pacman":
            return self._get_available_updates_pacman()
        elif self.package_manager == "dnf":
            return self._get_available_updates_dnf()
        elif self.package_manager == "brew":
            return self._get_available_updates_brew()
        else:
            return []

    def _get_available_updates_apt(self) -> list[Package]:
        """Получить доступные обновления через APT."""
        try:
            result = subprocess.run(
                ['apt', 'list', '--upgradable'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get APT updates: {e}")
        return []

    def _get_available_updates_pacman(self) -> list[Package]:
        """Получить доступные обновления через Pacman."""
        try:
            result = subprocess.run(
                ['pacman', '-Qu'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get Pacman updates: {e}")
        return []

    def _get_available_updates_dnf(self) -> list[Package]:
        """Получить доступные обновления через DNF."""
        try:
            result = subprocess.run(
                ['dnf', 'check-update'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get DNF updates: {e}")
        return []

    def _get_available_updates_brew(self) -> list[Package]:
        """Получить доступные обновления через Brew."""
        try:
            result = subprocess.run(
                ['brew', 'outdated'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self.parser.parse(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get Brew updates: {e}")
        return []

    def get_system_info(self) -> dict[str, Any]:
        """
        Получить информацию о системе.
        
        Returns:
            Словарь с информацией о системе
        """
        info = {
            "package_manager": self.package_manager,
            "installed_packages": len(self.get_installed_packages()),
            "available_updates": len(self.get_available_updates()),
        }
        
        # Пробуем получить версию пакетного менеджера
        try:
            if self.package_manager == "apt":
                result = subprocess.run(['apt', '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info["pm_version"] = result.stdout.split('\n')[0].strip()
            elif self.package_manager == "pacman":
                result = subprocess.run(['pacman', '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info["pm_version"] = result.stdout.split('\n')[0].strip()
            elif self.package_manager == "dnf":
                result = subprocess.run(['dnf', '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info["pm_version"] = result.stdout.split('\n')[0].strip()
            elif self.package_manager == "brew":
                result = subprocess.run(['brew', '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info["pm_version"] = result.stdout.strip()
        except Exception as e:
            logger.debug(f"Failed to get package manager version: {e}")
        
        return info
