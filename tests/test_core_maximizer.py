"""
Tests for core.maximizer module — targets uncovered branches.
"""

from __future__ import annotations

import pytest

from package_maximizer.core.maximizer import PackageMaximizer
from package_maximizer.core.package import Package
from package_maximizer.core.enums import PackageManagerType, SolverType


class TestPackageMaximizerInit:
    """Constructor defaults and cache setup."""

    def test_default_init(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        assert pm.manager == PackageManagerType.APT
        assert pm.solver_type == SolverType.GREEDY
        assert pm.use_cache is True

    def test_no_cache_init(self):
        pm = PackageMaximizer(manager="apt", solver="greedy", use_cache=False)
        assert pm.use_cache is False
        assert pm._get_cache() is None

    def test_custom_cache_ttl(self):
        pm = PackageMaximizer(manager="apt", solver="greedy", cache_ttl=600)
        cache = pm._get_cache()
        assert cache is not None
        assert cache.default_ttl == 600


class TestGetSolverInstance:
    """_get_solver_instance with valid and invalid types."""

    def test_valid_solver(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        solver = pm._get_solver_instance(SolverType.GREEDY)
        assert solver is not None
        assert solver.__class__.__name__ == "GreedySolver"

    def test_invalid_solver_fallback(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from unittest.mock import patch
        with patch("package_maximizer.solvers.get_solver", side_effect=ValueError("not found")):
            solver = pm._get_solver_instance(SolverType.Z3)
            assert solver.__class__.__name__ == "GreedySolver"


class TestInferSolverType:
    """_infer_solver_type maps class names to SolverType."""

    def test_greedy(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import GreedySolver
        assert pm._infer_solver_type(GreedySolver()) == SolverType.GREEDY

    def test_z3(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import Z3Solver
        assert pm._infer_solver_type(Z3Solver()) == SolverType.Z3

    def test_pulp(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import PulPSolver
        assert pm._infer_solver_type(PulPSolver()) == SolverType.PULP

    def test_ortools(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import ORToolsSolver
        assert pm._infer_solver_type(ORToolsSolver()) == SolverType.ORTOOLS

    def test_maxsat(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import MaxSatSolver
        assert pm._infer_solver_type(MaxSatSolver()) == SolverType.MAXSAT

    def test_minisat(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import MiniSatSolver
        assert pm._infer_solver_type(MiniSatSolver()) == SolverType.MINISAT

    def test_enhanced_greedy(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import EnhancedGreedySolver
        assert pm._infer_solver_type(EnhancedGreedySolver()) == SolverType.ENHANCED_GREEDY

    def test_unknown_defaults_to_greedy(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        assert pm._infer_solver_type(object()) == SolverType.GREEDY


class TestGetParserInstance:
    """_get_parser_instance with None, str, and object."""

    def test_none_uses_auto_selection(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        parser = pm._get_parser_instance(None)
        assert parser is not None
        assert parser.__class__.__name__ == "APTParser"

    def test_string_parser(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        parser = pm._get_parser_instance("pacman")
        assert parser.__class__.__name__ == "PacmanParser"

    def test_invalid_string_returns_none(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        parser = pm._get_parser_instance("nonexistent_parser_xyz")
        assert parser is None

    def test_object_parser_passthrough(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.parsers import APTParser
        parser_obj = APTParser()
        result = pm._get_parser_instance(parser_obj)
        assert result is parser_obj

    def test_pip_manager_gets_pip_parser(self):
        """Regression: manager='pip' should auto-select PipParser, not APTParser."""
        pm = PackageMaximizer(manager="pip", solver="greedy")
        assert pm.parser is not None
        assert pm.parser.__class__.__name__ == "PipParser"

    def test_npm_manager_gets_npm_parser(self):
        """Regression: manager='npm' should auto-select NpmParser."""
        pm = PackageMaximizer(manager="npm", solver="greedy")
        assert pm.parser is not None
        assert pm.parser.__class__.__name__ == "NpmParser"

    def test_unknown_string_returns_none(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        parser = pm._get_parser_instance("totally_unknown_parser_zzz")
        assert parser is None

class TestGetAnalyzerInstance:
    """_get_analyzer_instance with None, str, and object."""

    def test_none_creates_default(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        analyzer = pm._get_analyzer_instance(None)
        assert analyzer is not None
        assert analyzer.__class__.__name__ == "ResultAnalyzer"

    def test_string_analyzer(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        analyzer = pm._get_analyzer_instance("basic")
        assert analyzer is not None

    def test_invalid_string_returns_none(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        analyzer = pm._get_analyzer_instance("nonexistent_analyzer_xyz")
        assert analyzer is None

    def test_object_analyzer_passthrough(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.analyzers import ResultAnalyzer
        analyzer_obj = ResultAnalyzer()
        result = pm._get_analyzer_instance(analyzer_obj)
        assert result is analyzer_obj


class TestMaximize:
    """maximize method with caching and package selection."""

    def test_maximize_returns_packages(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [Package(name="a"), Package(name="b"), Package(name="c")]
        result = pm.maximize(pkgs)
        assert isinstance(result, list)
        assert all(isinstance(p, Package) for p in result)

    def test_maximize_uses_cache(self):
        pm = PackageMaximizer(manager="apt", solver="greedy", use_cache=True)
        pkgs = [Package(name="a"), Package(name="b")]
        result1 = pm.maximize(pkgs)
        result2 = pm.maximize(pkgs)
        assert result1 == result2

    def test_maximize_no_cache(self):
        pm = PackageMaximizer(manager="apt", solver="greedy", use_cache=False)
        pkgs = [Package(name="a"), Package(name="b")]
        result = pm.maximize(pkgs)
        assert isinstance(result, list)


class TestSolve:
    """solve method returns list of names."""

    def test_solve_returns_names(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [Package(name="a"), Package(name="b"), Package(name="c")]
        result = pm.solve(pkgs)
        assert isinstance(result, list)
        assert all(isinstance(n, str) for n in result)

    def test_solve_with_conflicts(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
        ]
        result = pm.solve(pkgs)
        assert not ("a" in result and "b" in result)


class TestSolveWithWeights:
    """solve_with_weights with caching and fallback."""

    def test_solve_with_weights(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [Package(name="a"), Package(name="b")]
        weights = {"a": 2.0, "b": 1.0}
        result = pm.solve_with_weights(pkgs, weights)
        assert isinstance(result, list)

    def test_solve_with_weights_uses_cache(self):
        pm = PackageMaximizer(manager="apt", solver="greedy", use_cache=True)
        pkgs = [Package(name="a"), Package(name="b")]
        weights = {"a": 2.0}
        result1 = pm.solve_with_weights(pkgs, weights)
        result2 = pm.solve_with_weights(pkgs, weights)
        assert result1 == result2

    def test_solve_with_weights_no_cache(self):
        pm = PackageMaximizer(manager="apt", solver="greedy", use_cache=False)
        pkgs = [Package(name="a")]
        result = pm.solve_with_weights(pkgs, {"a": 1.0})
        assert isinstance(result, list)

    def test_solve_with_weights_fallback(self):
        """When solver doesn't support weights, falls back to solve."""
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [Package(name="a"), Package(name="b")]
        result = pm.solve_with_weights(pkgs, {"a": 1.0})
        assert isinstance(result, list)


class TestGetCacheKey:
    """_get_cache_key generates unique keys."""

    def test_cache_key_is_string(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [Package(name="a")]
        key = pm._get_cache_key("test", pkgs)
        assert isinstance(key, str)

    def test_cache_key_with_weights(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [Package(name="a")]
        key = pm._get_cache_key("test", pkgs, {"a": 1.0})
        assert isinstance(key, str)

    def test_different_inputs_different_keys(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs1 = [Package(name="a")]
        pkgs2 = [Package(name="b")]
        key1 = pm._get_cache_key("test", pkgs1)
        key2 = pm._get_cache_key("test", pkgs2)
        assert key1 != key2


class TestCheckConstraints:
    """check_constraints validates package constraints."""

    def test_check_constraints_returns_dict(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pkgs = [Package(name="a", version="1.0")]
        from package_maximizer.core.package import PackageConstraint
        constraints = [PackageConstraint(package="a", version=">=1.0")]
        result = pm.check_constraints(pkgs, constraints)
        assert isinstance(result, dict)
        assert "a" in result


class TestAnalyze:
    """analyze method."""

    def test_analyze_with_analyzer(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        result = pm.analyze(installed=["a", "b"], proposed=["c"])
        assert isinstance(result, dict)

    def test_analyze_without_analyzer(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.analyzer = None
        result = pm.analyze(installed=["a"], proposed=["b"])
        assert result == {}


class TestParsePackages:
    """parse_packages method."""

    def test_parse_packages_with_parser(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        result = pm.parse_packages("vim 8.0\nemacs 27")
        assert isinstance(result, list)

    def test_parse_packages_without_parser(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.parser = None
        result = pm.parse_packages("vim 8.0")
        assert result == []


class TestParseFromSystem:
    """parse_from_system method."""

    def test_parse_from_system_no_parser(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.parser = None
        result = pm.parse_from_system(["vim"])
        assert result == []

    def test_parse_from_system_parser_without_method(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        # APTParser doesn't have parse_from_system
        result = pm.parse_from_system(["vim"])
        assert isinstance(result, list)


class TestFromNames:
    """from_names static method."""

    def test_from_names_creates_packages(self):
        result = PackageMaximizer.from_names(["a", "b", "c"])
        assert len(result) == 3
        assert all(isinstance(p, Package) for p in result)
        assert [p.name for p in result] == ["a", "b", "c"]


class TestSetSolver:
    """set_solver with SolverType, str, and object."""

    def test_set_solver_by_type(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.set_solver(SolverType.ENHANCED_GREEDY)
        assert pm.solver_type == SolverType.ENHANCED_GREEDY

    def test_set_solver_by_string(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.set_solver("enhanced_greedy")
        assert pm.solver_type == SolverType.ENHANCED_GREEDY

    def test_set_solver_by_object(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.solvers import GreedySolver
        solver = GreedySolver()
        pm.set_solver(solver)
        assert pm.solver is solver
        assert pm.solver_type == SolverType.GREEDY


class TestSetParser:
    """set_parser with str and object."""

    def test_set_parser_by_string(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.set_parser("pacman")
        assert pm.parser.__class__.__name__ == "PacmanParser"

    def test_set_parser_by_object(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.parsers import APTParser
        parser = APTParser()
        pm.set_parser(parser)
        assert pm.parser is parser

    def test_set_parser_none(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.set_parser(None)
        # Should auto-select based on manager
        assert pm.parser is not None


class TestSetAnalyzer:
    """set_analyzer with str and object."""

    def test_set_analyzer_by_string(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.set_analyzer("basic")
        assert pm.analyzer is not None

    def test_set_analyzer_by_object(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        from package_maximizer.analyzers import ResultAnalyzer
        analyzer = ResultAnalyzer()
        pm.set_analyzer(analyzer)
        assert pm.analyzer is analyzer

    def test_set_analyzer_none(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        pm.set_analyzer(None)
        assert pm.analyzer is not None


class TestGetters:
    """get_solver, get_solver_type, get_parser, get_analyzer."""

    def test_get_solver(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        assert pm.get_solver() is pm.solver

    def test_get_solver_type(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        assert pm.get_solver_type() == SolverType.GREEDY

    def test_get_parser(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        assert pm.get_parser() is pm.parser

    def test_get_analyzer(self):
        pm = PackageMaximizer(manager="apt", solver="greedy")
        assert pm.get_analyzer() is pm.analyzer


class TestClearCache:
    """clear_cache method."""

    def test_clear_cache(self):
        pm = PackageMaximizer(manager="apt", solver="greedy", use_cache=True)
        pm._cache["test"] = "value"
        pm.clear_cache()
        assert len(pm._cache) == 0
