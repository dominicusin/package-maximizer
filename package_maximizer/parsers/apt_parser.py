"""
APT Parser - Парсер для пакетов APT (Debian/Ubuntu).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ..core.interfaces import PackageParser
from ..core.package import Package

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class APTParser(PackageParser):
    """
    Парсер для работы с пакетами APT (Debian/Ubuntu).
    
    Поддерживает разбор различных форматов вывода:
    - dpkg -l
    - apt list --installed
    - apt-cache show
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
        if "ii " in raw or "rc " in raw:
            packages.extend(self._parse_dpkg_l(raw))
        elif raw.startswith("Listing"):
            packages.extend(self._parse_apt_list(raw))
        elif "Package:" in raw:
            packages.extend(self._parse_apt_cache_show(raw))
        else:
            packages.extend(self._parse_simple_list(raw))

        return packages

    def _parse_dpkg_l(self, raw: str) -> list[Package]:
        """
        Разобрать формат dpkg -l.
        
        Пример:
        ii  vim                        2:8.2.3995-1ubuntu1 amd64        Vi IMproved
        rc  apache2                    2.4.57-1ubuntu1     amd64        Apache HTTP Server
        """
        packages = []
        lines = raw.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('-') or line.startswith('Desired'):
                continue
            
            parts = line.split()
            if len(parts) < 4:
                continue
            
            status = parts[0]
            name = parts[1]
            version = parts[2]
            
            pkg_status = self._map_dpkg_status(status)
            
            packages.append(Package(
                name=name,
                version=version,
                status=pkg_status
            ))
        
        return packages

    def _parse_apt_list(self, raw: str) -> list[Package]:
        """
        Разобрать формат apt list --installed.
        
        Пример:
        Listing... Done
        apache2/stable,stable 2.4.57-1ubuntu1 amd64 [installed]
        vim/stable 2:8.2.3995-1ubuntu1 amd64 [installed]
        """
        packages = []
        lines = raw.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Listing'):
                continue
            
            # Формат: name/suite version arch [status]
            match = re.match(r'^([^/]+)/[^/]+\s+([^\s]+)', line)
            if match:
                name = match.group(1)
                version = match.group(2)
                
                if '[installed]' in line:
                    status = "installed"
                else:
                    status = "candidate"
                
                packages.append(Package(
                    name=name,
                    version=version,
                    status=status
                ))
        
        return packages

    def _parse_apt_cache_show(self, raw: str) -> list[Package]:
        """
        Разобрать формат apt-cache show.
        
        Пример:
        Package: vim
        Version: 2:8.2.3995-1ubuntu1
        Depends: vim-runtime (= 2:8.2.3995-1ubuntu1), libc6 (>= 2.27)
        Conflicts: vim-tiny
        
        Package: apache2
        ...
        """
        packages = []
        current_pkg = None
        lines = raw.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Package:'):
                if current_pkg:
                    packages.append(current_pkg)
                current_pkg = Package(name=line.split(':', 1)[1].strip())
            elif current_pkg and line.startswith('Version:'):
                current_pkg.version = line.split(':', 1)[1].strip()
            elif current_pkg and line.startswith('Depends:'):
                depends = line.split(':', 1)[1].strip()
                deps = [d.strip().split()[0] for d in depends.split(',') if d.strip()]
                current_pkg.depends = deps
            elif current_pkg and line.startswith('Conflicts:'):
                conflicts = line.split(':', 1)[1].strip()
                conflicts_list = [c.strip().split()[0] for c in conflicts.split(',') if c.strip()]
                current_pkg.conflicts = conflicts_list
        
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

    def _map_dpkg_status(self, status: str) -> str:
        """
        Преобразовать статус dpkg в наш статус.
        
        Формат dpkg: <желаемый><текущий><ошибка>
        """
        desired = status[0] if len(status) > 0 else ''
        pkg_status = status[1] if len(status) > 1 else ''
        
        if pkg_status == 'i':
            return "installed"
        elif desired == 'i':
            return "candidate"
        elif desired == 'r' or desired == 'p':
            return "missing"
        else:
            return "candidate"
