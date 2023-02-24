"""Unit tests for the CLI module."""

# pylint: disable=import-outside-toplevel,missing-function-docstring
# pylint: disable=unused-import,redefined-outer-name,protected-access

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudtile.__main__ import main
from cloudtile.cli import CloudTileCLI
from cloudtile.geofile import GeoFile


def test_cli_main(capsys):
    cli = CloudTileCLI(args=[])
    cli.main()
    captured = capsys.readouterr()
    assert "usage" in captured.out


@patch("cloudtile.__main__.CloudTileCLI")
def test_pkg_main(mock_cli: MagicMock):
    main()
    mock_cli.return_value.main.assert_called_once()


class TestCLIMain:
    """Tests for the main method of the CLI class."""

    def test_version_flag(self, capsys):
        cli = CloudTileCLI(args=["--version"])
        cli.main()
        captured = capsys.readouterr()
        assert "version" in captured.out


class TestManageSubcommand:
    """Tests for the manage subcommand of the CLI class."""

    def test_manage_subcommand_empty(self, capsys):
        cli = CloudTileCLI(args=["manage"])
        cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.out

    def test_manage_subcommand_upload_empty(self, capsys):
        with pytest.raises(SystemExit):
            cli = CloudTileCLI(args=["manage", "upload"])
            cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.err

    @patch("cloudtile.cli.Converter", spec=True)
    def test_manage_subcommand_upload(self, mock_converter: MagicMock):
        args = ["manage", "upload", "test.txt"]
        cli = CloudTileCLI(args=args)
        origin = MagicMock(spec=GeoFile)
        mock_converter.load_file.return_value = origin
        cli.main()
        mock_converter.load_file.assert_called_once_with(
            origin_str="test.txt", remote=False
        )
        origin.upload.assert_called_once()

    @patch("cloudtile.cli.Converter", spec=True)
    def test_manage_subcommand_download(self, mock_converter: MagicMock):
        args = ["manage", "download", "test.txt", "."]
        cli = CloudTileCLI(args=args)
        cli.main()
        mock_converter.load_file.assert_called_once_with(
            origin_str="test.txt", remote=True
        )


class TestConvertSubcommand:
    """Tests for the convert subcommand of the CLI class."""

    def test_convert_subcommand_empty(self, capsys):
        with pytest.raises(SystemExit):
            cli = CloudTileCLI(args=["convert"])
            cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.out

    def test_convert_memory_without_ecs(self, capsys):
        with pytest.raises(SystemExit):
            cli = CloudTileCLI(
                args=[
                    "convert",
                    "single-step",
                    "test.parquet",
                    "4",
                    "5",
                    "--memory",
                    "1024",
                ]
            )
            cli.main()
        captured = capsys.readouterr()
        assert "--memory can only be used with --ecs" in captured.err

    def test_convert_storage_without_ecs(self, capsys):
        with pytest.raises(SystemExit):
            cli = CloudTileCLI(
                args=[
                    "convert",
                    "single-step",
                    "test.parquet",
                    "4",
                    "5",
                    "--storage",
                    "1024",
                ]
            )
            cli.main()
        captured = capsys.readouterr()
        assert "--storage can only be used with --ecs" in captured.err

    @patch("cloudtile.cli.ECSTask", spec=True)
    def test_convert_with_ecs(self, mock_ecs: MagicMock):
        cli = CloudTileCLI(
            args=["convert", "single-step", "test.parquet", "4", "5", "--ecs"]
        )
        cli.main()
        mock_ecs.assert_called_once()
        mock_ecs.return_value.run.assert_called_once()

    def test_convert_with_ecs_bad_memory(self, capsys):
        with pytest.raises(SystemExit):
            cli = CloudTileCLI(
                args=[
                    "convert",
                    "single-step",
                    "--ecs",
                    "test.parquet",
                    "4",
                    "5",
                    "--memory",
                    "42",
                ]
            )
            cli.main()
        captured = capsys.readouterr()
        assert "memory must be between" in captured.err

    @patch("cloudtile.cli.Converter", spec=True)
    def test_convert_single_step(self, mock_converter: MagicMock):
        cli = CloudTileCLI(
            args=["convert", "single-step", "test.parquet", "4", "5"]
        )
        cli.main()
        mock_instance = mock_converter.return_value
        mock_instance.single_step_convert.assert_called_once_with(
            minimum_zoom=4, maximum_zoom=5, config=None, suffix=""
        )

    @patch("cloudtile.cli.Converter", spec=True)
    def test_convert_vector_no_config(self, mock_converter: MagicMock):
        cli = CloudTileCLI(args=["convert", "vector2fgb", "test.parquet"])
        cli.main()
        mock_instance = mock_converter.return_value
        mock_instance.convert.assert_called_once_with(
            minimum_zoom=None, maximum_zoom=None, config=None, suffix=""
        )

    @patch("cloudtile.geofile.FilePath", autospec=True)
    def test_convert_bad_zooms(self, mock_fp: MagicMock, capsys):
        mock_fp.return_value.fpath = Path("tests/test.parquet")
        with pytest.raises(SystemExit):
            cli = CloudTileCLI(
                args=["convert", "fgb2pmtiles", "test.fgb", "9", "4"]
            )
            cli.main()
        captured = capsys.readouterr()
        assert "Maximum zoom cannot be less than minimum zoom" in captured.err

    def test_convert_file_not_found(self, capsys):
        with pytest.raises(SystemExit):
            cli = CloudTileCLI(
                args=["convert", "fgb2pmtiles", "test.fgb", "4", "9"]
            )
            cli.main()
        captured = capsys.readouterr()
        assert "File test.fgb does not exist" in captured.err


@patch("cloudtile.cli.ECSTask", MagicMock())
@pytest.mark.parametrize(
    "args,expected",
    (
        [
            [
                "convert",
                "single-step",
                "test.parquet",
                "4",
                "5",
                "--ecs",
                "--memory=1024",
                "--tc-kwargs",
                "force=False",
                "visalingam=True",
                "maximum-zoom=g",
            ],
            [
                "convert",
                "single-step",
                "test.parquet",
                "4",
                "5",
                "--s3",
                "--tc-kwargs visalingam maximum-zoom=g",
            ],
        ],
        [
            [
                "convert",
                "single-step",
                "test.parquet",
                "4",
                "5",
                "--ecs",
                "--memory=1024",
                "--suffix=test",
                "--tc-kwargs",
                "force=False",
                "visalingam=True",
                "maximum-zoom=g",
            ],
            [
                "convert",
                "single-step",
                "test.parquet",
                "4",
                "5",
                "--suffix",
                "test",
                "--s3",
                "--tc-kwargs visalingam maximum-zoom=g",
            ],
        ],
    ),
)
def test_get_args_for_ecs(args: list[str], expected: list[str]) -> None:
    cli = CloudTileCLI(args=args)
    actual = cli._get_args_for_ecs()
    assert actual == expected
