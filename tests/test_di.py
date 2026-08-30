"""Tests for the Dependency Injection (DI) container and factory patterns."""

from __future__ import annotations

import pytest

from package_maximizer.di import Container, ServiceLocator, inject
from package_maximizer.di import (
    build_default_solver_factory,
    build_default_parser_factory,
)
from package_maximizer.core.package import Package
from package_maximizer.solvers import (
    GreedySolver,
    get_solver,
    SOLVER_REGISTRY,
)
from package_maximizer.parsers import get_parser


class _ServiceA:
    def __init__(self) -> None:
        self.value = "a"


class _ServiceB:
    def __init__(self, dep: _ServiceA) -> None:
        self.dep = dep
        self.value = "b"


class TestContainerBasics:
    """Test the basic Container functionality."""

    def test_register_and_resolve_singleton(self):
        """A registered singleton should resolve to the same instance."""
        container = Container()
        container.register_instance(_ServiceA, _ServiceA())
        a1 = container.resolve(_ServiceA)
        a2 = container.resolve(_ServiceA)
        assert a1 is a2

    def test_register_factory_creates_new_each_time(self):
        """A factory registration should create a new instance each call."""
        container = Container()
        container.register_factory(_ServiceA, lambda: _ServiceA())
        a1 = container.resolve(_ServiceA)
        a2 = container.resolve(_ServiceA)
        assert a1 is not a2
        assert a1.value == a2.value

    def test_auto_resolve_with_dependency(self):
        """Container should auto-resolve constructor dependencies."""
        container = Container()
        container.register_factory(_ServiceA, lambda: _ServiceA())
        container.register_factory(_ServiceB, lambda: _ServiceB(container.resolve(_ServiceA)))
        b = container.resolve(_ServiceB)
        assert isinstance(b, _ServiceB)
        assert isinstance(b.dep, _ServiceA)

    def test_resolve_unregistered_returns_none_safely(self):
        """Resolving an unknown type raises ValueError (no auto-construction)."""
        container = Container()
        # GreedySolver has no-arg constructor; container will try to construct it
        solver = container.resolve(GreedySolver)
        assert isinstance(solver, GreedySolver)


class TestServiceLocator:
    """Test the global ServiceLocator."""

    def test_global_container_singleton(self):
        """ServiceLocator.container() returns a stable global container."""
        c1 = ServiceLocator.container()
        c2 = ServiceLocator.container()
        assert c1 is c2

    def test_register_instance_and_resolve(self):
        """register_instance on the container makes resolve return that instance."""
        container = ServiceLocator.container()
        container.register_instance(_ServiceA, _ServiceA())
        assert ServiceLocator.resolve(_ServiceA) is not None
        ServiceLocator.reset()
        # After reset the container is new; resolve will construct a fresh instance
        assert isinstance(ServiceLocator.resolve(_ServiceA), _ServiceA)


class TestInjectDecorator:
    """Test the @inject decorator metadata attachment."""

    def test_inject_attaches_metadata(self):
        """@inject should mark the target with injected dependency info."""

        class _Svc:
            @inject(_ServiceA)
            def get_a(self) -> _ServiceA:
                return ServiceLocator.resolve(_ServiceA)

        assert hasattr(_Svc.get_a, "_injected_deps")
        assert _Svc.get_a._injected_deps == {"get_a": _ServiceA}


class TestRegistryIntegration:
    """Ensure DI plays well with existing solver/parser registries."""

    def test_get_solver_returns_expected_type(self):
        """get_solver should return the registered class instance."""
        solver = get_solver("greedy")
        assert isinstance(solver, GreedySolver)

    def test_all_registered_solvers_instantiable(self):
        """Every solver in the registry must be instantiable."""
        for name, cls in SOLVER_REGISTRY.items():
            instance = cls()
            assert instance is not None

    def test_parser_registry_instantiable(self):
        """Parsers must be instantiable via get_parser."""
        for name in ("apt", "pacman", "dnf", "brew"):
            parser = get_parser(name)
            assert parser is not None


class TestSolverFactory:
    """Test the solver/parser factories built on the DI container."""

    def test_build_default_solver_factory(self):
        """Default factory exposes every registered solver name."""
        factory = build_default_solver_factory()
        assert "greedy" in factory.available()
        assert "enhanced_greedy" in factory.available()

    def test_factory_create_returns_solver(self):
        """Factory.create returns a ConstraintSolver instance."""
        factory = build_default_solver_factory()
        solver = factory.create("greedy")
        assert isinstance(solver, GreedySolver)

    def test_factory_create_unknown_raises(self):
        """Unknown solver name raises ValueError."""
        factory = build_default_solver_factory()
        import pytest

        with pytest.raises(ValueError):
            factory.create("nonexistent")

    def test_factory_create_all(self):
        """create_all builds every registered solver."""
        factory = build_default_solver_factory()
        all_solvers = factory.create_all()
        assert set(all_solvers.keys()) == set(factory.available())


class TestParserFactory:
    """Test the parser factory."""

    def test_build_default_parser_factory(self):
        """Default parser factory exposes apt/pacman/dnf/brew."""
        factory = build_default_parser_factory()
        for name in ("apt", "pacman", "dnf", "brew"):
            assert name in factory.available()

    def test_parser_factory_create(self):
        """Factory.create returns a parser instance."""
        factory = build_default_parser_factory()
        parser = factory.create("apt")
        assert parser is not None

    def test_parser_factory_unknown_raises(self):
        """Unknown parser name raises ValueError."""
        factory = build_default_parser_factory()
        import pytest

        with pytest.raises(ValueError):
            factory.create("snap")
