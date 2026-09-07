"""
Tests for RealRepoIntegration.get_transaction_history.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from package_maximizer.integrations.real_repo_integration import (
    RealRepoIntegration,
)


def test_get_transaction_history_unknown_manager():
    """get_transaction_history returns empty list for unknown manager."""
    integration = RealRepoIntegration(package_manager="unknown")
    history = integration.get_transaction_history(limit=10)
    assert history == []


def test_get_transaction_history_apt():
    """get_transaction_history parses APT dpkg log format."""
    integration = RealRepoIntegration(package_manager="apt")
    mock_output = (
        "2024-01-15 10:30:00 install pkg1:amd64 < 1.0\n"
        "2024-01-15 10:31:00 remove pkg2:amd64 < 1.0\n"
        "2024-01-15 10:32:00 upgrade pkg3:amd64 < 1.0\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        history = integration.get_transaction_history(limit=20)

    assert len(history) == 3
    assert history[0]["operation"] == "install"
    assert history[0]["package"] == "pkg1:amd64"
    assert history[1]["operation"] == "remove"
    assert history[2]["operation"] == "upgrade"


def test_get_transaction_history_pacman():
    """get_transaction_history parses Pacman log format."""
    integration = RealRepoIntegration(package_manager="pacman")
    mock_output = (
        "[2024-01-15 10:30] [ALPM] installed pkg1 (1.0-1)\n"
        "[2024-01-15 10:31] [ALPM] removed pkg2 (1.0-1)\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        history = integration.get_transaction_history(limit=20)

    assert len(history) == 2
    assert history[0]["operation"] == "install"
    assert history[1]["operation"] == "remove"


def test_get_transaction_history_dnf():
    """get_transaction_history parses DNF history format."""
    integration = RealRepoIntegration(package_manager="dnf")
    mock_output = (
        "2024-01-15 10:30 install pkg1-1.0\n2024-01-15 10:31 remove pkg2-2.0\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        history = integration.get_transaction_history(limit=20)

    assert len(history) == 2
    assert history[0]["operation"] == "install"
    assert history[1]["operation"] == "remove"


def test_get_transaction_history_brew():
    """get_transaction_history parses Brew log format."""
    integration = RealRepoIntegration(package_manager="brew")
    mock_output = "install pkg1 1.0\nremove pkg2 2.0\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        history = integration.get_transaction_history(limit=20)

    assert len(history) == 2
    assert history[0]["operation"] == "install"


def test_get_transaction_history_file_not_found():
    """get_transaction_history handles FileNotFoundError gracefully."""
    integration = RealRepoIntegration(package_manager="apt")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("log file not found")
        history = integration.get_transaction_history(limit=10)

    assert history == []


def test_get_transaction_history_timeout():
    """get_transaction_history handles TimeoutExpired gracefully."""
    import subprocess

    integration = RealRepoIntegration(package_manager="apt")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="tail", timeout=30)
        history = integration.get_transaction_history(limit=10)

    assert history == []
