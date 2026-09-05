"""
Tests for PackageMaximizer.
"""

import pytest

from package_maximizer import Package, PackageManagerType, PackageMaximizer, SolverType
from package_maximizer.solvers import GreedySolver, Z3Solver


class TestPackageMaximizer:
    """Tests for PackageMaximizer."""

    def test_init_default(self):
        """Test default initialization."""
        maximizer = PackageMaximizer()
        assert maximizer.manager == PackageManagerType.APT
        assert maximizer.solver_type == SolverType.GREEDY

    def test_init_with_strings(self):
        """Test initialization with string parameters."""
        maximizer = PackageMaximizer(manager="pacman", solver="z3")
        assert maximizer.manager == PackageManagerType.PACMAN
        assert maximizer.solver_type == SolverType.Z3

    def test_init_with_enums(self):
        """Test initialization with enum parameters."""
        maximizer = PackageMaximizer(
            manager=PackageManagerType.DNF, solver=SolverType.PULP
        )
        assert maximizer.manager == PackageManagerType.DNF
        assert maximizer.solver_type == SolverType.PULP

    def test_init_with_solver_instance(self):
        """Test initialization with solver instance."""
        solver = GreedySolver()
        maximizer = PackageMaximizer(solver=solver)
        assert maximizer.solver is solver

    def test_maximize_no_conflicts(self):
        """Test maximize with no conflicts."""
        maximizer = PackageMaximizer(solver="greedy")
        packages = [
            Package(name="pkg1"),
            Package(name="pkg2"),
            Package(name="pkg3"),
        ]
        result = maximizer.maximize(packages)
        assert len(result) == 3

    def test_maximize_with_conflicts(self):
        """Test maximize with conflicts."""
        maximizer = PackageMaximizer(solver="greedy")
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        result = maximizer.maximize(packages)

        # Should select 2 packages (either pkg1 or pkg2, plus pkg3)
        assert len(result) == 2
        assert any(p.name == "pkg3" for p in result)

    def test_solve_returns_names(self):
        """Test solve method returns names."""
        maximizer = PackageMaximizer(solver="greedy")
        packages = [
            Package(name="pkg1"),
            Package(name="pkg2"),
        ]
        result = maximizer.solve(packages)
        assert isinstance(result, list)
        assert all(isinstance(name, str) for name in result)

    def test_from_names(self):
        """Test from_names static method."""
        packages = PackageMaximizer.from_names(["pkg1", "pkg2", "pkg3"])
        assert len(packages) == 3
        assert all(p.status == "candidate" for p in packages)

    def test_set_solver(self):
        """Test set_solver method."""
        maximizer = PackageMaximizer()
        assert maximizer.solver_type == SolverType.GREEDY

        maximizer.set_solver("z3")
        assert maximizer.solver_type == SolverType.Z3

        maximizer.set_solver(SolverType.PULP)
        assert maximizer.solver_type == SolverType.PULP

    def test_get_solver(self):
        """Test get_solver method."""
        maximizer = PackageMaximizer()
        solver = maximizer.get_solver()
        assert isinstance(solver, GreedySolver)

    def test_get_solver_type(self):
        """Test get_solver_type method."""
        maximizer = PackageMaximizer(solver="z3")
        solver_type = maximizer.get_solver_type()
        assert solver_type == SolverType.Z3

    def test_solve_with_weights(self):
        """Test solve_with_weights method."""
        maximizer = PackageMaximizer(solver="greedy")
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")

        pkg1.conflicts = ["pkg2"]
        pkg2.conflicts = ["pkg1"]

        packages = [pkg1, pkg2, pkg3]
        weights = {"pkg1": 1.0, "pkg2": 2.0, "pkg3": 1.0}

        result = maximizer.solve_with_weights(packages, weights)

        # Should prefer pkg2 (higher weight)
        assert "pkg2" in result
        assert "pkg3" in result

    def test_check_constraints(self):
        """Test check_constraints method."""
        from package_maximizer.core.package import PackageConstraint

        maximizer = PackageMaximizer()
        packages = [
            Package(name="pkg1", version="1.0"),
            Package(name="pkg2", version="2.0"),
        ]

        constraints = [
            PackageConstraint(package="pkg1", op=">=", version="0.5"),
            PackageConstraint(package="pkg2", op=">=", version="3.0"),
        ]

        result = maximizer.check_constraints(packages, constraints)
        assert result["pkg1"] is True
        assert result["pkg2"] is False


class TestPackageMaximizerIntegration:
    """Integration tests for PackageMaximizer with different solvers."""

    @pytest.mark.parametrize("solver_name", ["greedy", "z3"])
    def test_all_solvers_no_conflicts(self, solver_name):
        """Test all solvers with no conflicts."""
        maximizer = PackageMaximizer(solver=solver_name)
        packages = [Package(name=f"pkg{i}") for i in range(10)]
        result = maximizer.solve(packages)
        assert len(result) == 10

    @pytest.mark.parametrize("solver_name", ["greedy", "z3"])
    def test_all_solvers_with_conflicts(self, solver_name):
        """Test all solvers with conflicts."""
        maximizer = PackageMaximizer(solver=solver_name)

        # Create packages with conflicts
        packages = []
        for i in range(10):
            pkg = Package(name=f"pkg{i}")
            # Every even package conflicts with the next odd package
            if i % 2 == 0 and i < 9:
                pkg.conflicts = [f"pkg{i+1}"]
            packages.append(pkg)

        result = maximizer.solve(packages)

        # Should select at least 5 packages (every other one)
        assert len(result) >= 5

        # Check no conflicting packages are both selected
        for pkg in packages:
            if pkg.name in result:
                for conflict in pkg.conflicts:
                    assert (
                        conflict not in result
                    ), f"Both {pkg.name} and {conflict} selected"
