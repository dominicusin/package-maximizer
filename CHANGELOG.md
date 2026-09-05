# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
