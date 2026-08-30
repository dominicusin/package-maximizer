"""
Package Maximizer - Модульная система для максимизации непротиворечивого множества пакетов.

Использует различные SAT/ILP/SMT солверы для множественных пакетных менеджеров.
"""

__version__ = "0.3.0"
__author__ = "Package Maximizer Team"
__email__ = "team@package-maximizer.dev"
__license__ = "MIT"

# Core components
from .core.enums import PackageManagerType, SolverType, PackageStatus
from .core.interfaces import ConstraintSolver, PackageParser, ResultAnalyzer
from .core.maximizer import PackageMaximizer
from .core.package import Package, PackageConstraint

# Solvers
from .solvers import (
    GreedySolver,
    Z3Solver,
    PulPSolver,
    ORToolsSolver,
    MaxSatSolver,
    MiniSatSolver,
    get_solver,
    SOLVER_REGISTRY,
)

# Parsers
from .parsers import (
    APTParser,
    PacmanParser,
    DNFParser,
    BrewParser,
    get_parser,
    PARSER_REGISTRY,
)

# Analyzers
from .analyzers import (
    ResultAnalyzer,
    get_analyzer,
    ANALYZER_REGISTRY,
)

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
    "PackageMaximizer",
    
    # Solvers
    "GreedySolver",
    "Z3Solver",
    "PulPSolver",
    "ORToolsSolver",
    "MaxSatSolver",
    "MiniSatSolver",
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
]
