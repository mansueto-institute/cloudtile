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
    def test_min_zoom(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.min_zoom = 1
        assert flatgeobuf.min_zoom == 1

    @staticmethod
    def test_min_zoom_setter_with_max(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.max_zoom = 2
        flatgeobuf.min_zoom = 1
        assert flatgeobuf.min_zoom == 1

    @staticmethod
    def test_min_zoom_setter_bad_value(flatgeobuf: FlatGeobuf) -> None:
        with pytest.raises(ValueError):
            flatgeobuf.min_zoom = 0

    @staticmethod
    def test_min_zoom_setter_bad_value_max(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.max_zoom = 2
        with pytest.raises(ValueError):
            flatgeobuf.min_zoom = 3

    @staticmethod
    def test_max_zoom(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.max_zoom = 2
        assert flatgeobuf.max_zoom == 2

    @staticmethod
    def test_max_zoom_with_min(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.min_zoom = 1
        flatgeobuf.max_zoom = 2
        assert flatgeobuf.max_zoom == 2

    @staticmethod
    def test_max_zoom_setter_bad_value(flatgeobuf: FlatGeobuf) -> None:
        with pytest.raises(ValueError):
            flatgeobuf.max_zoom = 0

    @staticmethod
    def test_max_zoom_stter_bad_value_min(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.min_zoom = 2
        with pytest.raises(ValueError):
            flatgeobuf.max_zoom = 1

    @staticmethod
    def test_cfg_path(flatgeobuf: FlatGeobuf) -> None:
        assert flatgeobuf.cfg_path is None

    @staticmethod
    def test_cfg_path_setter(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.cfg_path = "src/cloudtile/tiles_config.yaml"
        assert (
            flatgeobuf.cfg_path
            == Path("src/cloudtile/tiles_config.yaml").resolve()
        )

    @staticmethod
    def test_cfg_path_setter_no_exists(flatgeobuf: FlatGeobuf) -> None:
        with pytest.raises(FileNotFoundError):
            flatgeobuf.cfg_path = "src/cloudtile/tiles_config_no_exists.yaml"

    @staticmethod
    def test_set_zoom_levels(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.set_zoom_levels(1, 2)
        assert flatgeobuf.min_zoom == 1
        assert flatgeobuf.max_zoom == 2

    @staticmethod
    def test_set_zoom_levels_bad_value(flatgeobuf: FlatGeobuf) -> None:
        with pytest.raises(ValueError):
            flatgeobuf.set_zoom_levels(2, 1)

    @staticmethod
    @patch("subprocess.run")
    def test_convert(mock_run: MagicMock, flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.set_zoom_levels(5, 6)
        result = flatgeobuf.convert()
        mock_run.assert_called_once_with(
            [
                "tippecanoe",
                "--read-parallel",
                "--coalesce-densest-as-needed",
                "--coalesce-smallest-as-needed",
                "--simplification=10",
                "--maximum-tile-bytes=2500000",
                "--maximum-tile-features=20000",
                "--force",
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
        with pytest.raises(AttributeError):
            flatgeobuf.convert()

    @staticmethod
    def test_get_result_fname(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.set_zoom_levels(5, 6)
        assert flatgeobuf._get_result_fname() == "test-5-6.pmtiles"

    @staticmethod
    def test_read_config(flatgeobuf: FlatGeobuf) -> None:
        flatgeobuf.cfg_path = "src/cloudtile/tiles_config.yaml"
        cfg = flatgeobuf._read_config()
        assert cfg == {
            "read-parallel": True,
            "coalesce-densest-as-needed": True,
            "coalesce-smallest-as-needed": True,
            "simplification": 10,
            "maximum-tile-bytes": 2500000,
            "maximum-tile-features": 20000,
            "force": True,
        }

    @staticmethod
    def test_convert_to_list_args(flatgeobuf: FlatGeobuf) -> None:
        cfg = flatgeobuf._read_config()
        arglist = flatgeobuf._convert_to_list_args(cfg)
        assert arglist == [
            "--read-parallel",
            "--coalesce-densest-as-needed",
            "--coalesce-smallest-as-needed",
            "--simplification=10",
            "--maximum-tile-bytes=2500000",
            "--maximum-tile-features=20000",
            "--force",
        ]


class TestPMTiles:
    """
    Tests for PMTiles class
    """

    @staticmethod
    def test_convert():
        pmtiles = PMTiles("tests/test-5-6.pmtiles")
        with pytest.raises(NotImplementedError):
            pmtiles.convert()
