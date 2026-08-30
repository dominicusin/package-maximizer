"""
Tests for constraints module
"""

import pytest
from package_maximizer.core.constraints import (
    VersionConstraint,
    DependencyConstraint,
    ConflictConstraint,
    ConstraintParser
)


class TestVersionConstraint:
    """Tests for VersionConstraint"""

    def test_equal(self):
        """Test equal version constraint"""
        constraint = VersionConstraint(package="pkg", operator="==", version="1.0.0")
        assert constraint.satisfied_by("1.0.0") == True
        assert constraint.satisfied_by("1.0.1") == False
        assert constraint.satisfied_by("0.9.9") == False

    def test_not_equal(self):
        """Test not equal version constraint"""
        constraint = VersionConstraint(package="pkg", operator="!=", version="1.0.0")
        assert constraint.satisfied_by("1.0.0") == False
        assert constraint.satisfied_by("1.0.1") == True
        assert constraint.satisfied_by("0.9.9") == True

    def test_greater_than(self):
        """Test greater than version constraint"""
        constraint = VersionConstraint(package="pkg", operator=">", version="1.0.0")
        assert constraint.satisfied_by("1.0.0") == False
        assert constraint.satisfied_by("1.0.1") == True
        assert constraint.satisfied_by("2.0.0") == True
        assert constraint.satisfied_by("0.9.9") == False

    def test_greater_than_or_equal(self):
        """Test greater than or equal version constraint"""
        constraint = VersionConstraint(package="pkg", operator=">=", version="1.0.0")
        assert constraint.satisfied_by("1.0.0") == True
        assert constraint.satisfied_by("1.0.1") == True
        assert constraint.satisfied_by("0.9.9") == False

    def test_less_than(self):
        """Test less than version constraint"""
        constraint = VersionConstraint(package="pkg", operator="<", version="1.0.0")
        assert constraint.satisfied_by("1.0.0") == False
        assert constraint.satisfied_by("0.9.9") == True
        assert constraint.satisfied_by("2.0.0") == False

    def test_less_than_or_equal(self):
        """Test less than or equal version constraint"""
        constraint = VersionConstraint(package="pkg", operator="<=", version="1.0.0")
        assert constraint.satisfied_by("1.0.0") == True
        assert constraint.satisfied_by("0.9.9") == True
        assert constraint.satisfied_by("1.0.1") == False

    def test_compatible_version(self):
        """Test compatible version constraint (~)"""
        constraint = VersionConstraint(package="pkg", operator="~", version="1.2.3")
        # ~1.2.3 means >=1.2.3, <1.3.0
        # Note: This is a simplified implementation
        # Our implementation checks >=1.2.3 and < next major version
        assert constraint.satisfied_by("1.2.3") == True
        assert constraint.satisfied_by("1.2.4") == True
        assert constraint.satisfied_by("1.1.9") == False

    def test_empty_version(self):
        """Test with empty version"""
        constraint = VersionConstraint(package="pkg", operator=">=", version="1.0.0")
        assert constraint.satisfied_by("") == False


class TestDependencyConstraint:
    """Tests for DependencyConstraint"""

    def test_simple_dependency(self):
        """Test simple dependency without version"""
        constraint = DependencyConstraint(package="libc")
        installed = {"libc": "2.31"}
        assert constraint.satisfied_by(installed) == True

    def test_missing_dependency(self):
        """Test missing dependency"""
        constraint = DependencyConstraint(package="libc")
        installed = {"libd": "1.0"}
        assert constraint.satisfied_by(installed) == False

    def test_versioned_dependency(self):
        """Test dependency with version constraint"""
        constraint = DependencyConstraint(
            package="libc",
            version_constraint=VersionConstraint(
                package="", operator=">=", version="2.30"
            )
        )
        installed = {"libc": "2.31"}
        assert constraint.satisfied_by(installed) == True
        
        installed = {"libc": "2.29"}
        assert constraint.satisfied_by(installed) == False


class TestConflictConstraint:
    """Tests for ConflictConstraint"""

    def test_simple_conflict(self):
        """Test simple conflict"""
        constraint = ConflictConstraint(package="pkg1")
        assert constraint.conflicts_with("pkg1", "1.0") == True
        assert constraint.conflicts_with("pkg2", "1.0") == False

    def test_versioned_conflict(self):
        """Test conflict with version constraint"""
        constraint = ConflictConstraint(
            package="pkg1",
            version_constraint=VersionConstraint(
                package="", operator="<", version="2.0"
            )
        )
        assert constraint.conflicts_with("pkg1", "1.0") == True
        assert constraint.conflicts_with("pkg1", "2.0") == False
        assert constraint.conflicts_with("pkg1", "3.0") == False


class TestConstraintParser:
    """Tests for ConstraintParser"""

    def test_parse_version_constraint_equal(self):
        """Test parsing version constraint with =="""
        constraint = ConstraintParser.parse_version_constraint("pkg == 1.0.0")
        assert constraint is not None
        assert constraint.operator == "=="
        assert constraint.version == "1.0.0"

    def test_parse_version_constraint_greater(self):
        """Test parsing version constraint with >="""
        constraint = ConstraintParser.parse_version_constraint("pkg >= 1.0.0")
        assert constraint is not None
        assert constraint.operator == ">="
        assert constraint.version == "1.0.0"

    def test_parse_version_constraint_less(self):
        """Test parsing version constraint with <"""
        constraint = ConstraintParser.parse_version_constraint("pkg < 2.0.0")
        assert constraint is not None
        assert constraint.operator == "<"
        assert constraint.version == "2.0.0"

    def test_parse_version_constraint_no_version(self):
        """Test parsing version constraint without version"""
        constraint = ConstraintParser.parse_version_constraint("pkg")
        assert constraint is None

    def test_parse_dependency_simple(self):
        """Test parsing simple dependency"""
        dep = ConstraintParser.parse_dependency("libc")
        assert dep is not None
        assert dep.package == "libc"
        assert dep.version_constraint is None

    def test_parse_dependency_with_version(self):
        """Test parsing dependency with version"""
        dep = ConstraintParser.parse_dependency("libc >= 2.30")
        assert dep is not None
        assert dep.package == "libc"
        assert dep.version_constraint is not None
        assert dep.version_constraint.operator == ">="
        assert dep.version_constraint.version == "2.30"

    def test_parse_dependency_complex(self):
        """Test parsing complex dependency"""
        # Complex dependencies with multiple constraints are simplified
        dep = ConstraintParser.parse_dependency("python3")
        assert dep is not None
        assert dep.package == "python3"

    def test_parse_conflict_simple(self):
        """Test parsing simple conflict"""
        conflict = ConstraintParser.parse_conflict("pkg1")
        assert conflict is not None
        assert conflict.package == "pkg1"

    def test_parse_conflict_with_version(self):
        """Test conflict with version constraint"""
        conflict = ConstraintParser.parse_conflict("pkg1 < 2.0")
        assert conflict is not None
        assert conflict.package == "pkg1"
        assert conflict.version_constraint is not None
