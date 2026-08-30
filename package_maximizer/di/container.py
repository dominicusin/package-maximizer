"""
Dependency Injection Container for Package Maximizer.

Provides a lightweight DI container for managing dependencies,
service registration, and lifecycle management.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, TypeVar, Generic

T = TypeVar('T')


class Container:
    """
    Simple dependency injection container.
    
    Supports:
    - Singleton and transient lifetimes
    - Factory functions
    - Manual registrations
    - Auto-resolution of type hints
    """
    
    def __init__(self) -> None:
        self._singletons: dict[type, Any] = {}
        self._factories: dict[type, Callable[[], Any]] = {}
        self._registrations: dict[type, Callable[[], Any]] = {}
    
    def register(self, lifecycle: str = "singleton") -> Callable[[type], type]:
        """Class decorator to register a service."""
        def decorator(cls: type) -> type:
            if lifecycle == "singleton":
                self._singletons[cls] = None  # type: ignore
            else:
                self._factories[cls] = lambda c=cls: c()
            return cls
        return decorator
    
    def register_instance(self, service_type: type, instance: Any) -> None:
        """Register a pre-created instance."""
        self._singletons[service_type] = instance
    
    def register_factory(self, service_type: type, factory: Callable[[], Any]) -> None:
        """Register a factory function."""
        self._factories[service_type] = factory
    
    def _resolve_constructor(self, cls: type) -> list[Any]:
        """Resolve constructor dependencies via type hints."""
        sig = inspect.signature(cls.__init__)
        deps = []
        
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            
            # Check if it's a type hint
            if param.annotation != inspect.Parameter.empty:
                hint = param.annotation
                # Handle typing generics
                origin = getattr(hint, '__origin__', None)
                if origin is not None:
                    hint = origin
                
                if hint in self._singletons and self._singletons[hint] is not None:
                    deps.append(self._singletons[hint])
                elif hint in self._factories:
                    deps.append(self._factories[hint]())
                else:
                    # Try to construct directly
                    deps.append(self.resolve(hint))
            elif param.default is not inspect.Parameter.empty:
                deps.append(param.default)
            else:
                raise ValueError(f"Cannot resolve parameter '{name}' for {cls.__name__}")
        
        return deps
    
    def resolve(self, service_type: type) -> Any:
        """Resolve a service instance."""
        # Check singletons first
        if service_type in self._singletons:
            if self._singletons[service_type] is None:
                deps = self._resolve_constructor(service_type)
                self._singletons[service_type] = service_type(*deps)
            return self._singletons[service_type]
        
        # Check factories
        if service_type in self._factories:
            return self._factories[service_type]()
        
        # Auto-resolve via constructor
        deps = self._resolve_constructor(service_type)
        return service_type(*deps)
    
    def get(self, service_type: type) -> Any:
        """Alias for resolve()."""
        return self.resolve(service_type)


class ServiceLocator:
    """
    Global service locator for the application.
    
    Use for accessing shared services across the codebase.
    """
    
    _instance: Container | None = None
    
    @classmethod
    def container(cls) -> Container:
        """Get or create the global container."""
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance
    
    @classmethod
    def register(cls, *args: Any) -> None:
        """Register services with the global container."""
        cls.container().register(*args)
    
    @classmethod
    def resolve(cls, service_type: type) -> Any:
        """Resolve a service from the global container."""
        return cls.container().resolve(service_type)
    
    @classmethod
    def reset(cls) -> None:
        """Reset the container (useful for testing)."""
        cls._instance = None


def inject(dep_type: type) -> Callable[[T], T]:
    """
    Decorator to inject a dependency into a method or property.
    
    Usage:
        class MyService:
            @inject(Clock)
            def clock(self) -> Clock:
                return ServiceLocator.resolve(Clock)
    """
    def decorator(target: T) -> T:
        setattr(target, '_injected_deps', 
                getattr(target, '_injected_deps', {}) | {target.__name__: dep_type})
        return target
    return decorator