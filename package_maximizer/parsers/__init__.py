"""Parsers module - Модуль парсеров пакетов."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .apt_parser import APTParser
    from .pacman_parser import PacmanParser
    from .dnf_parser import DNFParser
    from .brew_parser import BrewParser
    from .extra_parsers import (
        SnapParser,
        FlatpakParser,
        CargoParser,
        NpmParser,
        CondaParser,
        PortageParser,
        ApkParser,
        ZypperParser,
        YumParser,
        PipParser,
        GemParser,
        YarnParser,
        ComposerParser,
        VcpkgParser,
        NuGetParser,
        WingetParser,
        ScoopParser,
        ChocoParser,
    )

# Available parsers (names re-exported for typing convenience)
__all__ = [
    "APTParser",
    "PacmanParser",
    "DNFParser",
    "BrewParser",
    "SnapParser",
    "FlatpakParser",
    "CargoParser",
    "NpmParser",
    "CondaParser",
    "PortageParser",
    "ApkParser",
    "ZypperParser",
    "YumParser",
    "PipParser",
    "GemParser",
    "YarnParser",
    "ComposerParser",
    "VcpkgParser",
    "NuGetParser",
    "WingetParser",
    "ScoopParser",
    "ChocoParser",
    "get_parser",
    "PARSER_REGISTRY",
]

# Lazy registry: name -> (module_path, class_name, required_dependency).
_PARSER_SPECS = {
    "apt": (".apt_parser", "APTParser", None),
    "pacman": (".pacman_parser", "PacmanParser", None),
    "dnf": (".dnf_parser", "DNFParser", None),
    "brew": (".brew_parser", "BrewParser", None),
    "snap": (".extra_parsers", "SnapParser", None),
    "flatpak": (".extra_parsers", "FlatpakParser", None),
    "cargo": (".extra_parsers", "CargoParser", None),
    "npm": (".extra_parsers", "NpmParser", None),
    "conda": (".extra_parsers", "CondaParser", None),
    "portage": (".extra_parsers", "PortageParser", None),
    "apk": (".extra_parsers", "ApkParser", None),
    "zypper": (".extra_parsers", "ZypperParser", None),
    "yum": (".extra_parsers", "YumParser", None),
    "pip": (".extra_parsers", "PipParser", None),
    "gem": (".extra_parsers", "GemParser", None),
    "yarn": (".extra_parsers", "YarnParser", None),
    "composer": (".extra_parsers", "ComposerParser", None),
    "vcpkg": (".extra_parsers", "VcpkgParser", None),
    "nuget": (".extra_parsers", "NuGetParser", None),
    "winget": (".extra_parsers", "WingetParser", None),
    "scoop": (".extra_parsers", "ScoopParser", None),
    "choco": (".extra_parsers", "ChocoParser", None),
}

# Public class names importable directly (resolved lazily).
_PUBLIC_PARSER_NAMES = {
    "APTParser": (".apt_parser", "APTParser"),
    "PacmanParser": (".pacman_parser", "PacmanParser"),
    "DNFParser": (".dnf_parser", "DNFParser"),
    "BrewParser": (".brew_parser", "BrewParser"),
    "SnapParser": (".extra_parsers", "SnapParser"),
    "FlatpakParser": (".extra_parsers", "FlatpakParser"),
    "CargoParser": (".extra_parsers", "CargoParser"),
    "NpmParser": (".extra_parsers", "NpmParser"),
    "CondaParser": (".extra_parsers", "CondaParser"),
    "PortageParser": (".extra_parsers", "PortageParser"),
    "ApkParser": (".extra_parsers", "ApkParser"),
    "ZypperParser": (".extra_parsers", "ZypperParser"),
    "YumParser": (".extra_parsers", "YumParser"),
    "PipParser": (".extra_parsers", "PipParser"),
    "GemParser": (".extra_parsers", "GemParser"),
    "YarnParser": (".extra_parsers", "YarnParser"),
    "ComposerParser": (".extra_parsers", "ComposerParser"),
    "VcpkgParser": (".extra_parsers", "VcpkgParser"),
    "NuGetParser": (".extra_parsers", "NuGetParser"),
    "WingetParser": (".extra_parsers", "WingetParser"),
    "ScoopParser": (".extra_parsers", "ScoopParser"),
    "ChocoParser": (".extra_parsers", "ChocoParser"),
}


class _LazyParserRegistry(dict):
    """Dict-like view over ``_PARSER_SPECS`` (lazy import on access)."""

    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        super().__init__({name: None for name in _PARSER_SPECS})

    def __getitem__(self, name: str):  # type: ignore[override]
        if name not in _PARSER_SPECS:
            raise KeyError(name)
        cached = super().__getitem__(name)
        if cached is not None:
            return cached
        module_path, class_name, _ = _PARSER_SPECS[name]
        import importlib

        module = importlib.import_module(module_path, __name__)
        cls = getattr(module, class_name)
        super().__setitem__(name, cls)
        return cls

    def get(self, name: str, default=None):  # type: ignore[override]
        try:
            return self[name]
        except KeyError:
            return default

    def __contains__(self, name: object) -> bool:  # type: ignore[override]
        return name in _PARSER_SPECS

    def keys(self):  # type: ignore[override]
        return _PARSER_SPECS.keys()

    def items(self):  # type: ignore[override]
        return ((name, self[name]) for name in _PARSER_SPECS)

    def values(self):  # type: ignore[override]
        return (self[name] for name in _PARSER_SPECS)

    def __iter__(self):  # type: ignore[override]
        return iter(_PARSER_SPECS)


PARSER_REGISTRY = _LazyParserRegistry()


def get_parser(parser_name: str):
    """
    Получение экземпляра парсера по имени.

    Args:
        parser_name: Имя парсера (регистронезависимое)

    Returns:
        Экземпляр парсера

    Raises:
        ValueError: Если парсер не найден
    """
    parser_name = parser_name.lower()
    if parser_name not in PARSER_REGISTRY:
        available = ", ".join(PARSER_REGISTRY.keys())
        raise ValueError(f"Parser '{parser_name}' not found. Available: {available}")
    return PARSER_REGISTRY[parser_name]()


def __getattr__(name: str):  # module-level lazy attribute resolution
    spec = _PUBLIC_PARSER_NAMES.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, class_name = spec
    import importlib

    module = importlib.import_module(module_path, __name__)
    return getattr(module, class_name)
