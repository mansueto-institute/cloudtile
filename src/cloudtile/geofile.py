# -*- coding: utf-8 -*-
"""
Created on Wednesday, 31st December 1969 7:00:00 pm
===============================================================================
@fpath_str:  geofile.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   Conversion between file formats.
===============================================================================
"""

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from importlib.resources import open_text
from pathlib import Path
from shutil import copy
from typing import Any, ClassVar, Optional

import yaml

from cloudtile.s3 import S3Storage

logger = logging.getLogger(__name__)


@dataclass
class GeoFile(ABC):
    """
    Represents an instance of a remote geofile.
    """

    fpath_str: str = field(repr=False)
    fpath: Path = field(init=False)
    fname: str = field(init=False)

    def __post_init__(self):
        fpath = Path(self.fpath_str)
        if not fpath.exists():
            raise FileNotFoundError(f"{fpath} not found")
        self.fpath = fpath
        self.fname = self.fpath.name

    @property
    def suffix(self) -> str:
        """
        The filename's extension, i.e. the "fgb" in "myfile.fgb"

        Returns:
            str: the file name's suffix.
        """
        return self.fpath.suffix[1:]

    @abstractmethod
    def convert(self) -> GeoFile:
        """
        Converts self into the target format and uploads the result into S3.

        Returns:
            GeoFile: Some other subclass of GeoFile.
        """

    def upload(self) -> None:
        """
        Uploads a local file to S3.
        """
        logger.info("Uploading file %s", self)
        s3 = S3Storage()
        s3.upload_file(
            file_path=str(self.fpath), prefix=self.suffix, key_name=self.fname
        )

    def write(self, path_str: str) -> None:
        """
        Writes the file to a local directory passed in.

        Args:
            path_str (str): The directory where in to save the file. The name
                is not passed, as it is a property of the file itself.

        Raises:
            FileNotFoundError: If the directory is not found.
            TypeError: If the path points to something that is not a directory.
        """
        path = Path(path_str).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Folder {path} does not exist.")
        if not path.is_dir():
            raise TypeError(f"{path} is not a directory.")
        logger.info("Writing %s to %s", self, path.joinpath(self.fname))
        copy(self.fpath, path.joinpath(self.fname))

    def remove(self):
        """
        Removes the local file.
        """
        logger.info("Removing (from local) %s", self)
        self.fpath.unlink()

    @classmethod
    def from_s3(cls, file_key: str) -> GeoFile:
        """
        Downloads the geofile from S3

        Args:
            file_key (str): The S3 file key

        Returns:
            GeoFile: A GeoFile instance.
        """
        logger.info("Downloading %s from S3", file_key)
        fpath = Path(file_key)
        s3 = S3Storage()
        tmp_path = s3.download_file(file_key=file_key, prefix=fpath.suffix[1:])
        result = cls(str(tmp_path))
        result.fname = file_key
        return result


@dataclass
class VectorFile(GeoFile):
    """
    Class that represents a vector file that will be transformed into an fgb
    file via ogr2ogr.
    """

    ALLOWED_SUFFIXES: ClassVar[set[str]] = {"geojson", "gpkg", "parquet"}

    def __post_init__(self):
        super().__post_init__()
        if self.suffix not in self.ALLOWED_SUFFIXES:
            error_msg = (
                f"File type {self.suffix} must be in {self.ALLOWED_SUFFIXES}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def convert(self) -> FlatGeobuf:
        out_path = Path(self.fpath.parent.joinpath(self.fpath.stem + ".fgb"))
        ogr_args = (
            "ogr2ogr",
            "-f",
            "FlatGeobuf",
            out_path,
            self.fpath,
            "-progress",
        )
        subprocess.run(ogr_args, check=True)
        result = FlatGeobuf(str(out_path))
        result.fname = self.fname
        result.fname = result.fname.replace(
            "".join((".", self.suffix)), ".fgb"
        )
        return result


@dataclass
class FlatGeobuf(GeoFile):
    """
    Class that represents a FlatGeobuf file.
    """

    _min_zoom: int = field(init=False, repr=False)
    _max_zoom: int = field(init=False, repr=False)
    _cfg_path: Optional[Path] = field(init=False, repr=False, default=None)

    @property
    def min_zoom(self) -> int:
        """
        Sets the zoom level used by Tippecanoe.

        Returns:
            int: The minimum zoom level.
        """
        return self._min_zoom

    @min_zoom.setter
    def min_zoom(self, value: int) -> None:
        if hasattr(self, "max_zoom"):
            if value >= self.max_zoom:
                raise ValueError("min_zoom < max_zoom must be true")
        self._min_zoom = value

    @property
    def max_zoom(self) -> int:
        """
        Sets the zoom level used by Tippecanoe.

        Returns:
            int: The maximum zoom level.
        """
        return self._max_zoom

    @max_zoom.setter
    def max_zoom(self, value: int) -> None:
        if hasattr(self, "min_zoom"):
            if value <= self.min_zoom:
                raise ValueError("min_zoom < max_zoom must be true")
        self._max_zoom = value

    @property
    def cfg_path(self) -> Optional[Path]:
        """
        The config file to use in Tippecanoe. By default it's set to None and
        uses the .yaml file included in the python package.

        Returns:
            Optional[Path]: The path to the yaml file if set, otherwise it's
                None and uses the default.
        """
        return self._cfg_path

    @cfg_path.setter
    def cfg_path(self, path_str: str) -> None:
        """
        Sets a custom tippecanoe configuration file to use when converting.

        Args:
            path_str (str): the absolute or relative path to where the
                tippecanoe .yaml config file is located.
        """
        path = Path(path_str).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file {path} not found")
        logger.info("Using custom Tippecanoe config file from %s", path)
        self._cfg_path = path

    def set_zoom_levels(self, min_zoom: int, max_zoom: int) -> None:
        """
        Sets the minimum and maximum zoom levels used by Tippecanoe.

        Args:
            min_zoom (int): The minimum zoom level.
            max_zoom (int): The maximum zoom level.
        """
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom

    def convert(self) -> MBTiles:
        if not (hasattr(self, "min_zoom") and hasattr(self, "max_zoom")):
            raise AttributeError("Must set zoom levels before converting.")

        out_path = Path(self.fpath.parent.joinpath(self._get_result_fname()))
        tip_args: list[str] = ["tippecanoe"]
        tip_args.extend(self._convert_to_list_args(self._read_config()))
        tip_args.extend(
            [
                f"--minimum-zoom={self.min_zoom}",
                f"--maximum-zoom={self.max_zoom}",
                "-o",
                str(out_path),
                str(self.fpath),
            ]
        )

        subprocess.run(tip_args, check=True)
        result: MBTiles = MBTiles(str(out_path))
        result.fname = self._get_result_fname()
        return result

    def _get_result_fname(self) -> str:
        """
        Transforms the fgb filename into an mbtile filename with the
        conversion zooms in the name.

        Returns:
            str: The result file name
        """
        fname = self.fname
        fname = fname.replace(".fgb", "")
        result = "-".join(
            (fname, str(self.min_zoom), str(self.max_zoom) + ".mbtiles")
        )
        return result

    def _read_config(self) -> dict[str, Any]:
        """
        Parses a .yaml config file for Tippecanoe.

        Returns:
            dict[str, Any]: A flat dictionary with the uncommented settings in
                the .yaml file.
        """
        if self.cfg_path is None:
            with open_text("cloudtile", "tiles_config.yaml") as f:
                config_dict: dict = yaml.safe_load(f)
        else:
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)

        flat_dict = {}
        for v in config_dict.values():
            if v is not None:
                flat_dict.update(v)
        return flat_dict

    @staticmethod
    def _convert_to_list_args(args: dict[str, Any]) -> list[str]:
        """
        Converts a dictionary of Tippecanoe settings into a list of arguments
        that can be pased to the CLI call.

        Args:
            args (dict[str, Any]): Dictionary of Tippecanoe CLI arguments.

        Returns:
            list[str]: List of CLI string arguments to be passed into the CLI.
        """
        result = []
        for k, v in args.items():
            if isinstance(v, bool):
                result.append(f"--{k}")
            else:
                result.append(f"--{k}={v}")
        return result


@dataclass
class MBTiles(GeoFile):
    """
    Class that represents a MBTiles tileset file.
    """

    def convert(self):
        out_path = Path(
            self.fpath.parent.joinpath(self.fpath.stem + ".pmtiles")
        )
        pm_args = (
            "./pmtiles",
            "convert",
            self.fpath,
            out_path,
        )
        subprocess.run(pm_args, check=True)
        result = PMTiles(str(out_path))
        result.fname = self.fname
        result.fname = result.fname.replace(".mbtiles", ".pmtiles")
        return result


@dataclass
class PMTiles(GeoFile):
    """
    Class that represents a PMTiles tileset file.
    """

    def convert(self) -> GeoFile:
        raise NotImplementedError("PMTiles conversion is not implemented.")
