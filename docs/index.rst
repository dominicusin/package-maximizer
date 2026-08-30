# Package Maximizer Documentation

Welcome to **Package Maximizer** — a modular system for maximizing non-conflicting package sets using various SAT/ILP/SMT solvers.

## 📖 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Solvers](#solvers)
- [Parsers](#parsers)
- [CLI Reference](#cli-reference)
- [Web API](#web-api)
- [Contributing](#contributing)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/dominicusin/package-maximizer.git
cd package-maximizer

# Install all dependencies
pip install -e ".[all]"

# Or install specific components
pip install -e "."                    # Core only
pip install -e ".[solvers]"           # Add solvers
pip install -e ".[web]"             # Add web interface
```

---

## Quick Start

```python
from package_maximizer import PackageMaximizer, Package

# Create packages with conflicts
packages = [
    Package(name="nginx", conflicts=["apache2"]),
    Package(name="apache2", conflicts=["nginx"]),
    Package(name="python3"),
    Package(name="postgresql"),
]

# Solve with a specific solver
maximizer = PackageMaximizer(manager="apt", solver="z3")
result = maximizer.maximize(packages)

print("Selected packages:", [p.name for p in result])
```

---

## Architecture

```
package_maximizer/
├── core/              # Core domain models and interfaces
│   ├── package.py     # Package, PackageConstraint
│   ├── constraints.py # Version, Dependency, Conflict constraints
│   ├── interfaces.py  # Solver, Parser, Analyzer ABCs
│   ├── maximizer.py   # Main PackageMaximizer class
│   └── enums.py       # PackageManagerType, SolverType
├── solvers/           # SAT/ILP/SMT solvers
│   ├── greedy.py      # Basic greedy algorithm
│   ├── z3_solver.py   # Z3 SMT solver
│   ├── pulp_solver.py # PuLP ILP solver
│   ├── ortools_solver.py # OR-Tools CP-SAT
│   ├── maxsat_solver.py # MaxSAT (PySAT)
│   ├── minisat_solver.py # MiniSat (PySAT)
│   └── enhanced_greedy.py # Version-aware greedy
├── parsers/           # Package manager parsers
│   ├── apt_parser.py  # Debian/Ubuntu
│   ├── pacman_parser.py # Arch Linux
│   ├── dnf_parser.py  # Fedora/RHEL
│   └── brew_parser.py # macOS Homebrew
├── analyzers/         # Result analysis
├── integrations/      # Real repository integration
├── utils/             # Cache, Benchmark
├── web/               # Flask/FastAPI web interface
└── cli/               # Command-line interface
```

---

## API Reference

::: package_maximizer.PackageMaximizer
    handler: python
    options:
      show_source: true

::: package_maximizer.Package
    handler: python
    options:
      show_source: true

::: package_maximizer.core.constraints.VersionConstraint
    handler: python
    options:
      show_source: true

---

## Solvers

| Solver | Type | Dependencies | Description |
|--------|------|--------------|-------------|
| `GreedySolver` | Greedy | Built-in | Basic greedy algorithm |
| `EnhancedGreedySolver` | Greedy+ | Built-in | Version-aware greedy |
| `Z3Solver` | SMT | `pip install z3-solver` | Microsoft Z3 theorem prover |
| `PulPSolver` | ILP | `pip install pulp` | PuLP linear programming |
| `ORToolsSolver` | CP-SAT | `pip install ortools` | Google OR-Tools |
| `MaxSatSolver` | SAT | `pip install python-sat` | MaxSAT with PySAT |
| `MiniSatSolver` | SAT | `pip install python-sat` | MiniSat backend |

---

## Parsers

| Parser | Package Manager | Platforms |
|--------|-----------------|-----------|
| `APTParser` | APT (dpkg) | Debian, Ubuntu |
| `PacmanParser` | Pacman | Arch Linux |
| `DNFParser` | DNF (yum) | Fedora, RHEL, CentOS |
| `BrewParser` | Homebrew | macOS, Linux |

---

## CLI Reference

```bash
# Maximize packages
package-maximizer pkg1 pkg2 pkg3 -s z3

# With conflicts
package-maximizer pkg1 pkg2 -c pkg1,pkg2 -s greedy

# With weights (priorities)
package-maximizer pkg1 pkg2 -w pkg1,10.0 -w pkg2,5.0

# JSON output
package-maximizer pkg1 pkg2 -o json

# List available solvers
package-maximizer list-solvers

# List available parsers
package-maximizer list-parsers

# Run benchmark
package-maximizer benchmark --solvers greedy,z3 --packages 100

# Work with real repos
package-maximizer list-installed --manager apt
package-maximizer search python3 --manager apt
package-maximizer info nginx --manager apt
package-maximizer check-updates --manager apt
package-maximizer system-info --manager apt
```

---

## Web API

```bash
# Start the server
pm-web

# Or use environment variables
PM_API_KEY=your-secret-key PM_CACHE_TTL=3600 pm-web
```

See [README.md](https://github.com/dominicusin/package-maximizer#readme) for API documentation.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python -m pytest tests/ -v`
4. Ensure lint: `flake8 package_maximizer/ tests/`
5. Create a Pull Request

---

*This documentation is auto-generated with Sphinx and ReadTheDocs.*