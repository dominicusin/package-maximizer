# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0] - 2026-09-05

### Added
- **NpmMetadataAdapter**: парсер метаданных npm (package-lock.json v2/v3)
  - `parse()`: парсит `npm view` JSON и `package-lock.json`
  - `parse_lockfile()`: разбирает lockfile v2/v3
  - `fetch()`: зовёт `npm view <pkg> json`
- **BrewMetadataAdapter**: парсер метаданных brew
  - `parse()`: парсит JSON от `brew info --json=v2`
  - `fetch()`: зовёт `brew info --json=v2 <pkg>`
  - Поддержка dependencies, conflicts_with, versions
- **get_adapter()** теперь поддерживает npm и brew

### Tests
- 14 тестов для NpmMetadataAdapter и BrewMetadataAdapter
- Всего 779 тестов

## [0.9.0] - 2026-09-05

### Added
- **CLI `propose` command**: automatic metadata extraction + maximization
  - `package-maximizer propose nginx apache2 --manager apt --explain`
  - Auto-fetches depends/conflicts via adapters
  - `--explain` shows why packages were excluded
- **Web API `/api/v1/propose`**: POST endpoint with automatic metadata extraction
  - Accepts `packages`, `manager`, `solver`, `explain` fields
  - Returns `metadata_fetched`, `metadata` summary, and optional `excluded` reasons
- **Adapter `fetch()` method**: subprocess call + parse for APT, pip, pacman
  - `APTMetadataAdapter.fetch()` → `apt-cache show`
  - `PipMetadataAdapter.fetch()` → `pip show`
  - `PacmanMetadataAdapter.fetch()` → `pacman -Si`
- **`get_adapter(manager)` factory**: get adapter by manager name
- **Tests**: 8 tests for propose CLI, 5 tests for propose web API

### Changed
- Adapters now support both `parse()` (from raw string) and `fetch()` (from repository)

## [0.7.1] - 2026-09-05

### Added
- **Metadata adapters** (`adapters/`): парсеры метаданных для APT, pip, pacman
  - `APTMetadataAdapter`: парсит `apt-cache show` / `dpkg -s`
  - `PipMetadataAdapter`: парсит `pip show` / METADATA
  - `PacmanMetadataAdapter`: парсит `pacman -Si` / `-Qi`
- **E2E tests** на реальных фикстурах: nginx, apache2, requests, certifi, vim

## [0.7.0] - 2026-09-05

### Added
- **Dependency support**: `depends` field now properly encoded as implications in all solvers.
  - `Package(depends=["pkg2"])` → `selected(pkg1) ⇒ selected(pkg2)`
  - Greedy, EnhancedGreedy, Z3, PuLP, OR-Tools, MaxSAT, MiniSAT all respect dependencies
- **Model encoder** (`core/model_encoder.py`): intermediate constraint layer shared by all solvers
- **CLI `--depends` flag**: specify dependencies via `-d pkg dep`
- **CLI `--explain` flag**: shows why packages were excluded (conflicts, missing deps)
- **Web API `depends` field**: POST `/api/v1/maximize` accepts `depends: [["pkg", "dep"]]`
- **Web API `explain` flag**: returns exclusion reasons in response

### Changed
- Solvers now use `ModelConstraints` from `encode_packages()` for consistent constraint encoding
- Greedy solver sorts by weight (descending) in weighted mode

## [0.6.1] - 2026-09-04

### Fixed
- Version sync: `__init__.py`, `CITATION.cff`, web health/OpenAPI now read from `importlib.metadata` (single source of truth).
- `PackageManagerType` enum now matches `PARSER_REGISTRY` keys exactly (removed Nix/Guix/Spack/XBPS without parsers; added pip/npm/cargo/etc.).
- Auto parser selection via `get_parser(self.manager.value)` instead of hardcoded 4-entry map.
- `EnhancedGreedySolver` now correctly inferred from instance (was falling back to `GREEDY`).
- Web server now refuses to start without `PM_API_KEY` set (no more `dev-key-change-in-production` default).

### Changed
- CHANGELOG order: `[0.6.0]` moved above `[0.5.0]`.
- Removed "Planned" section from `[0.6.0]` (JWT/Flask-Limiter are debt, not features).

## [0.6.0] - 2026-09-02

### Added
- Textual TUI (`pm tui`) for interactive terminal UX.
- Optional property-based tests via `hypothesis` (skipped when missing).
- LRU cache decorators for solver/parser factory lookups.
- Benchmark report export (`json`, `csv`).
- Sphinx documentation with ReadTheDocs config (`.readthedocs.yaml`).
- CI coverage gate (`--cov-fail-under=85`, currently non-blocking at ~76%).
- Rate limiting for web API (in-memory, per API key).
- Conda and Portage parsers.
- Result exporters: JSON, CSV, GraphML.
- Config-driven CLI defaults via `-C/--config`.

### Planned (not yet implemented)
- JWT authentication support alongside API key.
- Flask-Limiter based rate limiting (currently in-memory fallback).

### Changed
- Lazy solver/parser registries to avoid optional-dependency import failures.
- `SolverType` enum extended with `ENHANCED_GREEDY`.
- README badges and multi-manager support documentation.

### Fixed
- Z3Solver `Solver` → `Optimize` critical bug.
- `pulp_solver` import compatibility.
- Makefile `PYTHON` override for venv compatibility.

## [0.6.0] - 2026-09-02

### Added
- 12 new package managers: apk, zypper, yum, pip, gem, yarn, composer, vcpkg, nuget, winget, scoop, choco.
- Registered CondaParser and PortageParser (were implemented but not registered).
- Total registered package managers: **8 → 22**.
- CLI `list-managers` command shows all supported package managers.
- Updated README with full list of 22 package managers.

### Changed
- Updated `--manager` help text with all 22 options.
- Updated package description to reflect 22+ package manager support.

### Tests
- Added 24 tests for all new parsers.
- Added tests for `list-managers` CLI command.
- Total: 492 passed, 2 skipped.
- Coverage: **85%**.
