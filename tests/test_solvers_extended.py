"""
Extended tests for solvers (MaxSAT, MiniSat)
"""

import pytest
from package_maximizer.core.package import Package
from package_maximizer.solvers import MaxSatSolver, MiniSatSolver


class TestMaxSatSolver:
    """Tests for MaxSAT solver"""

    def test_empty_input(self):
        """Test with empty input"""
        solver = MaxSatSolver()
        result = solver.solve([])
        assert result == []

    def test_single_package(self):
        """Test with single package"""
        pkg1 = Package(name="pkg1")
        solver = MaxSatSolver()
        result = solver.solve([pkg1])
        
        assert len(result) == 1
        assert "pkg1" in result

    def test_no_conflicts(self):
        """Test with packages that have no conflicts"""
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")
        
        solver = MaxSatSolver()
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # All packages should be selected
        assert len(result) == 3
        assert "pkg1" in result
        assert "pkg2" in result
        assert "pkg3" in result

    def test_with_conflicts(self):
        """Test with packages that have conflicts"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3")
        
        solver = MaxSatSolver()
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # Only pkg3 should be selected, or one of pkg1/pkg2
        assert len(result) >= 1
        assert not ("pkg1" in result and "pkg2" in result)

    def test_complex_conflicts(self):
        """Test with complex conflict graph"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2", "pkg3"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3", conflicts=["pkg1"])
        pkg4 = Package(name="pkg4")
        pkg5 = Package(name="pkg5")
        
        solver = MaxSatSolver()
        result = solver.solve([pkg1, pkg2, pkg3, pkg4, pkg5])
        
        # pkg1 conflicts with pkg2 and pkg3, so only one of them can be selected
        # pkg4 and pkg5 have no conflicts, so they should both be selected
        assert "pkg4" in result
        assert "pkg5" in result

        # pkg1 conflicts with pkg2 AND pkg3, so pkg1 cannot coexist with
        # either of them. pkg2 and pkg3 do NOT conflict with each other,
        # so both may be selected together.
        if "pkg1" in result:
            assert "pkg2" not in result
            assert "pkg3" not in result

    def test_solve_with_weights(self):
        """Test solve with weights"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3")
        
        solver = MaxSatSolver()
        weights = {"pkg1": 10.0, "pkg2": 1.0, "pkg3": 5.0}
        
        result = solver.solve_with_weights([pkg1, pkg2, pkg3], weights)
        
        # With these weights, pkg1 (10) and pkg3 (5) should be preferred over pkg2 (1)
        assert len(result) >= 2
        if "pkg1" in result:
            assert "pkg2" not in result


class TestMiniSatSolver:
    """Tests for MiniSat solver"""

    def test_empty_input(self):
        """Test with empty input"""
        solver = MiniSatSolver()
        result = solver.solve([])
        assert result == []

    def test_single_package(self):
        """Test with single package"""
        pkg1 = Package(name="pkg1")
        solver = MiniSatSolver()
        result = solver.solve([pkg1])
        
        assert len(result) == 1
        assert "pkg1" in result

    def test_no_conflicts(self):
        """Test with packages that have no conflicts"""
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")
        
        solver = MiniSatSolver()
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # All packages should be selected
        assert len(result) == 3
        assert "pkg1" in result
        assert "pkg2" in result
        assert "pkg3" in result

    def test_with_conflicts(self):
        """Test with packages that have conflicts"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3")
        
        solver = MiniSatSolver()
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # Only pkg3 should be selected, or one of pkg1/pkg2
        assert len(result) >= 1
        assert not ("pkg1" in result and "pkg2" in result)

    def test_complex_conflicts(self):
        """Test with complex conflict graph"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2", "pkg3"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3", conflicts=["pkg1"])
        pkg4 = Package(name="pkg4")
        pkg5 = Package(name="pkg5")
        
        solver = MiniSatSolver()
        result = solver.solve([pkg1, pkg2, pkg3, pkg4, pkg5])
        
        # pkg4 and pkg5 have no conflicts, so they should both be selected
        assert "pkg4" in result
        assert "pkg5" in result

    def test_solve_with_weights(self):
        """Test solve with weights"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3")
        
        solver = MiniSatSolver()
        weights = {"pkg1": 10.0, "pkg2": 1.0, "pkg3": 5.0}
        
        result = solver.solve_with_weights([pkg1, pkg2, pkg3], weights)
        
        # With these weights, pkg1 (10) and pkg3 (5) should be preferred over pkg2 (1)
        assert len(result) >= 2

    def test_different_solver_names(self):
        """Test with different solver names"""
        solver = MiniSatSolver(solver_name='g3')  # Glucose3
        result = solver.solve([Package(name="pkg1")])
        assert "pkg1" in result


class TestSolverRegistryExtended:
    """Tests for extended solver registry"""

    def test_get_solver_maxsat(self):
        """Test getting MaxSAT solver"""
        from package_maximizer.solvers import get_solver
        solver = get_solver("maxsat")
        assert isinstance(solver, MaxSatSolver)

    def test_get_solver_minisat(self):
        """Test getting MiniSat solver"""
        from package_maximizer.solvers import get_solver
        solver = get_solver("minisat")
        assert isinstance(solver, MiniSatSolver)

    def test_get_solver_case_insensitive_extended(self):
        """Test case insensitive solver lookup for extended solvers"""
        from package_maximizer.solvers import get_solver
        
        solver1 = get_solver("MAXSAT")
        solver2 = get_solver("MiniSat")
        
        assert isinstance(solver1, MaxSatSolver)
        assert isinstance(solver2, MiniSatSolver)

    def test_get_solver_invalid_extended(self):
        """Test getting invalid solver"""
        from package_maximizer.solvers import get_solver
        
        with pytest.raises(ValueError) as exc_info:
            get_solver("invalid_solver")
        
        assert "not found" in str(exc_info.value)
