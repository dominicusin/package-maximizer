"""E2E tests for metadata adapters with real-world fixtures."""

from __future__ import annotations

import pytest

from package_maximizer.adapters import (
    APTMetadataAdapter,
    PipMetadataAdapter,
    PacmanMetadataAdapter,
    PackageMetadata,
)


# ─── Fixtures ───────────────────────────────────────────────────────────

# Реальный вывод apt-cache show nginx (Ubuntu 22.04)
APT_CACHE_SHOW_NGINX = """Package: nginx
Priority: optional
Section: httpd
Installed-Size: 48
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Debian Nginx Maintainers <pkg-nginx-maintainers@alioth-lists.debian.net>
Architecture: amd64
Version: 1.18.0-6ubuntu14.4
Provides: httpd, httpd-cgi
Depends: nginx-core (<< 1.18.0-6ubuntu14.4.1~) | nginx-full (<< 1.18.0-6ubuntu14.4.1~) | nginx-light (<< 1.18.0-6ubuntu14.4.1~) | nginx-extras (<< 1.18.0-6ubuntu14.4.1~), nginx-core (>= 1.18.0-6ubuntu14.4) | nginx-full (>= 1.18.0-6ubuntu14.4) | nginx-light (>= 1.18.0-6ubuntu14.4) | nginx-extras (>= 1.18.0-6ubuntu14.4)
Pre-Depends: dpkg (>= 1.17.14)
Conflicts: nginx-common
Replaces: nginx-common (<< 1.18.0-6ubuntu14.4)
Homepage: http://nginx.net
Description: small, powerful, scalable web/proxy server
Description-md5: 05bbe750b2fa32f7b2f8d1a1b5b5b5b5
"""

# Реальный вывод apt-cache show apache2
APT_CACHE_SHOW_APACHE2 = """Package: apache2
Priority: optional
Section: httpd
Installed-Size: 512
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Architecture: amd64
Version: 2.4.54-1ubuntu1
Depends: (= 2.4.54-1ubuntu1), apache2-bin (= 2.4.54-1ubuntu1), apache2-utils (= 2.4.54-1ubuntu1), apache2-data
Recommends: ssl-cert
Suggests: apache2-doc, apache2-suexec-pristine | apache2-suexec-custom, www-browser, ufw
Conflicts: apache2.2-bin, apache2.2-common
Provides: httpd, httpd-cgi
Homepage: http://httpd.apache.org/
Description: Apache HTTP Server
Description-md5: 05bbe750b2fa32f7b2f8d1a1b5b5b5b5
"""

# Реальный вывод pip show requests
PIP_SHOW_REQUESTS = """Name: requests
Version: 2.31.0
Summary: Python HTTP for Humans.
Home-page: https://requests.readthedocs.io
Author: Kenneth Reitz
Author-email: me@kennethreitz.org
License: Apache 2.0
Location: /usr/lib/python3/dist-packages
Requires: certifi, charset-normalizer, idna, urllib3
Required-by: some-package
"""

# Реальный вывод pip show certifi
PIP_SHOW_CERTIFI = """Name: certifi
Version: 2023.7.22
Summary: Python package for providing CA certificates.
Home-page: https://github.com/certifi/python-certifi
Author: Kenneth Reitz
License: MPL-2.0
Location: /usr/lib/python3/dist-packages
Requires: 
Required-by: requests
"""

# Реальный вывод pacman -Si vim
PACMAN_SI_VIM = """Repository      : core
Name            : vim
Version         : 9.0.1420-1
Description     : Vi Improved, a highly configurable, improved version of the vi editor
Architecture    : x86_64
URL             : https://www.vim.org
License         : custom
Groups          : None
Depends On      : vim-runtime  gawk
Optional Deps   : python: vim bindings [installed]
                  lua: vim bindings
                  perl: vim bindings
                  ruby: vim bindings
                  tcl: vim bindings
Conflicts With  : gvim  vim-minimal
Provides        : vim-python3
Replaces        : None
Download Size   : 3.50 MiB
Installed Size  : 16.00 MiB
Packager        : Levente Polyak <dev@leventepolyak.net>
Build Date      : Mon 10 Jul 2023 12:00:00 PM UTC
Validated By    : SHA-256 Sum  Signature
"""


# ─── Tests ─────────────────────────────────────────────────────────────

class TestAPTMetadataAdapter:
    """Тесты парсера метаданных APT."""

    def test_parse_nginx(self):
        adapter = APTMetadataAdapter()
        pkg = adapter.parse(APT_CACHE_SHOW_NGINX)

        assert pkg is not None
        assert pkg.name == "nginx"
        assert pkg.version == "1.18.0-6ubuntu14.4"
        assert "nginx-core" in pkg.depends
        assert "nginx-common" in pkg.conflicts
        assert pkg.homepage == "http://nginx.net"

    def test_parse_apache2(self):
        adapter = APTMetadataAdapter()
        pkg = adapter.parse(APT_CACHE_SHOW_APACHE2)

        assert pkg is not None
        assert pkg.name == "apache2"
        assert pkg.version == "2.4.54-1ubuntu1"
        assert "apache2-bin" in pkg.depends
        assert "apache2.2-bin" in pkg.conflicts

    def test_parse_multi(self):
        adapter = APTMetadataAdapter()
        raw = APT_CACHE_SHOW_NGINX + "\n\n" + APT_CACHE_SHOW_APACHE2
        pkgs = adapter.parse_multi(raw)

        assert len(pkgs) == 2
        names = {p.name for p in pkgs}
        assert names == {"nginx", "apache2"}

    def test_parse_empty(self):
        adapter = APTMetadataAdapter()
        assert adapter.parse("") is None
        assert adapter.parse("   ") is None

    def test_to_package(self):
        adapter = APTMetadataAdapter()
        pkg = adapter.parse(APT_CACHE_SHOW_NGINX)
        assert pkg is not None

        package = pkg.to_package()
        assert package.name == "nginx"
        assert "nginx-core" in package.depends
        assert "nginx-common" in package.conflicts


class TestPipMetadataAdapter:
    """Тесты парсера метаданных pip."""

    def test_parse_requests(self):
        adapter = PipMetadataAdapter()
        pkg = adapter.parse(PIP_SHOW_REQUESTS)

        assert pkg is not None
        assert pkg.name == "requests"
        assert pkg.version == "2.31.0"
        assert "certifi" in pkg.depends
        assert "urllib3" in pkg.depends
        assert pkg.homepage == "https://requests.readthedocs.io"

    def test_parse_certifi(self):
        adapter = PipMetadataAdapter()
        pkg = adapter.parse(PIP_SHOW_CERTIFI)

        assert pkg is not None
        assert pkg.name == "certifi"
        assert pkg.version == "2023.7.22"
        assert pkg.depends == []  # certifi не имеет зависимостей

    def test_parse_empty(self):
        adapter = PipMetadataAdapter()
        assert adapter.parse("") is None

    def test_to_package(self):
        adapter = PipMetadataAdapter()
        pkg = adapter.parse(PIP_SHOW_REQUESTS)
        assert pkg is not None

        package = pkg.to_package()
        assert package.name == "requests"
        assert "certifi" in package.depends


class TestPacmanMetadataAdapter:
    """Тесты парсера метаданных pacman."""

    def test_parse_vim(self):
        adapter = PacmanMetadataAdapter()
        pkg = adapter.parse(PACMAN_SI_VIM)

        assert pkg is not None
        assert pkg.name == "vim"
        assert pkg.version == "9.0.1420-1"
        assert "vim-runtime" in pkg.depends
        assert "gawk" in pkg.depends
        assert "gvim" in pkg.conflicts

    def test_parse_empty(self):
        adapter = PacmanMetadataAdapter()
        assert adapter.parse("") is None


class TestAdapterIntegration:
    """Интеграционные тесты: адаптеры + солверы."""

    def test_apt_deps_in_solver(self):
        """APT-метаданные → Package → солвер учитывает зависимости."""
        from package_maximizer.solvers.greedy import GreedySolver

        adapter = APTMetadataAdapter()
        nginx_meta = adapter.parse(APT_CACHE_SHOW_NGINX)
        apache2_meta = adapter.parse(APT_CACHE_SHOW_APACHE2)

        assert nginx_meta is not None
        assert apache2_meta is not None

        # Создаём пакеты с зависимостями
        packages = [
            nginx_meta.to_package(),
            apache2_meta.to_package(),
            # Добавляем зависимости как отдельные пакеты
            PackageMetadata(name="nginx-core", version="1.18.0").to_package(),
            PackageMetadata(name="nginx-common", version="1.18.0").to_package(),
            PackageMetadata(name="apache2-bin", version="2.4.54").to_package(),
        ]

        result = GreedySolver().solve(packages)

        # nginx конфликтует с nginx-common (из фикстуры)
        assert not ("nginx" in result and "nginx-common" in result)

        # apache2 конфликтует с apache2.2-bin и apache2.2-common
        # (если они есть в списке)
        if "apache2" in result:
            assert "apache2.2-bin" not in result
            assert "apache2.2-common" not in result

        # Если выбран nginx, должна быть выбрана nginx-core
        if "nginx" in result:
            assert "nginx-core" in result

    def test_pip_deps_in_solver(self):
        """pip-метаданные → Package → солвер учитывает зависимости."""
        from package_maximizer.solvers.greedy import GreedySolver

        adapter = PipMetadataAdapter()
        requests_meta = adapter.parse(PIP_SHOW_REQUESTS)
        certifi_meta = adapter.parse(PIP_SHOW_CERTIFI)

        assert requests_meta is not None
        assert certifi_meta is not None

        packages = [
            requests_meta.to_package(),
            certifi_meta.to_package(),
            PackageMetadata(name="urllib3", version="2.0.0").to_package(),
            PackageMetadata(name="charset-normalizer", version="3.0.0").to_package(),
            PackageMetadata(name="idna", version="3.0.0").to_package(),
        ]

        result = GreedySolver().solve(packages)

        # Если выбран requests, должны быть выбраны зависимости
        if "requests" in result:
            assert "certifi" in result
            assert "urllib3" in result
