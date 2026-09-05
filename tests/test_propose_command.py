"""Tests for the propose CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from package_maximizer.cli.main import cli


class TestProposeCommand:
    """Tests for the propose command."""

    def test_propose_help(self):
        """Test that propose --help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["propose", "--help"])
        assert result.exit_code == 0
        assert "propose" in result.output.lower()

    def test_propose_no_packages(self):
        """Test propose with no packages."""
        runner = CliRunner()
        result = runner.invoke(cli, ["propose"])
        assert result.exit_code != 0

    def test_propose_with_mock_adapter(self):
        """Test propose with mocked adapter."""
        from package_maximizer.adapters import PackageMetadata

        mock_metadata = PackageMetadata(
            name="requests",
            version="2.31.0",
            depends=["certifi", "charset-normalizer"],
            conflicts=[],
        )

        mock_adapter = MagicMock()
        mock_adapter.fetch.return_value = mock_metadata

        runner = CliRunner()
        with patch("package_maximizer.adapters.get_adapter", return_value=mock_adapter):
            result = runner.invoke(
                cli,
                [
                    "propose",
                    "requests",
                    "--manager",
                    "pip",
                    "--solver",
                    "greedy",
                ],
            )

        assert result.exit_code == 0
        assert "requests" in result.output
        mock_adapter.fetch.assert_called_once_with("requests")

    def test_propose_with_explain(self):
        """Test propose with --explain flag."""
        from package_maximizer.adapters import PackageMetadata

        mock_metadata = PackageMetadata(
            name="nginx",
            version="1.24.0",
            depends=["libc6"],
            conflicts=["apache2"],
        )

        mock_adapter = MagicMock()
        mock_adapter.fetch.return_value = mock_metadata

        runner = CliRunner()
        with patch("package_maximizer.adapters.get_adapter", return_value=mock_adapter):
            result = runner.invoke(
                cli,
                [
                    "propose",
                    "nginx",
                    "apache2",
                    "--manager",
                    "apt",
                    "--solver",
                    "greedy",
                    "--explain",
                ],
            )

        assert result.exit_code == 0
        assert "nginx" in result.output

    def test_propose_json_output(self):
        """Test propose with JSON output."""
        from package_maximizer.adapters import PackageMetadata

        mock_metadata = PackageMetadata(
            name="certifi",
            version="2023.7.22",
            depends=[],
            conflicts=[],
        )

        mock_adapter = MagicMock()
        mock_adapter.fetch.return_value = mock_metadata

        runner = CliRunner()
        with patch("package_maximizer.adapters.get_adapter", return_value=mock_adapter):
            result = runner.invoke(
                cli,
                [
                    "propose",
                    "certifi",
                    "--manager",
                    "pip",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0
        assert "certifi" in result.output

    def test_propose_metadata_not_found(self):
        """Test propose when metadata is not found."""
        mock_adapter = MagicMock()
        mock_adapter.fetch.return_value = None

        runner = CliRunner()
        with patch("package_maximizer.adapters.get_adapter", return_value=mock_adapter):
            result = runner.invoke(
                cli,
                [
                    "propose",
                    "nonexistent-package-xyz",
                    "--manager",
                    "pip",
                ],
            )

        assert result.exit_code == 0
        assert "не найдены" in result.output or "not found" in result.output.lower()

    def test_propose_invalid_manager(self):
        """Test propose with invalid manager."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "propose",
                "requests",
                "--manager",
                "invalid_manager_xyz",
            ],
        )
        assert result.exit_code != 0

    def test_propose_multiple_packages(self):
        """Test propose with multiple packages."""
        from package_maximizer.adapters import PackageMetadata

        def fetch_side_effect(name):
            return PackageMetadata(
                name=name,
                version="1.0.0",
                depends=[],
                conflicts=[],
            )

        mock_adapter = MagicMock()
        mock_adapter.fetch.side_effect = fetch_side_effect

        runner = CliRunner()
        with patch("package_maximizer.adapters.get_adapter", return_value=mock_adapter):
            result = runner.invoke(
                cli,
                [
                    "propose",
                    "requests",
                    "certifi",
                    "urllib3",
                    "--manager",
                    "pip",
                ],
            )

        assert result.exit_code == 0
        assert mock_adapter.fetch.call_count == 3
