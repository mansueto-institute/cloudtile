"""Unit tests for the converter module."""
# pylint: disable=missing-function-docstring,redefined-outer-name
# pylint: disable=protected-access

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from cloudtile.converter import Converter
from cloudtile.geofile import FlatGeobuf, GeoFile, PMTiles, VectorFile


@pytest.fixture
def converter() -> Converter:
    converter = Converter("tests/test.parquet", remote=False)
    return converter


def test_instance(converter: Converter) -> None:
    assert converter
    assert isinstance(converter.origin, VectorFile)


def test_bad_origin_type(converter: Converter) -> None:
    with pytest.raises(TypeError):
        converter.origin = "tests/test.fgb"


@pytest.mark.parametrize("remote", [True, False])
def test_convert_vector(remote: bool, converter: Converter) -> None:
    with patch.object(Converter, "origin", MagicMock(spec=VectorFile)):
        converter.remote = remote
        result: MagicMock = MagicMock(name="result")
        converter.origin.convert.return_value = result
        converter.convert()
        converter.origin.convert.assert_called_once()
        if remote:
            result.upload.assert_called_once()
            converter.origin.remove.assert_any_call()
            result.remove.assert_called_once()


@pytest.mark.parametrize("config", [None, "tests/test.toml"])
def test_convert_fgb(converter: Converter, config: Optional[str]) -> None:
    with patch.object(Converter, "origin", MagicMock(spec=FlatGeobuf)):
        result: MagicMock = MagicMock(name="result")
        converter.origin.convert.return_value = result
        converter.convert(min_zoom=1, max_zoom=2, config=config)
        converter.origin.convert.assert_called_once()
        converter.origin.set_zoom_levels.assert_called_once()


@pytest.mark.parametrize("config", [None, "tests/test.toml"])
@pytest.mark.parametrize("remote", [True, False])
def test_single_step_convert_vector(
    converter: Converter, config: Optional[str], remote: bool
) -> None:
    converter.remote = remote
    with patch.object(Converter, "origin", MagicMock(spec=VectorFile)):
        fgb: MagicMock = MagicMock(spec=FlatGeobuf)
        converter.origin.convert.return_value = fgb
        pmt: MagicMock = MagicMock(spec=PMTiles)
        fgb.convert.return_value = pmt
        converter.single_step_convert(min_zoom=1, max_zoom=2, config=config)
        converter.origin.convert.assert_called_once()
        fgb.set_zoom_levels.assert_called_once()
        if remote:
            converter.origin.remove.assert_called_once()
            fgb.remove.assert_called_once()
            pmt.upload.assert_called_once()
            pmt.remove.assert_called_once()

        fgb.convert.return_value = MagicMock(spec=PMTiles)
        fgb.convert.assert_called_once()


@pytest.mark.parametrize("config", [None, "tests/test.toml"])
@pytest.mark.parametrize("remote", [True, False])
def test_single_step_convert_fgb(
    converter: Converter, config: Optional[str], remote: bool
) -> None:
    converter.remote = remote
    with patch.object(Converter, "origin", MagicMock(spec=FlatGeobuf)):
        pmt: MagicMock = MagicMock(spec=PMTiles)
        converter.origin.convert.return_value = pmt
        converter.single_step_convert(min_zoom=1, max_zoom=2, config=config)
        converter.origin.convert.assert_called_once()
        converter.origin.set_zoom_levels.assert_called_once()

        if remote:
            pmt.upload.assert_called_once()
            pmt.remove.assert_called_once()


def test_single_step_bad_origin(converter: Converter) -> None:
    with patch.object(Converter, "origin", MagicMock(spec=PMTiles)):
        with pytest.raises(NotImplementedError):
            converter.single_step_convert()


@pytest.mark.parametrize(
    "origin_str,filetype",
    ((".parquet", VectorFile), (".fgb", FlatGeobuf), (".pmtiles", PMTiles)),
)
@pytest.mark.parametrize("remote", [True, False])
def test_load_file(remote: bool, origin_str: str, filetype: GeoFile) -> None:
    with patch(
        f"cloudtile.converter.{filetype.__name__}", autospec=True
    ) as mock:
        if remote:
            mock.from_s3.return_value = MagicMock(spec=filetype)
        result = Converter.load_file(f"tests/test{origin_str}", remote=remote)
        assert isinstance(result, filetype)
        if remote:
            mock.from_s3.assert_called_once()


@pytest.mark.parametrize("remote", [True, False])
@patch("cloudtile.converter.VectorFile", autospec=True)
def test_load_file_error(mock_vector: MagicMock, remote: bool) -> None:
    if remote:
        mock_vector.from_s3 = MagicMock(side_effect=ValueError)
        with pytest.raises(ValueError):
            Converter.load_file("tests/test.txt", remote=remote)
    else:
        mock_vector.side_effect = FileNotFoundError
        with pytest.raises(FileNotFoundError):
            Converter.load_file("tests/test.txt", remote=remote)
