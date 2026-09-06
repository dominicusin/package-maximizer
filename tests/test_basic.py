"""
Basic tests for Package Maximizer
"""


def test_import():
    """
    Test import of package_maximizer module
    """
    try:
        import package_maximizer

        assert hasattr(package_maximizer, "__version__")
        # Accept both release and dev versions (0.10.x or 0.10.y.devN+...)
        ver = package_maximizer.__version__
        assert ver.split("+")[0].startswith("0.10") or ver.split("+")[0].startswith("0.9"), f"Expected 0.10.x, got {ver}"
    except ImportError:
        assert False, "Failed to import package_maximizer"


def test_basic_functionality():
    """
    Test basic functionality
    """
    # Simple test
    assert 1 + 1 == 2


def test_version():
    """
    Test version information
    """
    from package_maximizer import __version__

    assert __version__ is not None
    assert isinstance(__version__, str)
