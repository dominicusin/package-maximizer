"""Regression tests for audit findings."""

from unittest.mock import patch

import pytest

from package_maximizer.adapters import _is_safe_package_name, get_adapter


@pytest.mark.parametrize("manager", ["apt", "pip", "pacman", "npm", "brew"])
@pytest.mark.parametrize(
    "name", ["--registry=http://evil.example", "-h", "foo bar", "", "a\nb"]
)
def test_adapters_refuse_option_like_names(manager, name):
    with patch("package_maximizer.adapters.subprocess.run") as run:
        assert get_adapter(manager).fetch(name) is None
    run.assert_not_called()


@pytest.mark.parametrize(
    "name", ["curl", "@types/node", "python3.11-numpy", "lib++", "g++-12", "x" * 256]
)
def test_safe_names_accepted(name):
    assert _is_safe_package_name(name)


def test_overlong_name_rejected():
    assert not _is_safe_package_name("x" * 257)
