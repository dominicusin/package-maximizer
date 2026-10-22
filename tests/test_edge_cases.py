"""Edge-case tests for the package-maximizer kernel.

Covers: cyclic dependencies, unresolvable conflicts, empty sets and the
choice between mutually exclusive versions.
"""

from __future__ import annotations

import logging
from io import StringIO

import pytest

from package_maximizer import Package, PackageMaximizer, SolverType


class TestEdgeCases:
    """Edge-case tests for PackageMaximizer."""

    # ------------------------------------------------------------------
    # Empty sets
    # ------------------------------------------------------------------

    def test_maximize_empty_package_list(self):
        """Empty input -> empty output."""
        maximizer = PackageMaximizer(solver=SolverType.GREEDY)
        assert maximizer.solve([]) == []
        assert maximizer.maximize([]) == []

    def test_solve_with_weights_empty(self):
        """Empty input with weights -> empty output."""
        maximizer = PackageMaximizer(solver=SolverType.GREEDY)
        assert maximizer.solve_with_weights([], {}) == []

    def test_greedy_empty(self):
        """Greedy solver on empty set."""
        solver = PackageMaximizer(solver=SolverType.GREEDY).get_solver()
        assert solver.solve([]) == []

    # ------------------------------------------------------------------
    # Cyclic dependencies (self-loop, two-way chain)
    # ------------------------------------------------------------------

    def test_self_cyclic_dependency(self):
        """A package that depends on itself must not break solving."""
        pkg = Package(name="selfpkg", depends=["selfpkg"])
        maximizer = PackageMaximizer(solver=SolverType.GREEDY)
        result = maximizer.solve([pkg])
        # solver must still return something consistent (self-dependency is
        # ignored because the package is the only one in scope)
        assert pkg.name in result

    def test_two_way_cyclic_dependency(self):
        """Only mutual dependencies A<->B -> both can be selected."""
        a = Package(name="a", depends=["b"])
        b = Package(name="b", depends=["a"])
        maximizer = PackageMaximizer(solver=SolverType.GREEDY)
        result = maximizer.solve([a, b])
        assert set(result) == {"a", "b"}

    def test_three_way_cycle(self):
        """A->B->C->A; all three can coexist."""
        a = Package(name="a", depends=["b"])
        b = Package(name="b", depends=["c"])
        c = Package(name="c", depends=["a"])
        maximizer = PackageMaximizer(solver=SolverType.GREEDY)
        result = maximizer.solve([a, b, c])
        assert set(result) == {"a", "b", "c"}

    # ------------------------------------------------------------------
    # Unresolvable conflicts (both sides forced by dependencies)
    # ------------------------------------------------------------------

    def test_conflict_with_forced_dependencies(self):
        """A and B conflict, but both depend on C. The solver must pick one
        of A/B and still include C."""
        a = Package(name="a", depends=["c"], conflicts=["b"])
        b = Package(name="b", depends=["c"], conflicts=["a"])
        c = Package(name="c")
        maximizer = PackageMaximizer(solver=SolverType.GREEDY)
        result = maximizer.solve([a, b, c])
        # Result may be names (str) or Package objects
        names = [p if isinstance(p, str) else p.name for p in result]
        selected = set(names)
        # Exactly one of a/b, plus c
        assert "c" in selected
        assert (selected == {"a", "c"}) or (selected == {"b", "c"})

    def test_mutually_exclusive_versions(self):
        """Two packages that cannot coexist (dependency-level conflict)."""
        x = Package(name="x", version="1.0", conflicts=["y"])
        y = Package(name="y", version="2.0", conflicts=["x"])
        maximizer = PackageMaximizer(solver=SolverType.GREEDY)
        result = maximizer.solve([x, y])
        assert len(result) == 1
        assert result[0] in (x.name, y.name)

    # ------------------------------------------------------------------
    # Strictness enforcements (warn / skip / fail)
    # ------------------------------------------------------------------

    def test_strictness_fail_raises_on_final_conflict(self):
        """strictness=fail rejects a final set that still contains a conflict."""
        maximizer = PackageMaximizer(solver=SolverType.GREEDY, strictness="fail")
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        packages = [pkg1, pkg2]
        from package_maximizer.core.model_encoder import encode_packages

        constraints = encode_packages(packages)
        with pytest.raises(ValueError, match="конфликтующие"):
            maximizer._apply_strictness(["pkg1", "pkg2"], constraints)

    def test_strictness_skip_removes_conflict(self):
        """strictness=skip drops the losing package from the final set."""
        maximizer = PackageMaximizer(solver=SolverType.GREEDY, strictness="skip")
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        packages = [pkg1, pkg2]
        from package_maximizer.core.model_encoder import encode_packages

        constraints = encode_packages(packages)
        result = maximizer._apply_strictness(["pkg1", "pkg2"], constraints)
        assert set(result) in ({"pkg1"}, {"pkg2"})

    def test_strictness_warn_keeps_conflict(self):
        """strictness=warn leaves the conflicting set as-is (with a warning)."""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        packages = [pkg1, pkg2]
        from package_maximizer.core.model_encoder import encode_packages

        constraints = encode_packages(packages)
        # Capture logs to assert the warning fires
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("package_maximizer.core.maximizer")
        logger.addHandler(handler)
        try:
            maximizer = PackageMaximizer(solver=SolverType.GREEDY, strictness="warn")
            result = maximizer._apply_strictness(["pkg1", "pkg2"], constraints)
        finally:
            logger.removeHandler(handler)
        # warn keeps everything
        assert set(result) == {"pkg1", "pkg2"}
        # Log message uses "Конфликтующие" — case-insensitive check
        assert "конфликт" in stream.getvalue().lower()
