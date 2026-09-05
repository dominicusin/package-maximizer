"""Типы пакетных менеджеров и солверов."""

from enum import Enum


class PackageManagerType(Enum):
    """Package managers supported by the parser registry.

    Every value must have a matching entry in ``parsers.PARSER_REGISTRY``.
    """

    APT = "apt"
    PACMAN = "pacman"
    DNF = "dnf"
    BREW = "brew"
    SNAP = "snap"
    FLATPAK = "flatpak"
    CARGO = "cargo"
    NPM = "npm"
    CONDA = "conda"
    PORTAGE = "portage"
    APK = "apk"
    ZYPPER = "zypper"
    YUM = "yum"
    PIP = "pip"
    GEM = "gem"
    YARN = "yarn"
    COMPOSER = "composer"
    VCPKG = "vcpkg"
    NUGET = "nuget"
    WINGET = "winget"
    SCOOP = "scoop"
    CHOCO = "choco"


class SolverType(Enum):
    GREEDY = "greedy"
    ENHANCED_GREEDY = "enhanced_greedy"
    Z3 = "z3"
    PULP = "pulp"
    ORTOOLS = "ortools"
    MAXSAT = "maxsat"
    MINISAT = "minisat"


class PackageStatus(Enum):
    INSTALLED = "installed"
    MISSING = "missing"
    CONFLICTED = "conflicted"
    CANDIDATE = "candidate"
