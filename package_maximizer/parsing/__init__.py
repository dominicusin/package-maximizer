"""`parsing` module — парсеры пакетных менеджеров и загрузчики манифестов.

Модули:

* Парсеры вывода пакетных менеджеров (APT, Pacman, DNF, Homebrew, snap,
  Flatpak, Cargo, npm, pip, gem, yarn, Composer, NuGet, WinGet и др.) — через
  ``get_parser`` / ``PARSER_REGISTRY``.
* :class:`ManifestLoader` — чтение манифестов пакетов в форматах JSON, YAML
  и CSV (локальные файлы).
* :class:`RemoteManifestSource` — загрузка манифестов по HTTP(S) через
  ``requests`` (REST-инвентаризация репозиториев).

Пример::

    from package_maximizer.parsing import (
        get_parser, ManifestLoader, RemoteManifestSource,
    )

    # локальный манифест
    loader = ManifestLoader.from_paths(["manifest.yaml", "packages.json"])
    pkgs = loader.parse()

    # удалённая инвентаризация
    remote = RemoteManifestSource("https://repo.example.org/api/packages")
    pkgs = remote.fetch()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .apt_parser import APTParser
    from .brew_parser import BrewParser
    from .dnf_parser import DNFParser
    from .extra_parsers import (
        ApkParser,
        CargoParser,
        ChocoParser,
        ComposerParser,
        CondaParser,
        FlatpakParser,
        GemParser,
        GuixParser,
        NixParser,
        NpmParser,
        NuGetParser,
        PipParser,
        PortageParser,
        ScoopParser,
        SnapParser,
        SpackParser,
        VcpkgParser,
        WingetParser,
        YarnParser,
        YumParser,
        ZypperParser,
    )
    from .pacman_parser import PacmanParser

# Public class names importable directly (resolved lazily).
_PUBLIC_PARSER_NAMES = {
    "APTParser": ("package_maximizer.parsers.apt_parser", "APTParser"),
    "PacmanParser": ("package_maximizer.parsers.pacman_parser", "PacmanParser"),
    "DNFParser": ("package_maximizer.parsers.dnf_parser", "DNFParser"),
    "BrewParser": ("package_maximizer.parsers.brew_parser", "BrewParser"),
    "SnapParser": ("package_maximizer.parsers.extra_parsers", "SnapParser"),
    "FlatpakParser": ("package_maximizer.parsers.extra_parsers", "FlatpakParser"),
    "CargoParser": ("package_maximizer.parsers.extra_parsers", "CargoParser"),
    "NpmParser": ("package_maximizer.parsers.extra_parsers", "NpmParser"),
    "CondaParser": ("package_maximizer.parsers.extra_parsers", "CondaParser"),
    "PortageParser": ("package_maximizer.parsers.extra_parsers", "PortageParser"),
    "ApkParser": ("package_maximizer.parsers.extra_parsers", "ApkParser"),
    "ZypperParser": ("package_maximizer.parsers.extra_parsers", "ZypperParser"),
    "YumParser": ("package_maximizer.parsers.extra_parsers", "YumParser"),
    "PipParser": ("package_maximizer.parsers.extra_parsers", "PipParser"),
    "GemParser": ("package_maximizer.parsers.extra_parsers", "GemParser"),
    "YarnParser": ("package_maximizer.parsers.extra_parsers", "YarnParser"),
    "ComposerParser": ("package_maximizer.parsers.extra_parsers", "ComposerParser"),
    "VcpkgParser": ("package_maximizer.parsers.extra_parsers", "VcpkgParser"),
    "NuGetParser": ("package_maximizer.parsers.extra_parsers", "NuGetParser"),
    "WingetParser": ("package_maximizer.parsers.extra_parsers", "WingetParser"),
    "ScoopParser": ("package_maximizer.parsers.extra_parsers", "ScoopParser"),
    "ChocoParser": ("package_maximizer.parsers.extra_parsers", "ChocoParser"),
    "NixParser": ("package_maximizer.parsers.extra_parsers", "NixParser"),
    "GuixParser": ("package_maximizer.parsers.extra_parsers", "GuixParser"),
    "SpackParser": ("package_maximizer.parsers.extra_parsers", "SpackParser"),
}

# Lazy registry over parser specs.
_PARSER_SPECS = {
    "apt": ("package_maximizer.parsers.apt_parser", "APTParser", None),
    "pacman": ("package_maximizer.parsers.pacman_parser", "PacmanParser", None),
    "dnf": ("package_maximizer.parsers.dnf_parser", "DNFParser", None),
    "brew": ("package_maximizer.parsers.brew_parser", "BrewParser", None),
    "snap": ("package_maximizer.parsers.extra_parsers", "SnapParser", None),
    "flatpak": ("package_maximizer.parsers.extra_parsers", "FlatpakParser", None),
    "cargo": ("package_maximizer.parsers.extra_parsers", "CargoParser", None),
    "npm": ("package_maximizer.parsers.extra_parsers", "NpmParser", None),
    "conda": ("package_maximizer.parsers.extra_parsers", "CondaParser", None),
    "portage": ("package_maximizer.parsers.extra_parsers", "PortageParser", None),
    "apk": ("package_maximizer.parsers.extra_parsers", "ApkParser", None),
    "zypper": ("package_maximizer.parsers.extra_parsers", "ZypperParser", None),
    "yum": ("package_maximizer.parsers.extra_parsers", "YumParser", None),
    "pip": ("package_maximizer.parsers.extra_parsers", "PipParser", None),
    "gem": ("package_maximizer.parsers.extra_parsers", "GemParser", None),
    "yarn": ("package_maximizer.parsers.extra_parsers", "YarnParser", None),
    "composer": ("package_maximizer.parsers.extra_parsers", "ComposerParser", None),
    "vcpkg": ("package_maximizer.parsers.extra_parsers", "VcpkgParser", None),
    "nuget": ("package_maximizer.parsers.extra_parsers", "NuGetParser", None),
    "winget": ("package_maximizer.parsers.extra_parsers", "WingetParser", None),
    "scoop": ("package_maximizer.parsers.extra_parsers", "ScoopParser", None),
    "choco": ("package_maximizer.parsers.extra_parsers", "ChocoParser", None),
    "nix": ("package_maximizer.parsers.extra_parsers", "NixParser", None),
    "guix": ("package_maximizer.parsers.extra_parsers", "GuixParser", None),
    "spack": ("package_maximizer.parsers.extra_parsers", "SpackParser", None),
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
    """Get parser instance by name."""
    parser_name = parser_name.lower()
    if parser_name not in PARSER_REGISTRY:
        available = ", ".join(PARSER_REGISTRY.keys())
        raise ValueError(f"Parser '{parser_name}' not found. Available: {available}")
    return PARSER_REGISTRY[parser_name]()


# --- Manifest loader (YAML/JSON/CSV + HTTP API) --------------------------------

from .manifest_loader import (
    ManifestLoader,
    ManifestParseException,
    RemoteManifestSource,
)

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
    "NixParser",
    "GuixParser",
    "SpackParser",
    "get_parser",
    "PARSER_REGISTRY",
    # Manifest loader
    "ManifestLoader",
    "RemoteManifestSource",
    "ManifestParseException",
]


def __getattr__(name: str):
    spec = _PUBLIC_PARSER_NAMES.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, class_name = spec
    import importlib

    module = importlib.import_module(module_path, __name__)
    return getattr(module, class_name)
