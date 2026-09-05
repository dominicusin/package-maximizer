"""Golden tests — проверка зависимостей на фикстурах реальных пакетов."""

from __future__ import annotations

import pytest

from package_maximizer.core.model_encoder import ModelConstraints, encode_packages
from package_maximizer.core.package import Package
from package_maximizer.solvers.enhanced_greedy import EnhancedGreedySolver
from package_maximizer.solvers.greedy import GreedySolver


class TestModelEncoder:
    """Тесты кодирования ограничений из Package."""

    def test_no_deps_no_conflicts(self):
        pkgs = [
            Package(name="vim"),
            Package(name="nano"),
        ]
        c = encode_packages(pkgs)
        assert c.packages == ["vim", "nano"]
        assert c.conflicts == []
        assert c.dependencies == {}

    def test_simple_dependency(self):
        pkgs = [
            Package(name="nginx", depends=["libnginx"]),
            Package(name="libnginx"),
        ]
        c = encode_packages(pkgs)
        assert c.dependencies == {"nginx": ["libnginx"]}
        assert c.conflicts == []

    def test_simple_conflict(self):
        pkgs = [
            Package(name="nginx", conflicts=["apache2"]),
            Package(name="apache2"),
        ]
        c = encode_packages(pkgs)
        assert c.conflicts == [("apache2", "nginx")]
        assert c.dependencies == {}

    def test_bidirectional_conflict_normalized(self):
        """Конфликты нормализуются в один порядок."""
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
        ]
        c = encode_packages(pkgs)
        assert len(c.conflicts) == 1
        assert c.conflicts[0] == ("a", "b")

    def test_multiple_deps(self):
        pkgs = [
            Package(name="webapp", depends=["python3", "nginx", "libpq"]),
            Package(name="python3"),
            Package(name="nginx"),
            Package(name="libpq"),
        ]
        c = encode_packages(pkgs)
        assert c.dependencies == {"webapp": ["python3", "nginx", "libpq"]}

    def test_dep_on_unknown_ignored(self):
        """Зависимость от неизвестного пакета игнорируется."""
        pkgs = [
            Package(name="nginx", depends=["unknown-pkg"]),
        ]
        c = encode_packages(pkgs)
        assert c.dependencies == {}


class TestGreedyWithDependencies:
    """Greedy solver: проверка зависимостей."""

    def test_dependency_auto_included(self):
        """Если выбран pkg с depends=[dep], dep должен быть выбран."""
        pkgs = [
            Package(name="nginx", depends=["libnginx"]),
            Package(name="libnginx"),
            Package(name="vim"),
        ]
        result = GreedySolver().solve(pkgs)
        if "nginx" in result:
            assert "libnginx" in result

    def test_conflict_prevents_selection(self):
        """Конфликтующие пакеты не могут быть выбраны вместе."""
        pkgs = [
            Package(name="nginx", conflicts=["apache2"]),
            Package(name="apache2"),
        ]
        result = GreedySolver().solve(pkgs)
        assert not ("nginx" in result and "apache2" in result)

    def test_chain_dependencies(self):
        """Цепочка зависимостей: a -> b -> c."""
        pkgs = [
            Package(name="a", depends=["b"]),
            Package(name="b", depends=["c"]),
            Package(name="c"),
        ]
        result = GreedySolver().solve(pkgs)
        if "a" in result:
            assert "b" in result
            assert "c" in result

    def test_real_world_scenario_nginx_apache(self):
        """Реалистичный сценарий: nginx vs apache + общие зависимости."""
        pkgs = [
            Package(name="nginx", depends=["libnginx", "libc"], conflicts=["apache2"]),
            Package(name="apache2", depends=["libapache", "libc"], conflicts=["nginx"]),
            Package(name="libnginx"),
            Package(name="libapache"),
            Package(name="libc"),
        ]
        result = GreedySolver().solve(pkgs)
        # Конфликт nginx/apache2 не должен быть выбран вместе
        assert not ("nginx" in result and "apache2" in result)
        # Если выбран nginx, должны быть выбраны его зависимости
        if "nginx" in result:
            assert "libnginx" in result
            assert "libc" in result


class TestGoldenFixtures:
    """Golden-тесты на фикстурах."""

    def test_apt_like_system(self):
        """Система с несколькими пакетами и зависимостями."""
        pkgs = [
            Package(name="postgresql", depends=["libpq", "libc"]),
            Package(name="libpq"),
            Package(name="libc"),
            Package(name="vim", depends=["libc"]),
            Package(name="nginx", depends=["libnginx", "libc"], conflicts=["apache2"]),
            Package(name="libnginx"),
            Package(name="apache2", depends=["libapache", "libc"], conflicts=["nginx"]),
            Package(name="libapache"),
        ]
        c = encode_packages(pkgs)
        assert len(c.packages) == 8
        assert ("apache2", "nginx") in c.conflicts
        assert c.dependencies["postgresql"] == ["libpq", "libc"]
        assert c.dependencies["vim"] == ["libc"]

    def test_pip_like_chain(self):
        """pip-подобная цепочка зависимостей."""
        pkgs = [
            Package(name="requests", depends=["urllib3", "certifi"]),
            Package(name="urllib3"),
            Package(name="certifi"),
        ]
        result = GreedySolver().solve(pkgs)
        # requests зависит от urllib3 и certifi
        if "requests" in result:
            assert "urllib3" in result
            assert "certifi" in result
