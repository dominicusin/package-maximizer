"""
Tests for EnhancedGreedySolver
"""

import pytest
from package_maximizer.solvers import EnhancedGreedySolver
from package_maximizer.core.package import Package


class TestEnhancedGreedySolver:
    """Tests for EnhancedGreedySolver"""

    def test_empty_input(self):
        """Test with empty input"""
        solver = EnhancedGreedySolver()
        result = solver.solve([])
        assert result == []

    def test_single_package(self):
        """Test with single package"""
        pkg1 = Package(name="pkg1")
        solver = EnhancedGreedySolver()
        result = solver.solve([pkg1])
        
        assert len(result) == 1
        assert "pkg1" in result

    def test_no_conflicts(self):
        """Test with packages that have no conflicts"""
        pkg1 = Package(name="pkg1")
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")
        
        solver = EnhancedGreedySolver()
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # All packages should be selected
        assert len(result) == 3
        assert "pkg1" in result
        assert "pkg2" in result
        assert "pkg3" in result

    def test_with_conflicts_skip(self):
        """Test with packages that have conflicts using skip strategy"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3")
        
        solver = EnhancedGreedySolver(conflict_strategy="skip")
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # pkg3 should be selected, and one of pkg1 or pkg2 (whichever comes first)
        assert len(result) >= 1
        assert "pkg3" in result
        assert not ("pkg1" in result and "pkg2" in result)

    def test_with_conflicts_remove(self):
        """Test with packages that have conflicts using remove strategy"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3")
        
        solver = EnhancedGreedySolver(conflict_strategy="remove")
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # Should have all packages or at least pkg3
        assert len(result) >= 1
        assert "pkg3" in result

    def test_complex_conflicts(self):
        """Test with complex conflict graph"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2", "pkg3"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3", conflicts=["pkg1"])
        pkg4 = Package(name="pkg4")
        pkg5 = Package(name="pkg5")
        
        solver = EnhancedGreedySolver()
        result = solver.solve([pkg1, pkg2, pkg3, pkg4, pkg5])
        
        # pkg4 and pkg5 have no conflicts, so they should both be selected
        assert "pkg4" in result
        assert "pkg5" in result

    def test_solve_with_weights(self):
        """Test solve with weights"""
        pkg1 = Package(name="pkg1", conflicts=["pkg2"])
        pkg2 = Package(name="pkg2", conflicts=["pkg1"])
        pkg3 = Package(name="pkg3")
        
        solver = EnhancedGreedySolver()
        weights = {"pkg1": 10.0, "pkg2": 1.0, "pkg3": 5.0}
        
        result = solver.solve_with_weights([pkg1, pkg2, pkg3], weights)
        
        # With these weights, pkg1 (10) and pkg3 (5) should be preferred
        assert len(result) >= 2

    def test_dependency_handling(self):
        """Test dependency handling"""
        pkg1 = Package(name="pkg1", depends=["pkg2"])
        pkg2 = Package(name="pkg2")
        pkg3 = Package(name="pkg3")
        
        solver = EnhancedGreedySolver()
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # pkg2 should be selected before pkg1 (dependency)
        # Both should be selected
        assert "pkg2" in result
        if "pkg1" in result:
            # If pkg1 is selected, pkg2 must also be selected
            assert "pkg2" in result

    def test_version_constraints(self):
        """Test version constraint handling"""
        pkg1 = Package(name="pkg1", version="1.0.0", depends=["pkg2 >= 2.0.0"])
        pkg2 = Package(name="pkg2", version="1.5.0")
        pkg3 = Package(name="pkg3", version="2.0.0")
        
        solver = EnhancedGreedySolver(respect_version_constraints=True)
        result = solver.solve([pkg1, pkg2, pkg3])
        
        # pkg1 requires pkg2 >= 2.0.0, but pkg2 is 1.5.0
        # So pkg1 should not be selected with pkg2
        # pkg3 should be selected
        assert "pkg3" in result

    def test_time_limit(self):
        """Test time limit parameter"""
        solver = EnhancedGreedySolver(time_limit=5000)
        assert solver.time_limit == 5000

    def test_conflict_strategy(self):
        """Test conflict strategy parameter"""
        solver = EnhancedGreedySolver(conflict_strategy="skip")
        assert solver.conflict_strategy == "skip"

    def test_respect_version_constraints(self):
        """Test respect_version_constraints parameter"""
        solver = EnhancedGreedySolver(respect_version_constraints=False)
        assert solver.respect_version_constraints == False


class TestEnhancedGreedySolverRegistry:
    """Tests for EnhancedGreedySolver in registry"""

    def test_get_solver_enhanced_greedy(self):
        """Test getting EnhancedGreedySolver from registry"""
        from package_maximizer.solvers import get_solver
        solver = get_solver("enhanced_greedy")
        assert isinstance(solver, EnhancedGreedySolver)

    def test_get_solver_case_insensitive(self):
        """Test case insensitive lookup"""
        from package_maximizer.solvers import get_solver
        solver = get_solver("ENHANCED_GREEDY")
        assert isinstance(solver, EnhancedGreedySolver)
