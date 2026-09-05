"""
Package Maximizer - Модульная система для максимизации непротиворечивого множества пакетов.

Использует различные SAT/ILP/SMT солверы для множественных пакетных менеджеров.
"""

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _dist_version

    try:
        __version__ = _dist_version("package-maximizer")
    except PackageNotFoundError:
        __version__ = "0.7.1"
except ImportError:  # pragma: no cover — Python < 3.8
    __version__ = "0.7.1"
__author__ = "Package Maximizer Team"
__email__ = "team@package-maximizer.dev"
__license__ = "MIT"

# Analyzers
from .analyzers import ANALYZER_REGISTRY, ResultAnalyzer, get_analyzer
# CLI
from .cli import (benchmark, check_updates, cli, from_file, info,
                  list_installed, list_parsers, list_solvers, maximize, search,
                  system_info, version)
from .core.constraints import (ConflictConstraint, ConstraintParser,
                               DependencyConstraint, VersionConstraint)
# Core components
from .core.enums import PackageManagerType, PackageStatus, SolverType
from .core.interfaces import ConstraintSolver, PackageParser
from .core.interfaces import ResultAnalyzer as ResultAnalyzerInterface
from .core.maximizer import PackageMaximizer
from .core.package import Package, PackageConstraint
# Integrations
from .integrations import RealRepoIntegration
# Parsers
from .parsers import (PARSER_REGISTRY, APTParser, BrewParser, DNFParser,
                      PacmanParser, get_parser)
# Solvers
from .solvers import (SOLVER_REGISTRY, EnhancedGreedySolver, GreedySolver,
                      MaxSatSolver, MiniSatSolver, ORToolsSolver, PulPSolver,
                      Z3Solver, get_solver)
# Utilities
from .utils import BenchmarkRunner, CacheManager

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Enums
    "PackageManagerType",
    "SolverType",
    "PackageStatus",
    # Interfaces
    "ConstraintSolver",
    "PackageParser",
    "ResultAnalyzer",
    # Core classes
    "Package",
    "PackageConstraint",
    "VersionConstraint",
    "DependencyConstraint",
    "ConflictConstraint",
    "ConstraintParser",
    "PackageMaximizer",
    # Solvers
    "GreedySolver",
    "Z3Solver",
    "PulPSolver",
    "ORToolsSolver",
    "MaxSatSolver",
    "MiniSatSolver",
    "EnhancedGreedySolver",
    "get_solver",
    "SOLVER_REGISTRY",
    # Parsers
    "APTParser",
    "PacmanParser",
    "DNFParser",
    "BrewParser",
    "get_parser",
    "PARSER_REGISTRY",
    # Analyzers
    "ResultAnalyzer",
    "get_analyzer",
    "ANALYZER_REGISTRY",
    # Utilities
    "CacheManager",
    "BenchmarkRunner",
    # Integrations
    "RealRepoIntegration",
    # CLI
    "cli",
    "maximize",
    "list_solvers",
    "list_parsers",
    "version",
    "from_file",
    "benchmark",
    "list_installed",
    "search",
    "info",
    "check_updates",
    "system_info",
]
