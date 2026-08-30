"""Property-based tests for Package Maximizer core invariants."""

from __future__ import annotations

try:
    from hypothesis import given, settings, strategies as st
except ImportError:  # pragma: no cover - optional dependency
    import pytest

    pytest.skip("hypothesis not installed", allow_module_level=True)

from package_maximizer.core.package import Package
from package_maximizer.solvers import GreedySolver, EnhancedGreedySolver


# Strategy for small package names / versions
names = st.text(min_size=1, max_size=20, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=('_-')
))
versions = st.one_of(st.none(), st.text(min_size=1, max_size=10))


class TestGreedyInvariants:
    """Greedy solvers should satisfy basic set invariants."""

    @given(st.lists(names, min_size=0, max_size=12, unique=True))
    @settings(max_examples=60)
    def test_selected_is_subset(self, pkg_names):
        solver = GreedySolver()
        packages = [Package(name=n) for n in pkg_names]
        selected = solver.solve(packages)
        assert set(selected) <= {p.name for p in packages}

    @given(st.lists(names, min_size=0, max_size=12, unique=True))
    @settings(max_examples=60)
    def test_no_duplicates_in_result(self, pkg_names):
        solver = GreedySolver()
        packages = [Package(name=n) for n in pkg_names]
        selected = solver.solve(packages)
        assert len(selected) == len(set(selected))

    @given(st.lists(names, min_size=0, max_size=12, unique=True))
    @settings(max_examples=60)
    def test_empty_input_returns_empty(self, pkg_names):
        if not pkg_names:
            solver = GreedySolver()
            selected = solver.solve([])
            assert selected == []


class TestEnhancedGreedyInvariants:
    """Enhanced greedy solver should satisfy set invariants."""

    @given(st.lists(names, min_size=0, max_size=12, unique=True))
    @settings(max_examples=50)
    def test_selected_is_subset(self, pkg_names):
        solver = EnhancedGreedySolver()
        packages = [Package(name=n) for n in pkg_names]
        selected = solver.solve(packages)
        assert set(selected) <= {p.name for p in packages}

    @given(st.lists(names, min_size=0, max_size=12, unique=True))
    @settings(max_examples=50)
    def test_conflicts_respected(self, pkg_names):
        if len(pkg_names) < 2:
            return
        solver = EnhancedGreedySolver()
        a, b = pkg_names[0], pkg_names[1]
        packages = [
            Package(name=a, conflicts=[b]),
            Package(name=b, conflicts=[a]),
        ]
        selected = solver.solve(packages)
        assert not ({a} & set(selected) and {b} & set(selected))
