"""
Core module - Ядро системы Package Maximizer.
"""

from .enums import PackageManagerType, SolverType, PackageStatus
from .interfaces import ConstraintSolver, PackageParser, ResultAnalyzer
from .maximizer import PackageMaximizer
from .package import Package, PackageConstraint

__all__ = [
    "PackageManagerType",
    "SolverType",
    "PackageStatus",
    "ConstraintSolver",
    "PackageParser",
    "ResultAnalyzer",
    "PackageMaximizer",
    "Package",
    "PackageConstraint",
]
