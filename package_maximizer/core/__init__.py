"""
Core module — Ядро системы Package Maximizer.
"""

from .constraints import (
    ConflictConstraint,
    ConstraintParser,
    DependencyConstraint,
    VersionConstraint,
)
from .enums import PackageManagerType, PackageStatus, SolverType
from .interfaces import ConstraintSolver, PackageParser, ResultAnalyzer
from .maximizer import PackageMaximizer
from .model_encoder import ModelConstraints, encode_packages
from .package import Package, PackageConstraint

__all__ = [
    "PackageManagerType",
    "SolverType",
    "PackageStatus",
    "ConstraintSolver",
    "PackageParser",
    "ResultAnalyzer",
    "PackageMaximizer",
    "ModelConstraints",
    "encode_packages",
    "Package",
    "PackageConstraint",
    "VersionConstraint",
    "DependencyConstraint",
    "ConflictConstraint",
    "ConstraintParser",
]
