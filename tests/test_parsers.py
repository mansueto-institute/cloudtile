"""Unit tests for the parsers module."""

# pylint: disable=missing-function-docstring,redefined-outer-name
# pylint: disable=protected-access

from argparse import ArgumentParser, _SubParsersAction
from typing import Generator, Union
from unittest.mock import MagicMock, patch

import pytest

from cloudtile.cli.parsers import ConvertParser, ManageParser, ParseTCKwargs


@pytest.fixture
def parser() -> Generator[ArgumentParser, None, None]:
    parser = ArgumentParser()
    yield parser
    parser = ArgumentParser()


class TestConvertParser:
    """Unit tests for the ConvertParser class"""

    @pytest.fixture
    def subparser(
        self, parser: ArgumentParser
    ) -> Generator[_SubParsersAction, None, None]:
        subparsers = parser.add_subparsers(
            dest="convert_subcommand",
            help="The different conversion types supported",
            metavar="conversions",
        )
        yield subparsers

    @patch.object(ConvertParser, "_build_vector2fgb", MagicMock())
    @patch.object(ConvertParser, "_build_fgb2pmtiles", MagicMock())
    @patch.object(ConvertParser, "_build_single_step", MagicMock())
    def test_build_parser(self, parser: ArgumentParser) -> None:
        ConvertParser.build_parser(parser)
        ConvertParser._build_vector2fgb.assert_called_once_with(
            parser=parser._subparsers._group_actions[0]  # type: ignore
        )
        ConvertParser._build_fgb2pmtiles.assert_called_once_with(
            parser=parser._subparsers._group_actions[0]  # type: ignore
        )
        ConvertParser._build_single_step.assert_called_once_with(
            parser=parser._subparsers._group_actions[0]  # type: ignore
        )

    @patch.object(ConvertParser, "_add_std_args", MagicMock())
    @patch("cloudtile.cli.parsers._SubParsersAction.add_parser")
    def test_build_vector2fgb(
        self, add_parser: MagicMock, subparser: _SubParsersAction
    ) -> None:
        vector2fgb = MagicMock(name="vector2fgb")
        add_parser.return_value = vector2fgb
        ConvertParser._build_vector2fgb(parser=subparser)
        add_parser.assert_called_once_with(
            name="vector2fgb",
            help="Convert a file using gdal's ogr2ogr",
        )
        ConvertParser._add_std_args.assert_called_once_with(vector2fgb)

    @patch.object(ConvertParser, "_add_std_args", MagicMock())
    @patch.object(ConvertParser, "_add_fgb_args", MagicMock())
    @patch("cloudtile.cli.parsers._SubParsersAction.add_parser")
    def test_build_fgb2pmtiles(
        self, add_parser: MagicMock, subparser: _SubParsersAction
    ) -> None:
        fgb2pmtiles = MagicMock(name="fgb2pmtiles")
        add_parser.return_value = fgb2pmtiles
        ConvertParser._build_fgb2pmtiles(parser=subparser)
        add_parser.assert_called_once_with(
            name="fgb2pmtiles",
            help="Convert a file using Tippecanoe",
        )
        ConvertParser._add_std_args.assert_called_once_with(fgb2pmtiles)
        ConvertParser._add_fgb_args.assert_called_once_with(fgb2pmtiles)

    @patch.object(ConvertParser, "_add_std_args", MagicMock())
    @patch.object(ConvertParser, "_add_fgb_args", MagicMock())
    @patch("cloudtile.cli.parsers._SubParsersAction.add_parser")
    def test_build_single_step(
        self, add_parser: MagicMock, subparser: _SubParsersAction
    ) -> None:
        ssparser = MagicMock(name="single_step")
        add_parser.return_value = ssparser
        ConvertParser._build_single_step(parser=subparser)
        ConvertParser._add_std_args.assert_called_once_with(ssparser)
        ConvertParser._add_fgb_args.assert_called_once_with(ssparser)

    @patch("cloudtile.cli.parsers.ArgumentParser", spec=ArgumentParser)
    def test_add_std_args(self, mock_parser: MagicMock) -> None:
        mock_exc_group = MagicMock(name="mutually_exclusive_group")
        mock_parser.add_mutually_exclusive_group.return_value = mock_exc_group
        ConvertParser._add_std_args(parser=mock_parser)
        assert mock_parser.add_argument.call_count == 3
        assert mock_exc_group.add_argument.call_count == 2

    @patch("cloudtile.cli.parsers.ArgumentParser", spec=ArgumentParser)
    def test_add_fgb_args(self, mock_parser: MagicMock) -> None:
        ConvertParser._add_fgb_args(parser=mock_parser)
        assert mock_parser.add_argument.call_count == 5

    @pytest.mark.parametrize("expected,value", [(5, "5"), ("g", "g")])
    def test_parse_maximum_zoom(
        self,
        expected: Union[str, int],
        value: Union[str, int],
    ) -> None:
        assert ConvertParser._parse_maximum_zoom(value) == expected


class TestManageParser:
    """Unit tests for the ManageParser class"""

    @patch.object(ManageParser, "_build_upload_parser", MagicMock())
    @patch.object(ManageParser, "_build_download_parser", MagicMock())
    def test_build_parser(self, parser: ArgumentParser) -> None:
        ManageParser.build_parser(parser)
        ManageParser._build_upload_parser.assert_called_once_with(
            parser=parser._subparsers._group_actions[0]  # type: ignore
        )
        ManageParser._build_download_parser.assert_called_once_with(
            parser=parser._subparsers._group_actions[0]  # type: ignore
        )

    @patch("cloudtile.cli.parsers._SubParsersAction", spec=_SubParsersAction)
    def test_build_upload_parser(self, parser: MagicMock) -> None:
        subparser = MagicMock(spec=ArgumentParser)
        parser.add_parser.return_value = subparser
        ManageParser._build_upload_parser(parser=parser)
        parser.add_parser.assert_called_once()
        subparser.add_argument.assert_called_once()

    @patch("cloudtile.cli.parsers._SubParsersAction", spec=_SubParsersAction)
    def test_build_download_parser(self, parser: MagicMock) -> None:
        subparser = MagicMock(spec=ArgumentParser)
        parser.add_parser.return_value = subparser
        ManageParser._build_download_parser(parser=parser)
        parser.add_parser.assert_called_once()
        assert subparser.add_argument.call_count == 2


class TestParseTCKwargs:
    """Unit tests for the ParseTCKwargs class"""

    @pytest.mark.parametrize(
        "expected,actual",
        [
            ({"name": "test"}, "name=test"),
            ({"boolean": True}, "boolean"),
            ({"boolean": False}, "boolean=False"),
            ({"boolean": True}, "boolean=True"),
        ],
    )
    def test_call(self, expected: dict, actual: str) -> None:
        parser = ArgumentParser()
        parser.add_argument("--tc-kwargs", action=ParseTCKwargs, nargs="+")
        args = parser.parse_args(["--tc-kwargs", actual])
        assert args.tc_kwargs == expected
