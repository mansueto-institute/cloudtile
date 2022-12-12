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
import json
import logging
import sys
from argparse import ArgumentParser, _SubParsersAction
from typing import Optional

from cloudtile.converter import Converter
from cloudtile.ecs import ECSTask

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
        ManageParser.build_parser(self.manage_parser)

        self.convert_parser = subparsers.add_parser(
            name="convert", help="File conversion subcommands"
        )
        ConvertParser.build_parser(self.convert_parser)
        self.parser = parser
        self.args = parser.parse_args(args)

    def main(self):
        """
        Main driver method for the CLI which defines the work done by each
        of the subcommands.
        """
        if self.args.subcommand is None:
            self.parser.print_usage()
        elif self.args.subcommand == "manage":
            if self.args.manage_subcommand == "upload":
                origin = Converter.load_file(
                    origin_str=self.args.filename, remote=False
                )
                origin.upload()
            elif self.args.manage_subcommand == "download":
                origin = Converter.load_file(
                    origin_str=self.args.filename, remote=True
                )
                origin.write(path_str=self.args.directory)
                origin.remove()
        elif self.args.subcommand == "convert":
            if self.args.convert_subcommand is None:
                self.convert_parser.print_usage()
                sys.exit()

            if "min_zoom" not in self.args:
                self.args.min_zoom = None
            if "max_zoom" not in self.args:
                self.args.max_zoom = None

            if self.args.ecs:
                task = ECSTask(self._get_args_for_ecs())
                print(
                    json.dumps(
                        task.run(), sort_keys=True, indent=4, default=str
                    )
                )
                sys.exit(0)

            converter = Converter(
                origin_str=self.args.filename, remote=self.args.s3
            )
            converter.convert(
                min_zoom=self.args.min_zoom, max_zoom=self.args.max_zoom
            )

    def _get_args_for_ecs(self) -> list[str]:
        cli_args: dict = vars(self.args)
        args = []
        for arg in cli_args.values():
            if not isinstance(arg, bool) and arg is not None:
                args.append(str(arg))
        args.append("--s3")
        return args


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
        vector2fgb = parser.add_parser(
            name="vector2fgb",
            help="Convert a file using gdal's ogr2ogr",
        )
        ConvertParser._add_std_args(vector2fgb)

    @staticmethod
    def _build_fgb2mbtiles(parser: _SubParsersAction) -> None:
        fgb2mbtiles = parser.add_parser(
            name="fgb2mbtiles",
            help="Convert a file using Tippecanoe",
        )
        ConvertParser._add_std_args(fgb2mbtiles)
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

    @staticmethod
    def _build_mb2pmtiles(parser: _SubParsersAction) -> None:
        mb2pmtiles = parser.add_parser(
            name="mb2pmtiles",
            help="Convert a file using PMTiles Go executable",
        )
        ConvertParser._add_std_args(mb2pmtiles)

    @staticmethod
    def _add_std_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            "filename", help="The file name to convert", metavar="filename"
        )
        exc_group = parser.add_mutually_exclusive_group()
        exc_group.add_argument(
            "--s3",
            help="Whether to use a remote file or use S3",
            action="store_true",
        )
        exc_group.add_argument(
            "--ecs",
            help="Whether to run the entire job on AWS ECS",
            action="store_true",
        )


class ManageParser:
    """
    This class represents the manage subparser
    """

    @classmethod
    def build_parser(cls, parser: ArgumentParser) -> None:
        """
        Builds the manage subparser

        Args:
            parser (ArgumentParser): _description_

        Returns:
            ArgumentParser: _description_
        """
        subparsers = parser.add_subparsers(
            dest="manage_subcommand",
            help="The management actions available",
            metavar="management",
        )
        cls._build_upload_parser(subparsers)
        cls._build_download_parser(subparsers)

    @staticmethod
    def _build_upload_parser(parser: _SubParsersAction) -> None:
        upload: ArgumentParser = parser.add_parser(
            name="upload",
            help="Uploads a local file to S3",
        )
        upload.add_argument(
            "filename",
            help=(
                "Absolute or relative path to local file that you wish "
                "to upload to S3"
            ),
            metavar="filename",
        )

    @staticmethod
    def _build_download_parser(parser: _SubParsersAction) -> None:
        download: ArgumentParser = parser.add_parser(
            name="download", help="Downloads a file from S3 a local directory."
        )
        download.add_argument(
            "filename",
            help=(
                "Name of the file in S3, something like myfile.parquet or "
                "blocks.fgb"
            ),
        )
        download.add_argument(
            "directory",
            help=(
                "The relative or absolute path to a directory where you want "
                "to download into."
            ),
        )


def main() -> None:
    """
    Main driver method for the CLI.
    """
    cli = CloudTileCLI()
    cli.main()
