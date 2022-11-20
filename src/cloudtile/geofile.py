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

    @classmethod
    @abstractmethod
    def from_s3(cls, file_key: str) -> GeoFile:
        """
        Downloads the geofile from S3

        Args:
            file_key (str): The S3 file key

        Returns:
            GeoFile: A GeoFile instance.
        """

    @abstractmethod
    def convert(self) -> GeoFile:
        """
        Converts self into the target format and uploads the result into S3.

        Returns:
            GeoFile: Some other subclass of GeoFile.
        """

    @abstractmethod
    def upload(self) -> None:
        """
        Uploads a local file to S3.
        """

    def remove(self):
        """
        Removes the local file.
        """
        self.fpath.unlink()


@dataclass
class GeoPackage(GeoFile):
    """
    Class that represents a geopackage file.
    """

    @classmethod
    def from_s3(cls, file_key: str):
        s3 = S3Storage()
        tmp_path = s3.download_file(file_key=file_key, prefix="gpkg")
        result = cls(str(tmp_path))
        result.fname = file_key
        return result

    def upload(self) -> None:
        s3 = S3Storage()
        s3.upload_file(file_path=self.fname, prefix="gpkg")

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

    @classmethod
    def from_s3(cls, file_key: str):
        s3 = S3Storage()
        tmp_path = s3.download_file(file_key=file_key, prefix="fgb")
        return cls(str(tmp_path))

    def upload(self) -> None:
        s3 = S3Storage()
        s3.upload_file(file_path=self.fname, prefix="fgb")

    def convert(self) -> GeoFile:
        return FlatGeobuf("test.fgb")
