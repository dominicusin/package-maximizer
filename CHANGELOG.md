# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-08-31

### Added
- Textual TUI (`pm tui`) for interactive terminal UX.
- Optional property-based tests via `hypothesis` (skipped when missing).
- LRU cache decorators for solver/parser factory lookups.
- Benchmark report export (`json`, `csv`).
- Sphinx documentation with ReadTheDocs config (`.readthedocs.yaml`).
- CI coverage gate (`--cov-fail-under=85`).
- JWT authentication support alongside API key.
- Rate limiting for web API (Flask-Limiter / in-memory fallback).
- Conda and Portage parsers.
- Result exporters: JSON, CSV, GraphML.
- Config-driven CLI defaults via `-C/--config`.

### Changed
- Lazy solver/parser registries to avoid optional-dependency import failures.
- `SolverType` enum extended with `ENHANCED_GREEDY`.
- README badges and multi-manager support documentation.

### Fixed
- Z3Solver `Solver` → `Optimize` critical bug.
- `pulp_solver` import compatibility.
- Makefile `PYTHON` override for venv compatibility.
