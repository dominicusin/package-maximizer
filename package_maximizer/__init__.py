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
        __version__ = "0.29.0"
except ImportError:  # pragma: no cover — Python < 3.8
    __version__ = "0.29.0"
__author__ = "Package Maximizer Team"
__email__ = "team@package-maximizer.dev"
__license__ = "MIT"

# Analyzers
from .analyzers import ANALYZER_REGISTRY, ResultAnalyzer, get_analyzer

# CLI
from .cli import (
    benchmark,
    check_updates,
    cli,
    from_file,
    info,
    list_installed,
    list_parsers,
    list_solvers,
    maximize,
    search,
    system_info,
    version,
)
from .core.constraints import (
    ConflictConstraint,
    ConstraintParser,
    DependencyConstraint,
    VersionConstraint,
)

# Core components
from .core.enums import PackageManagerType, PackageStatus, SolverType
from .core.graph_builder import (
    GraphBuilder,
    PackageGraph,
    build_buildtime_graph,
    build_runtime_graph,
    detect_cycles,
)
from .core.interfaces import ConstraintSolver, PackageParser
from .core.interfaces import ResultAnalyzer as ResultAnalyzerInterface
from .core.maximizer import PackageMaximizer
from .core.objective import Objective, get_default_weights
from .core.package import Package, PackageConstraint

# Integrations
from .integrations import RealRepoIntegration

# Parsers
from .parsers import (
    PARSER_REGISTRY,
    APTParser,
    BrewParser,
    DNFParser,
    PacmanParser,
    get_parser,
)

# Manifest parsing (YAML/JSON/CSV + remote HTTP inventory)
from .parsing import ManifestLoader, ManifestParseException, RemoteManifestSource

# Solvers
from .solvers import (
    SOLVER_REGISTRY,
    BacktrackingSolver,
    EnhancedGreedySolver,
    GreedySolver,
    MaxSatSolver,
    MiniSatSolver,
    ORToolsSolver,
    PulPSolver,
    Z3Solver,
    get_solver,
)

# Utilities
from .utils import BenchmarkRunner, CacheManager, ResourceMonitor, ResourceSnapshot

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
    "GraphBuilder",
    "PackageGraph",
    "build_runtime_graph",
    "build_buildtime_graph",
    "detect_cycles",
    "Objective",
    "get_default_weights",
    # Solvers
    "GreedySolver",
    "Z3Solver",
    "PulPSolver",
    "ORToolsSolver",
    "MaxSatSolver",
    "MiniSatSolver",
    "EnhancedGreedySolver",
    "BacktrackingSolver",
    "get_solver",
    "SOLVER_REGISTRY",
    # Manifest parsing
    "ManifestLoader",
    "RemoteManifestSource",
    "ManifestParseException",
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
    "ResourceMonitor",
    "ResourceSnapshot",
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
