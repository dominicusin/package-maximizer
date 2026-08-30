"""Типы пакетных менеджеров и солверов."""

from enum import Enum


class PackageManagerType(Enum):
    APT = "apt"
    PACMAN = "pacman"
    DNF = "dnf"
    ZYPPER = "zypper"
    BREW = "brew"
    SPACK = "spack"
    FLATPAK = "flatpak"
    SNAP = "snap"
    NIX = "nix"
    GUIX = "guix"
    PORTAGE = "portage"
    XBS = "xbps"


class SolverType(Enum):
    GREEDY = "greedy"
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
