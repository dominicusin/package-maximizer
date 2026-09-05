"""
Core module — Ядро системы Package Maximizer.
"""

from .enums import PackageManagerType, SolverType, PackageStatus
from .interfaces import ConstraintSolver, PackageParser, ResultAnalyzer
from .maximizer import PackageMaximizer
from .model_encoder import ModelConstraints, encode_packages
from .package import Package, PackageConstraint
from .constraints import VersionConstraint, DependencyConstraint, ConflictConstraint, ConstraintParser

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
