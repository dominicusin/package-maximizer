"""
Package Maximizer - Модульная система для максимизации пакетов

Система для решения задачи максимизации непротиворечивого множества пакетов
с использованием различных SAT/ILP/SMT солверов.
"""

__version__ = "0.1.0"
__author__ = "Package Maximizer Team"
__email__ = "team@package-maximizer.dev"
__license__ = "MIT"

from .core.package import Package, PackageConstraint
from .core.maximizer import PackageMaximizer
from .core.interfaces import PackageParser, ConstraintSolver, ResultAnalyzer

# Enums
from .core.enums import PackageManagerType, SolverType

__all__ = [
    "Package",
    "PackageConstraint", 
    "PackageMaximizer",
    "PackageParser",
    "ConstraintSolver", 
    "ResultAnalyzer",
    "PackageManagerType",
    "SolverType",
    "__version__"
]
