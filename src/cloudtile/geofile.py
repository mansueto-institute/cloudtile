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

    def convert(self, **kwargs) -> FlatGeobuf:
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

    cfg_path: InitVar[Optional[str]] = field(repr=False, default=None)
    tc_override: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self, cfg_path: Optional[str] = None):
        super().__post_init__()
        self.tc_settings = TippecanoeSettings(cfg_path=cfg_path)
        self.override_tc_settings(**self.tc_override)

    def override_tc_settings(self, **kwargs) -> None:
        """
        Overrides any settings already set in the TippecanoeSettings object.
        Otherwise the new settings are added.
        """
        self.tc_settings.update(kwargs)

    def convert(self, **kwargs) -> PMTiles:
        try:
            min_zoom, max_zoom = kwargs["minimum_zoom"], kwargs["maximum_zoom"]
        except KeyError as e:
            raise TypeError(
                "minimum_zoom and maximum_zoom must be passed as kwargs."
            ) from e
        if "minimum-zoom" not in self.tc_settings:
            self.tc_settings["minimum-zoom"] = min_zoom
        if "maximum-zoom" not in self.tc_settings:
            self.tc_settings["maximum-zoom"] = max_zoom

        out_path = Path(self.fpath.parent.joinpath(self._get_result_fname()))
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
            (
                fname,
                str(self.tc_settings["minimum-zoom"]),
                str(self.tc_settings["maximum-zoom"]) + ".pmtiles",
            )
        )
        return result


@dataclass
class PMTiles(GeoFile):
    """
    Class that represents a PMTiles tileset file.
    """

    def convert(self, **kwargs) -> GeoFile:
        raise NotImplementedError("PMTiles conversion is not implemented.")
