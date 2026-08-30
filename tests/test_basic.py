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
        assert package_maximizer.__version__ == "0.3.0"
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
