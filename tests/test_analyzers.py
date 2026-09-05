"""
Tests for analyzers module
"""

import pytest

from package_maximizer.analyzers import ResultAnalyzer


class TestResultAnalyzer:
    """Tests for ResultAnalyzer"""

    def test_analyze_empty(self):
        """Test analysis with empty inputs"""
        analyzer = ResultAnalyzer()
        result = analyzer.analyze([], [])

        assert result["statistics"]["installed_count"] == 0
        assert result["statistics"]["proposed_count"] == 0
        assert result["changes"]["to_install"] == []
        assert result["changes"]["to_remove"] == []

    def test_analyze_no_changes(self):
        """Test analysis with no changes"""
        analyzer = ResultAnalyzer()
        installed = ["pkg1", "pkg2", "pkg3"]
        proposed = ["pkg1", "pkg2", "pkg3"]

        result = analyzer.analyze(installed, proposed)

        assert result["statistics"]["installed_count"] == 3
        assert result["statistics"]["proposed_count"] == 3
        assert result["changes"]["to_install"] == []
        assert result["changes"]["to_remove"] == []
        assert result["changes"]["unchanged"] == ["pkg1", "pkg2", "pkg3"]
        assert result["summary"]["total_changes"] == 0
        assert result["summary"]["net_change"] == 0

    def test_analyze_add_packages(self):
        """Test analysis with packages to add"""
        analyzer = ResultAnalyzer()
        installed = ["pkg1", "pkg2"]
        proposed = ["pkg1", "pkg2", "pkg3", "pkg4"]

        result = analyzer.analyze(installed, proposed)

        assert result["statistics"]["installed_count"] == 2
        assert result["statistics"]["proposed_count"] == 4
        assert set(result["changes"]["to_install"]) == {"pkg3", "pkg4"}
        assert result["changes"]["to_remove"] == []
        assert set(result["changes"]["unchanged"]) == {"pkg1", "pkg2"}
        assert result["summary"]["total_changes"] == 2
        assert result["summary"]["net_change"] == 2

    def test_analyze_remove_packages(self):
        """Test analysis with packages to remove"""
        analyzer = ResultAnalyzer()
        installed = ["pkg1", "pkg2", "pkg3", "pkg4"]
        proposed = ["pkg1", "pkg2"]

        result = analyzer.analyze(installed, proposed)

        assert result["statistics"]["installed_count"] == 4
        assert result["statistics"]["proposed_count"] == 2
        assert result["changes"]["to_install"] == []
        assert set(result["changes"]["to_remove"]) == {"pkg3", "pkg4"}
        assert set(result["changes"]["unchanged"]) == {"pkg1", "pkg2"}
        assert result["summary"]["total_changes"] == 2
        assert result["summary"]["net_change"] == -2

    def test_analyze_mixed_changes(self):
        """Test analysis with mixed changes"""
        analyzer = ResultAnalyzer()
        installed = ["pkg1", "pkg2", "pkg3"]
        proposed = ["pkg1", "pkg4", "pkg5"]

        result = analyzer.analyze(installed, proposed)

        assert result["statistics"]["installed_count"] == 3
        assert result["statistics"]["proposed_count"] == 3
        assert set(result["changes"]["to_install"]) == {"pkg4", "pkg5"}
        assert set(result["changes"]["to_remove"]) == {"pkg2", "pkg3"}
        assert result["changes"]["unchanged"] == ["pkg1"]
        assert result["summary"]["total_changes"] == 4
        assert result["summary"]["net_change"] == 0

    def test_categorize_changes(self):
        """Test change categorization"""
        analyzer = ResultAnalyzer()

        # No changes
        assert analyzer._categorize_changes(0, 0, 10) == "no_changes"

        # Minor changes (< 5%)
        assert analyzer._categorize_changes(1, 0, 100) == "minor"

        # Moderate changes (5-20%)
        assert analyzer._categorize_changes(10, 0, 100) == "moderate"

        # Significant changes (20-50%)
        assert analyzer._categorize_changes(30, 0, 100) == "significant"

        # Major changes (>50%)
        assert analyzer._categorize_changes(60, 0, 100) == "major"

        # Fresh install
        assert analyzer._categorize_changes(5, 0, 0) == "fresh_install"

    def test_compatibility_matrix(self):
        """Test compatibility matrix generation"""
        analyzer = ResultAnalyzer()
        proposed = ["pkg1", "pkg2", "pkg3"]
        conflict_graph = {"pkg1": ["pkg2"], "pkg2": ["pkg1", "pkg3"], "pkg3": ["pkg2"]}

        result = analyzer.get_compatibility_matrix(proposed, conflict_graph)

        assert "matrix" in result
        assert "statistics" in result

        matrix = result["matrix"]
        assert "pkg1" in matrix
        assert "pkg2" in matrix
        assert "pkg3" in matrix

        # Проверяем конфликты
        assert matrix["pkg1"]["pkg2"] == False  # pkg1 conflicts with pkg2
        assert matrix["pkg2"]["pkg1"] == False  # pkg2 conflicts with pkg1
        assert matrix["pkg1"]["pkg3"] == True  # pkg1 compatible with pkg3
        assert matrix["pkg3"]["pkg1"] == True  # pkg3 compatible with pkg1

    def test_dependency_analysis(self):
        """Test dependency analysis"""
        analyzer = ResultAnalyzer()
        proposed = ["pkg1", "pkg2", "pkg3"]
        dependency_graph = {"pkg1": ["pkg2", "pkg3"], "pkg2": ["pkg3"], "pkg3": []}

        result = analyzer.get_dependency_analysis(proposed, dependency_graph)

        assert result["total_dependencies"] == 3  # pkg1->pkg2, pkg1->pkg3, pkg2->pkg3
        assert result["satisfied_dependencies"] == 3  # All deps are in proposed
        assert result["unsatisfied_dependencies"] == 0
        assert result["satisfaction_percentage"] == 100.0

    def test_dependency_analysis_unsatisfied(self):
        """Test dependency analysis with unsatisfied dependencies"""
        analyzer = ResultAnalyzer()
        proposed = ["pkg1", "pkg2"]
        dependency_graph = {
            "pkg1": ["pkg2", "pkg3"],  # pkg3 not in proposed
            "pkg2": [],
        }

        result = analyzer.get_dependency_analysis(proposed, dependency_graph)

        assert result["total_dependencies"] == 2
        assert result["satisfied_dependencies"] == 1  # Only pkg2
        assert result["unsatisfied_dependencies"] == 1  # pkg3
        assert result["satisfaction_percentage"] == 50.0

    def test_compare_solvers(self):
        """Test solver comparison"""
        analyzer = ResultAnalyzer()
        results = {
            "greedy": ["pkg1", "pkg2", "pkg3"],
            "z3": ["pkg1", "pkg2", "pkg4"],
            "pulp": ["pkg1", "pkg3", "pkg4"],
        }

        comparison = analyzer.compare_solvers(results)

        assert "solvers" in comparison
        assert set(comparison["solvers"]) == {"greedy", "z3", "pulp"}
        assert "common_packages" in comparison
        assert "pkg1" in comparison["common_packages"]
        assert "unique_packages" in comparison

    def test_compare_solvers_with_reference(self):
        """Test solver comparison with reference"""
        analyzer = ResultAnalyzer()
        results = {"greedy": ["pkg1", "pkg2", "pkg3"], "z3": ["pkg1", "pkg2", "pkg4"]}
        reference = ["pkg1", "pkg2", "pkg3"]

        comparison = analyzer.compare_solvers(results, reference)

        assert "reference_comparison" in comparison
        ref_comp = comparison["reference_comparison"]

        assert "greedy" in ref_comp
        assert "z3" in ref_comp

        # greedy matches all 3
        assert ref_comp["greedy"]["matches"] == 3
        assert ref_comp["greedy"]["precision"] == 100.0
        assert ref_comp["greedy"]["recall"] == 100.0


class TestAnalyzerRegistry:
    """Tests for analyzer registry"""

    def test_get_analyzer_basic(self):
        """Test getting basic analyzer"""
        from package_maximizer.analyzers import get_analyzer

        analyzer = get_analyzer("basic")
        assert isinstance(analyzer, ResultAnalyzer)

    def test_get_analyzer_case_insensitive(self):
        """Test case insensitive analyzer lookup"""
        from package_maximizer.analyzers import get_analyzer

        analyzer = get_analyzer("BASIC")
        assert isinstance(analyzer, ResultAnalyzer)

    def test_get_analyzer_invalid(self):
        """Test getting invalid analyzer"""
        from package_maximizer.analyzers import get_analyzer

        with pytest.raises(ValueError) as exc_info:
            get_analyzer("invalid")

        assert "not found" in str(exc_info.value)
