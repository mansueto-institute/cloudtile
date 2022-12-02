# -*- coding: utf-8 -*-
"""
Created on Wednesday, 31st December 1969 6:00:00 pm
===============================================================================
@filename:  __main__.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   Main CLI for cloudtile.
===============================================================================
"""
import logging
from argparse import ArgumentParser, _SubParsersAction
from typing import Optional

from cloudtile.converter import convert

logging.basicConfig(level=logging.INFO)


class CloudTileCLI:
    """
    This class represents a CLI instance.
    """

    def __init__(self, args: Optional[list[str]] = None) -> None:
        parser = ArgumentParser(
            description="Basic CLI for using the cloudtile package."
        )

        subparsers = parser.add_subparsers(
            dest="subcommand",
            help="The different sub-commands available",
            metavar="subcommands",
        )

        self.manage_parser = subparsers.add_parser(
            name="manage",
            help="Subcommands for managing/uploading files to S3",
        )

        self.convert_parser = subparsers.add_parser(
            name="convert", help="File conversion subcommands"
        )
        ConvertParser.build_parser(self.convert_parser)
        self.parser = parser
        self.args = parser.parse_args(args)

    def main(self):
        print(self.args)
        if self.args.subcommand == "manage":
            raise NotImplementedError("No manage yet")
        elif self.args.subcommand == "convert":
            if self.args.convert_subcommand is None:
                self.convert_parser.print_usage()

            if "min_zoom" not in self.args:
                self.args.min_zoom = None
            if "max_zoom" not in self.args:
                self.args.max_zoom = None

            convert(
                origin_str=self.args.filename,
                remote=self.args.remote,
                min_zoom=self.args.min_zoom,
                max_zoom=self.args.max_zoom,
            )


class ConvertParser:
    """
    This class represents the convert subparser
    """

    @classmethod
    def build_parser(cls, parser: ArgumentParser) -> None:
        """
        Builds the convert subparser

        Args:
            parser (ArgumentParser): _description_

        Returns:
            ArgumentParser: _description_
        """
        subparsers = parser.add_subparsers(
            dest="convert_subcommand",
            help="The different conversion types supported",
            metavar="conversions",
        )
        cls._build_vector2fgb(parser=subparsers)
        cls._build_fgb2mbtiles(parser=subparsers)
        cls._build_mb2pmtiles(parser=subparsers)

    @staticmethod
    def _build_vector2fgb(parser: _SubParsersAction) -> None:
        vector2fgb = parser.add_parser(  # type: ignore
            name="vector2fgb",
            help="Convert a file using gdal's ogr2ogr",
        )
        vector2fgb.add_argument(
            "filename", help="The file name to convert", metavar="filename"
        )
        vector2fgb.add_argument(
            "--remote",
            help="Whether to use a remote file or use S3",
            action="store_true",
        )

    @staticmethod
    def _build_fgb2mbtiles(parser: _SubParsersAction) -> None:
        fgb2mbtiles = parser.add_parser(
            name="fgb2mbtiles",
            help="Convert a file using Tippecanoe",
        )
        fgb2mbtiles.add_argument(
            "filename", help="The file name to convert", metavar="filename"
        )
        fgb2mbtiles.add_argument(
            "min_zoom",
            type=int,
            help="The minimum zoom level to use in the conversion",
        )
        fgb2mbtiles.add_argument(
            "max_zoom",
            type=int,
            help="The maximum zoom level to use in the conversion",
        )
        fgb2mbtiles.add_argument(
            "--remote",
            help="Whether to use a remote file or use S3",
            action="store_true",
        )

    @staticmethod
    def _build_mb2pmtiles(parser: _SubParsersAction) -> None:
        mb2pmtiles = parser.add_parser(
            name="mb2pmtiles",
            help="Convert a file using PMTiles Go executable",
        )
        mb2pmtiles.add_argument(
            "filename", help="The file name to convert", metavar="filename"
        )
        mb2pmtiles.add_argument(
            "--remote",
            help="Whether to use a remote file or use S3",
            action="store_true",
        )


def main() -> None:
    """
    Main driver method for the CLI.
    """
    CloudTileCLI().main()
