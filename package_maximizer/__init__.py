"""
Package Maximizer - Модульная система для максимизации пакетов

Система для решения задачи максимизации непротиворечивого множества пакетов
с использованием различных SAT/ILP/SMT солверов.
"""

__version__ = "0.1.0"
__author__ = "Package Maximizer Team"
__email__ = "team@package-maximizer.dev"
__license__ = "MIT"

# Enums
from .core.enums import PackageManagerType, SolverType
from .core.interfaces import ConstraintSolver, PackageParser, ResultAnalyzer
from .core.maximizer import PackageMaximizer
from .core.package import Package, PackageConstraint

__all__ = [
    "Package",
    "PackageConstraint",
    "PackageMaximizer",
    "PackageParser",
    "ConstraintSolver",
    "ResultAnalyzer",
    "PackageManagerType",
    "SolverType",
    "__version__",
]
