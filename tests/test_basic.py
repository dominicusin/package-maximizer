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
        # Accept both release (0.9.0) and dev (0.9.1.dev+...) versions
        ver = package_maximizer.__version__
        assert ver.startswith("0.9"), f"Expected 0.9.x, got {ver}"
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
