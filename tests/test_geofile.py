# -*- coding: utf-8 -*-
"""
Created on 2022-12-12 06:55:05-05:00
===============================================================================
@filename:  test_geofile.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   Unit tests for the geofile.py module.
===============================================================================
"""
# pylint: disable=missing-function-docstring,redefined-outer-name
# pylint: disable=protected-access

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudtile.geofile import FlatGeobuf, GeoFile, PMTiles, VectorFile


@pytest.fixture(scope="session")
def vectorfile() -> VectorFile:
    return VectorFile(fpath_str="tests/test.parquet")


@pytest.fixture(scope="function")
def flatgeobuf() -> FlatGeobuf:
    yield FlatGeobuf(fpath_str="tests/test.fgb")


class TestGeoFile:
    """
    Tests functionality in the GeoFile abstract class.
    """

    @staticmethod
    def test_geofile() -> None:
        with pytest.raises(TypeError):
            GeoFile("")  # pylint: disable=abstract-class-instantiated


class TestVectorFile:
    """
    Tests the VectorFile class.
    """

    @staticmethod
    def test_instantiation() -> None:
        assert VectorFile("tests/test.parquet")

    @staticmethod
    def test_unsupported_file_type() -> None:
        with pytest.raises(ValueError):
            VectorFile("tests/test.shapefile")

    @staticmethod
    def test_file_not_exists() -> None:
        with pytest.raises(FileNotFoundError):
            VectorFile("tests/i-dont-exist.parquet")

    @staticmethod
    def test_suffix_attr(vectorfile: VectorFile) -> None:
        assert vectorfile.suffix == "parquet"

    @staticmethod
    @patch("cloudtile.geofile.S3Storage")
    def test_upload(s3: MagicMock, vectorfile: VectorFile) -> None:
        vectorfile.upload()
        s3.return_value.upload_file.assert_called_with(
            file_path=str(vectorfile.fpath),
            prefix=vectorfile.suffix,
            key_name=vectorfile.fname,
        )

    @staticmethod
    @patch("cloudtile.geofile.copy")
    def test_write(cp: MagicMock, vectorfile: VectorFile) -> None:
        vectorfile.write("tests")
        cp.assert_called_once_with(
            vectorfile.fpath,
            Path("tests").resolve().joinpath(vectorfile.fname),
        )

    @staticmethod
    def test_write_path_not_exists(vectorfile: VectorFile) -> None:
        with pytest.raises(FileNotFoundError):
            vectorfile.write("blablabla")

    @staticmethod
    def test_write_path_not_dir(vectorfile: VectorFile) -> None:
        with pytest.raises(TypeError):
            vectorfile.write("README.md")

    @staticmethod
    def test_remove(vectorfile: VectorFile) -> None:
        with patch("pathlib.Path.unlink") as mock_unlink:
            vectorfile.remove()
            mock_unlink.assert_called_once()

    @staticmethod
    @patch("cloudtile.geofile.S3Storage")
    def test_from_s3(mock_s3: MagicMock) -> None:
        mock_s3.return_value.download_file.return_value = Path(
            "tests/test.parquet"
        )
        vec = VectorFile.from_s3(file_key="test.parquet")
        mock_s3.return_value.download_file.assert_called_once_with(
            file_key="test.parquet", prefix="parquet"
        )
        assert vec.fpath.exists()

    @staticmethod
    @patch("subprocess.run")
    def test_convert(mock_run: MagicMock, vectorfile: VectorFile) -> None:
        result = vectorfile.convert()
        mock_run.assert_called_once_with(
            (
                "ogr2ogr",
                "-f",
                "FlatGeobuf",
                Path("tests/test.fgb"),
                Path("tests/test.parquet"),
                "-progress",
            ),
            check=True,
        )
        assert isinstance(result, FlatGeobuf)
        assert result.fname == "test.fgb"


class TestFlatGeobuf:
    """
    Tests the FlatGeobuf class.
    """

    @staticmethod
    @patch("subprocess.run")
    def test_convert(mock_run: MagicMock, flatgeobuf: FlatGeobuf) -> None:
        result = flatgeobuf.convert(minimum_zoom=5, maximum_zoom=6)
        mock_run.assert_called_once_with(
            [
                "tippecanoe",
                "--force",
                "--read-parallel",
                "--coalesce-densest-as-needed",
                "--simplification=10",
                "--maximum-tile-bytes=2500000",
                "--maximum-tile-features=20000",
                "--no-tile-compression",
                "--minimum-zoom=5",
                "--maximum-zoom=6",
                "-o",
                str(Path("tests/test-5-6.pmtiles")),
                str(Path("tests/test.fgb")),
            ],
            check=True,
        )
        assert isinstance(result, PMTiles)
        assert result.fname == "test-5-6.pmtiles"

    @staticmethod
    def test_convert_no_zoom_levels(flatgeobuf: FlatGeobuf) -> None:
        with pytest.raises(TypeError):
            flatgeobuf.convert()

    @staticmethod
    def test_get_result_fname(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.override_tc_settings(minimum_zoom=5, maximum_zoom=6)
        assert flatgeobuf._get_result_fname() == "test-5-6.pmtiles"


class TestPMTiles:
    """
    Tests for PMTiles class
    """

    @staticmethod
    def test_convert():
        pmtiles = PMTiles("tests/test-5-6.pmtiles")
        with pytest.raises(NotImplementedError):
            pmtiles.convert()
