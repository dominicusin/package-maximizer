"""
Brew Parser - Парсер для пакетов Homebrew (macOS).
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


class BrewParser(PackageParser):
    """
    Парсер для работы с пакетами Homebrew (macOS).
    
    Поддерживает разбор различных форматов вывода:
    - brew list
    - brew info
    - brew search
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
        if raw.startswith("==> Formulae"):
            packages.extend(self._parse_brew_list(raw))
        elif "From:" in raw or "Version:" in raw:
            packages.extend(self._parse_brew_info(raw))
        else:
            packages.extend(self._parse_simple_list(raw))

        return packages

    def _parse_brew_list(self, raw: str) -> list[Package]:
        """
        Разобрать формат brew list.
        
        Пример:
        ==> Formulae
        vim
        wget
        python@3.11
        
        ==> Casks
        firefox
        google-chrome
        """
        packages = []
        lines = raw.strip().split('\n')
        
        in_formulae = False
        in_casks = False
        
        for line in lines:
            line = line.strip()
            
            if line == "==> Formulae":
                in_formulae = True
                in_casks = False
                continue
            elif line == "==> Casks":
                in_formulae = False
                in_casks = True
                continue
            
            if in_formulae or in_casks:
                if line:
                    packages.append(Package(
                        name=line,
                        status="installed"
                    ))
        
        return packages

    def _parse_brew_info(self, raw: str) -> list[Package]:
        """
        Разобрать формат brew info.
        
        Пример:
        vim:
        Stable version: 9.1.0000
        From: https://github.com/vim/vim
        Dependencies: python@3.11, ncurses
        Conflicts with: vim-tiny
        """
        packages = []
        current_pkg = None
        lines = raw.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Проверяем, начинается ли строка с имени пакета (с двоеточием)
            if line.endswith(':') and not line.startswith(' '):
                if current_pkg:
                    packages.append(current_pkg)
                current_pkg = Package(name=line[:-1])  # Убираем двоеточие
            elif current_pkg and line.startswith('Stable version:'):
                version = line.split(':', 1)[1].strip()
                current_pkg.version = version
            elif current_pkg and line.startswith('From:'):
                # URL производителя
                pass
            elif current_pkg and line.startswith('Dependencies:'):
                depends = line.split(':', 1)[1].strip()
                deps = [d.strip() for d in depends.split(',') if d.strip()]
                current_pkg.depends = deps
            elif current_pkg and line.startswith('Conflicts with:'):
                conflicts = line.split(':', 1)[1].strip()
                conflicts_list = [c.strip() for c in conflicts.split(',') if c.strip()]
                current_pkg.conflicts = conflicts_list
            elif current_pkg and line.startswith('Installed:'):
                if 'YES' in line.upper():
                    current_pkg.status = "installed"
        
        if current_pkg:
            packages.append(current_pkg)
        
        return packages

    def _parse_simple_list(self, raw: str) -> list[Package]:
        """
        Разобрать простой список имен пакетов.
        """
        packages = []
        lines = raw.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line:
                packages.append(Package(name=line, status="candidate"))
        
        return packages

    def parse_from_system(self, package_names: list[str] | None = None) -> list[Package]:
        """
        Разобрать пакеты напрямую из системы.
        
        Args:
            package_names: Список имен пакетов для запроса (если None - все установленные)

        Returns:
            Список объектов Package
        """
        if package_names is None:
            return self._get_all_installed()
        else:
            return self._get_package_info(package_names)

    def _get_all_installed(self) -> list[Package]:
        """
        Получить все установленные пакеты.
        """
        try:
            result = subprocess.run(
                ['brew', 'list', '--formula', '--cask'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return self._parse_brew_list(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
            logger.warning(f"Failed to get installed packages: {e}")
        
        return []

    def _get_package_info(self, package_names: list[str]) -> list[Package]:
        """
        Получить информацию о конкретных пакетах.
        """
        packages = []
        
        for name in package_names:
            try:
                result = subprocess.run(
                    ['brew', 'info', name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    parsed = self._parse_brew_info(result.stdout)
                    if parsed:
                        packages.extend(parsed)
                    else:
                        packages.append(Package(name=name, status="candidate"))
                else:
                    packages.append(Package(name=name, status="candidate"))
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.warning(f"Failed to get info for package {name}: {e}")
                packages.append(Package(name=name, status="candidate"))
        
        return packages
