# -*- coding: utf-8 -*-
"""
Created on Wednesday, 31st December 1969 7:00:00 pm
===============================================================================
@filename:  converter.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   Convert between file types.
===============================================================================
"""
from cloudtile.geofile import GeoPackage, FlatGeobuf


def convert(origin_str: str, remote: bool = False, **kwargs) -> None:
    """
    Converts a file from one type to another and uploads the result into S3.

    Args:
        origin_str (str): The file name or path, depending on the remote
            option.
        remote (bool, optional): Whether to download the file from S3 instead
            of using a local path. Defaults to False.
    """
    if origin_str.endswith(".gpkg"):
        if remote:
            origin = GeoPackage.from_s3(file_key=origin_str)
        else:
            origin = GeoPackage(fpath_str=origin_str)
    elif origin_str.endswith(".fgb"):
        if remote:
            origin = FlatGeobuf.from_s3(file_key=origin_str)
        else:
            origin = FlatGeobuf(fpath_str=origin_str)

        if isinstance(origin, FlatGeobuf):
            origin.set_zoom_levels(**kwargs)

    result = origin.convert()
    result.upload()

    if remote:
        origin.remove()
    result.remove()
