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
from pathlib import Path
from typing import Any
from importlib.resources import open_text

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
        s3 = S3Storage()
        s3.upload_file(
            file_path=str(self.fpath), prefix=self.suffix, key_name=self.fname
        )

    def remove(self):
        """
        Removes the local file.
        """
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
        fpath = Path(file_key)
        s3 = S3Storage()
        tmp_path = s3.download_file(file_key=file_key, prefix=fpath.suffix[1:])
        result = cls(str(tmp_path))
        result.fname = file_key
        return result


@dataclass
class GeoPackage(GeoFile):
    """
    Class that represents a geopackage file.
    """

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
        result.fname = result.fname.replace(".gpkg", ".fgb")
        return result


@dataclass
class FlatGeobuf(GeoFile):
    """
    Class that represents a FlatGeobuf file.
    """

    _min_zoom: int = field(init=False, repr=False)
    _max_zoom: int = field(init=False, repr=False)

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

        out_path = Path(
            self.fpath.parent.joinpath(self.fpath.stem + ".mbtiles")
        )
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
        result = MBTiles(str(out_path), self.min_zoom, self.max_zoom)
        result.fname = self.fname
        result.fname = result.fname.replace(".fgb", ".mbtiles")
        return result

    def _get_fname_w_zooms(self) -> Path:
        # TODO: gets a new filename with the current zoom levels set.
        pass

    @staticmethod
    def _read_config() -> dict[str, Any]:
        """
        Parses a .yaml config file for Tippecanoe.

        Returns:
            dict[str, Any]: A flat dictionary with the uncommented settings in
                the .yaml file.
        """
        with open_text("cloudtile", "tiles_config.yaml") as f:
            config_dict: dict = yaml.safe_load(f)

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

    min_zoom: int
    max_zoom: int

    def convert(self):
        pass
