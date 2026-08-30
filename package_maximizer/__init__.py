"""
Package Maximizer - Модульная система для максимизации непротиворечивого множества пакетов.

Использует различные SAT/ILP/SMT солверы для множественных пакетных менеджеров.
"""

__version__ = "0.4.0"
__author__ = "Package Maximizer Team"
__email__ = "team@package-maximizer.dev"
__license__ = "MIT"

# Core components
from .core.enums import PackageManagerType, SolverType, PackageStatus
from .core.interfaces import ConstraintSolver, PackageParser, ResultAnalyzer
from .core.maximizer import PackageMaximizer
from .core.package import Package, PackageConstraint
from .core.constraints import VersionConstraint, DependencyConstraint, ConflictConstraint, ConstraintParser

# Solvers
from .solvers import (
    GreedySolver,
    Z3Solver,
    PulPSolver,
    ORToolsSolver,
    MaxSatSolver,
    MiniSatSolver,
    EnhancedGreedySolver,
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

# Utilities
from .utils import (
    CacheManager,
    BenchmarkRunner,
)

# Integrations
from .integrations import RealRepoIntegration

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
]
