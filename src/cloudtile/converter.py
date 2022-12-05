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
from cloudtile.geofile import FlatGeobuf, VectorFile, MBTiles


def convert(origin_str: str, remote: bool = False, **kwargs) -> None:
    """
    Converts a file from one type to another and uploads the result into S3.

    Args:
        origin_str (str): The file name or path, depending on the remote
            option.
        remote (bool, optional): Whether to download the file from S3 instead
            of using a local path. Defaults to False.
    """
    if origin_str.endswith(".fgb"):
        if remote:
            origin = FlatGeobuf.from_s3(file_key=origin_str)
        else:
            origin = FlatGeobuf(fpath_str=origin_str)

        if isinstance(origin, FlatGeobuf):
            origin.set_zoom_levels(**kwargs)
    elif origin_str.endswith(".mbtiles"):
        if remote:
            origin = MBTiles.from_s3(file_key=origin_str)
        else:
            origin = MBTiles(fpath_str=origin_str)
    else:
        if remote:
            origin = VectorFile.from_s3(file_key=origin_str)
        else:
            origin = VectorFile(fpath_str=origin_str)

    result = origin.convert()
    result.upload()

    if remote:
        origin.remove()
    result.remove()


def main():
    convert("blocks_SLE-8-11.mbtiles", remote=True)
