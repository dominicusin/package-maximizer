"""
Tests for di.container — Dependency Injection Container.
"""

from __future__ import annotations

import pytest

from package_maximizer.di.container import Container, ServiceLocator, inject


class TestContainerInit:
    """Container initialization."""

    def test_init_creates_empty_registries(self):
        c = Container()
        assert len(c._singletons) == 0
        assert len(c._factories) == 0
        assert len(c._registrations) == 0


class TestContainerRegister:
    """Container.register decorator with singleton and transient."""

    def test_register_singleton(self):
        c = Container()

        @c.register(lifecycle="singleton")
        class MyService:
            pass

        assert MyService in c._singletons
        assert c._singletons[MyService] is None

    def test_register_transient(self):
        c = Container()

        @c.register(lifecycle="transient")
        class MyService:
            pass

        assert MyService in c._factories


class TestContainerRegisterInstance:
    """Container.register_instance."""

    def test_register_instance(self):
        c = Container()
        instance = object()
        c.register_instance(str, instance)
        assert c._singletons[str] is instance


class TestContainerRegisterFactory:
    """Container.register_factory."""

    def test_register_factory(self):
        c = Container()
        factory = lambda: "test"
        c.register_factory(str, factory)
        assert c._factories[str] is factory


class TestResolveConstructor:
    """_resolve_constructor with various parameter types."""

    def test_no_params(self):
        c = Container()

        class NoDeps:
            def __init__(self):
                pass

        deps = c._resolve_constructor(NoDeps)
        assert deps == []

    def test_param_with_default(self):
        c = Container()

        class WithDefault:
            def __init__(self, x: int = 42):
                self.x = x

        deps = c._resolve_constructor(WithDefault)
        assert deps == [42]

    def test_string_annotation_with_default(self):
        c = Container()

        class StringAnn:
            def __init__(self, x: "int" = 10):
                self.x = x

        deps = c._resolve_constructor(StringAnn)
        assert deps == [10]

    def test_type_not_registered_with_default(self):
        c = Container()

        class Unregistered:
            def __init__(self, x: int = 5):
                self.x = x

        deps = c._resolve_constructor(Unregistered)
        assert deps == [5]

    def test_type_not_registered_no_default(self):
        c = Container()

        class UnregisteredNoDefault:
            def __init__(self, x: int):
                self.x = x

        with pytest.raises(ValueError):
            c._resolve_constructor(UnregisteredNoDefault)

    def test_no_annotation_no_default(self):
        c = Container()

        class NoAnnNoDefault:
            def __init__(self, x):
                self.x = x

        with pytest.raises(ValueError):
            c._resolve_constructor(NoAnnNoDefault)


class TestResolve:
    """Container.resolve for singletons, factories, and auto-resolution."""

    def test_resolve_singleton(self):
        c = Container()
        instance = object()
        c.register_instance(str, instance)
        result = c.resolve(str)
        assert result is instance

    def test_resolve_singleton_lazy_init(self):
        c = Container()

        class LazyService:
            def __init__(self):
                self.value = "lazy"

        c.register()(LazyService)
        result = c.resolve(LazyService)
        assert isinstance(result, LazyService)
        assert result.value == "lazy"

    def test_resolve_factory(self):
        c = Container()
        factory = lambda: "factory_result"
        c.register_factory(str, factory)
        result = c.resolve(str)
        assert result == "factory_result"

    def test_resolve_auto_resolve(self):
        c = Container()

        class Simple:
            def __init__(self):
                self.value = "auto"

        result = c.resolve(Simple)
        assert isinstance(result, Simple)
        assert result.value == "auto"

    def test_get_alias(self):
        c = Container()
        instance = object()
        c.register_instance(str, instance)
        assert c.get(str) is instance


class TestServiceLocator:
    """ServiceLocator global container."""

    def test_container_creates_on_first_access(self):
        ServiceLocator.reset()
        container = ServiceLocator.container()
        assert isinstance(container, Container)

    def test_container_singleton(self):
        ServiceLocator.reset()
        c1 = ServiceLocator.container()
        c2 = ServiceLocator.container()
        assert c1 is c2

    def test_register(self):
        ServiceLocator.reset()

        class TestService:
            def __init__(self):
                pass

        # register takes *args, so pass lifecycle string
        ServiceLocator.container().register("singleton")(TestService)
        assert TestService in ServiceLocator.container()._singletons

    def test_resolve(self):
        ServiceLocator.reset()
        instance = object()
        ServiceLocator.container().register_instance(str, instance)
        result = ServiceLocator.resolve(str)
        assert result is instance

    def test_reset(self):
        ServiceLocator.reset()
        c1 = ServiceLocator.container()
        ServiceLocator.reset()
        c2 = ServiceLocator.container()
        assert c1 is not c2


class TestInject:
    """inject decorator."""

    def test_inject_sets_deps(self):
        @inject(str)
        def my_func():
            return "test"

        assert hasattr(my_func, "_injected_deps")
        assert str in my_func._injected_deps.values()

    def test_inject_stacked_decorators(self):
        """Stacked injects: outermost wins (same key 'my_func')."""
        @inject(int)
        @inject(str)
        def my_func():
            return "test"

        # Outer inject(int) overwrites inner inject(str) since same key
        assert int in my_func._injected_deps.values()
