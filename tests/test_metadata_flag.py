from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from package_maximizer.cli.main import cli


def test_metadata_flag_loads_depends_via_adapter():
    runner = CliRunner()
    fake_metadata = MagicMock()
    fake_metadata.name = "pkg1"
    fake_metadata.depends = ["dep1"]
    fake_metadata.conflicts = []

    fake_adapter = MagicMock()
    fake_adapter.fetch.return_value = fake_metadata

    with (
        patch("package_maximizer.adapters.get_adapter", return_value=fake_adapter),
        patch("package_maximizer.core.maximizer.PackageMaximizer") as fake_max,
    ):
        fake_max.return_value.solve.return_value = ["pkg1"]
        result = runner.invoke(
            cli,
            ["maximize", "pkg1", "--metadata", "--manager", "apt", "--output", "json"],
        )

    assert result.exit_code == 0, result.output
    assert "Загружены метаданные" in result.output


def test_metadata_flag_warns_without_adapter():
    runner = CliRunner()
    with (
        patch("package_maximizer.adapters.get_adapter", return_value=None),
        patch("package_maximizer.core.maximizer.PackageMaximizer") as fake_max,
    ):
        fake_max.return_value.solve.return_value = ["pkg1"]
        result = runner.invoke(
            cli,
            ["maximize", "pkg1", "--metadata", "--manager", "apt", "--output", "json"],
        )

    assert result.exit_code == 0, result.output
    assert "нет адаптера метаданных" in result.output


def test_metadata_flag_merges_depends_and_conflicts():
    runner = CliRunner()
    fake_metadata = MagicMock()
    fake_metadata.name = "pkg1"
    fake_metadata.depends = ["dep1", "dep2"]
    fake_metadata.conflicts = ["conf1"]

    fake_adapter = MagicMock()
    fake_adapter.fetch.return_value = fake_metadata

    with (
        patch("package_maximizer.adapters.get_adapter", return_value=fake_adapter),
        patch("package_maximizer.core.maximizer.PackageMaximizer") as fake_max,
    ):
        fake_pkg = MagicMock()
        fake_pkg.depends = []
        fake_pkg.conflicts = []
        fake_max.return_value.solve.return_value = ["pkg1"]
        result = runner.invoke(
            cli,
            [
                "maximize",
                "pkg1",
                "--metadata",
                "--manager",
                "apt",
                "-d",
                "existing_dep",
                "-c",
                "existing_conf",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Загружены метаданные" in result.output
