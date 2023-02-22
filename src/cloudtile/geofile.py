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
# pylint: disable=invalid-name

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Optional

from cloudtile.s3 import S3Storage
from cloudtile.tippecanoe import TippecanoeSettings

logger = logging.getLogger(__name__)


@dataclass
class GeoFile(ABC):
    """
    Represents an instance of a remote geofile.
    """

    fpath_str: InitVar[str] = field(repr=False)
    location: FilePath = field(init=False)

    def __post_init__(self, fpath_str: str):
        self.location = FilePath(fpath_str)
        if "." not in self.target_suffix:
            raise ValueError(
                f"Target suffix {self.target_suffix} must include the dot."
            )

    @property
    @abstractmethod
    def target_suffix(self) -> str:
        """
        The conversion target suffix for the file. For example ".fgb"

        Returns:
            str: The target suffix for the file.
        """

    @property
    def suffix(self) -> str:
        """
        The filename's extension, i.e. the "fgb" in "myfile.fgb"

        Returns:
            str: the file name's suffix.
        """
        return self.fpath.suffix[1:]

    @property
    def fpath(self) -> Path:
        """
        The file's path.

        Returns:
            Path: The file's path.
        """
        return self.location.fpath

    @property
    def fname(self) -> str:
        """
        The file's name.

        Returns:
            str: The file's name.
        """
        return self.location.fname

    @abstractmethod
    def convert(self, **kwargs) -> GeoFile:
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

    def remove(self):
        """
        Removes the local file.
        """
        logger.info("Removing (from local) %s", self)
        self.fpath.unlink()

    @classmethod
    def from_s3(cls, file_key: str, **kwargs) -> GeoFile:
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
        result = cls(str(tmp_path), **kwargs)
        return result


@dataclass
class VectorFile(GeoFile):
    """
    Class that represents a vector file that will be transformed into an fgb
    file via ogr2ogr.
    """

    ALLOWED_SUFFIXES: ClassVar[set[str]] = {"geojson", "gpkg", "parquet"}

    def __post_init__(self, fpath_str: str):
        super().__post_init__(fpath_str)
        if self.suffix not in self.ALLOWED_SUFFIXES:
            error_msg = (
                f"File type {self.suffix} must be in {self.ALLOWED_SUFFIXES}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    @property
    def target_suffix(self) -> str:
        return ".fgb"

    def convert(self, **kwargs) -> FlatGeobuf:
        out_path = self.location.get_output_path(self)
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
        return result


@dataclass
class FlatGeobuf(GeoFile):
    """
    Class that represents a FlatGeobuf file.
    """

    cfg_path: InitVar[Optional[str]] = field(repr=False, default=None)
    tc_override: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self, fpath_str: str, cfg_path: Optional[str] = None):
        super().__post_init__(fpath_str=fpath_str)
        self.tc_settings = TippecanoeSettings(cfg_path=cfg_path)
        self.override_tc_settings(**self.tc_override)

    @property
    def target_suffix(self) -> str:
        return ".pmtiles"

    def override_tc_settings(self, **kwargs) -> None:
        """
        Overrides any settings already set in the TippecanoeSettings object.
        Otherwise the new settings are added.
        """
        if "config" in kwargs:
            kwargs.pop("config")
        self.tc_settings.update(kwargs)

    def convert(self, **kwargs) -> PMTiles:
        if "minimum_zoom" not in kwargs or "maximum_zoom" not in kwargs:
            raise TypeError(
                "minimum_zoom and maximum_zoom must be passed as kwargs."
            )
        min_zoom, max_zoom = kwargs.pop("minimum_zoom"), kwargs.pop(
            "maximum_zoom"
        )

        if "config" in kwargs and kwargs["config"] is not None:
            self.tc_settings = TippecanoeSettings(
                cfg_path=kwargs.pop("config")
            )

        if "minimum-zoom" not in self.tc_settings:
            self.tc_settings["minimum-zoom"] = min_zoom
        if "maximum-zoom" not in self.tc_settings:
            self.tc_settings["maximum-zoom"] = max_zoom

        if "suffix" in kwargs:
            suffix = kwargs.pop("suffix")
        else:
            suffix = ""
        self.override_tc_settings(**kwargs)

        out_path = self.location.get_output_path(
            self,
            self.tc_settings["minimum-zoom"],
            self.tc_settings["maximum-zoom"],
            suffix,
        )
        tip_args: list[str] = ["tippecanoe"]
        tip_args.extend(self.tc_settings.convert_to_list_args())
        tip_args.extend(
            [
                "-o",
                str(out_path),
                str(self.fpath),
            ]
        )
        logger.info("Tippecanoe call: %s", " ".join(tip_args))
        subprocess.run(tip_args, check=True)
        result: PMTiles = PMTiles(str(out_path))
        return result


@dataclass
class PMTiles(GeoFile):
    """
    Class that represents a PMTiles tileset file.
    """

    @property
    def target_suffix(self) -> str:
        return ".pmtiles"

    def convert(self, **kwargs) -> GeoFile:
        raise NotImplementedError("PMTiles conversion is not implemented.")


@dataclass
class FilePath:
    """Represents the location of a GeoFile.

    Raises:
        FileNotFoundError: If the file does not exist.

    Attributes:
        fpath_str (str): The path to the file.
        fname (str): The file name.
    """

    fpath_str: InitVar[str] = field(repr=False)
    fpath: Path = field(init=False)

    def __post_init__(self, fpath_str: str):
        self.fpath = Path(fpath_str)
        if not self.fpath.exists():
            raise FileNotFoundError(f"File {self.fpath} does not exist.")

    @property
    def fname(self) -> str:
        """The name property of the file path."""
        return self.fpath.name

    def get_output_path(self, origin: GeoFile, *args) -> Path:
        """
        Returns the output path for the file.

        Args:
            suffix (str): The suffix to append to the file name. It has to be
                something like .fgb or fgb

        Returns:
            Path: The output path
        """
        args_in_name = "-" + "-".join(str(arg) for arg in args) if args else ""
        new_fname = "".join(
            (self.fpath.stem, args_in_name, origin.target_suffix)
        )
        return self.fpath.parent / new_fname
