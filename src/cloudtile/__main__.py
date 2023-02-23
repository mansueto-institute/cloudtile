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
from argparse import Action, ArgumentParser, Namespace, _SubParsersAction
from importlib import metadata
from typing import Any, Optional, Sequence, Union

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

        parser.add_argument(
            "--version",
            "-v",
            help="Display the cloudtile version installed.",
            action="store_true",
        )

        self.parser = parser
        self.args = parser.parse_args(args)

    def main(self):
        """
        Main driver method for the CLI which defines the work done by each
        of the subcommands.
        """
        if self.args.subcommand is None:
            if self.args.version:
                print(f"cloudtile version: {metadata.version('cloudtile')}")
                sys.exit(0)
            else:
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
        elif self.args.subcommand == "convert":
            if self.args.convert_subcommand is None:
                self.convert_parser.print_usage()
                sys.exit()

            if self.args.memory and not self.args.ecs:
                self.parser.error("--memory can only be used with --ecs")
            if self.args.storage and not self.args.ecs:
                self.parser.error("--storage can only be used with --ecs")

            if self.args.ecs:
                try:
                    task = ECSTask(
                        self._get_args_for_ecs(),
                        memory=self.args.memory,
                        storage=self.args.storage,
                    )
                except ValueError as e:
                    self.parser.error(e)
                print(
                    json.dumps(
                        task.run(), sort_keys=True, indent=4, default=str
                    )
                )
            else:
                try:
                    converter = Converter(
                        origin_str=self.args.filename, remote=self.args.s3
                    )

                    if "config" not in self.args:
                        self.args.config = None
                    if "minimum_zoom" not in self.args:
                        self.args.minimum_zoom = None
                    if "maximum_zoom" not in self.args:
                        self.args.maximum_zoom = None
                    if "tc_kwargs" not in self.args:
                        self.args.tc_kwargs = {}
                    if "suffix" not in self.args:
                        self.args.suffix = ""

                    if self.args.convert_subcommand == "single-step":
                        converter.single_step_convert(
                            minimum_zoom=self.args.minimum_zoom,
                            maximum_zoom=self.args.maximum_zoom,
                            config=self.args.config,
                            **self.args.tc_kwargs,
                            suffix=self.args.suffix,
                        )
                    else:
                        converter.convert(
                            minimum_zoom=self.args.minimum_zoom,
                            maximum_zoom=self.args.maximum_zoom,
                            config=self.args.config,
                            **self.args.tc_kwargs,
                            suffix=self.args.suffix,
                        )
                except ValueError as e:
                    self.parser.error(e)
                except FileNotFoundError as e:
                    self.parser.error(e)

    def _get_args_for_ecs(self) -> list[str]:
        cli_args: dict = vars(self.args)
        args = []
        for arg, argval in cli_args.items():
            if arg in {"memory", "storage"}:
                continue
            if arg == "tc_kwargs":
                tc_settings = ["--tc-kwargs"]
                for k, v in argval.items():
                    if isinstance(v, bool):
                        tc_settings.append(f"{k}")
                    else:
                        tc_settings.append(f"{k}={v}")
            elif arg == "suffix":
                args.append("--suffix")
                args.append(argval)
            elif not isinstance(argval, bool) and argval is not None:
                args.append(str(argval))
        args.append("--s3")
        args.append(" ".join(tc_settings))
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
        cls._build_fgb2pmtiles(parser=subparsers)
        cls._build_single_step(parser=subparsers)

    @staticmethod
    def _build_vector2fgb(parser: _SubParsersAction) -> None:
        vector2fgb = parser.add_parser(
            name="vector2fgb",
            help="Convert a file using gdal's ogr2ogr",
        )
        ConvertParser._add_std_args(vector2fgb)

    @staticmethod
    def _build_fgb2pmtiles(parser: _SubParsersAction) -> None:
        fgb2pmtiles: ArgumentParser = parser.add_parser(
            name="fgb2pmtiles",
            help="Convert a file using Tippecanoe",
        )
        ConvertParser._add_std_args(fgb2pmtiles)
        ConvertParser._add_fgb_args(fgb2pmtiles)

    @staticmethod
    def _build_single_step(parser: _SubParsersAction) -> None:
        ssparser = parser.add_parser(
            name="single-step",
            help=(
                "Convert a vector file into an pmtile (equivalent to running "
                "vector2fgb -> fgb2pmtiles). You can start from "
                "a vectorfile (i.e. .parquet) OR start from a .fgb file."
            ),
        )
        ConvertParser._add_std_args(ssparser)
        ConvertParser._add_fgb_args(ssparser)

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
        parser.add_argument(
            "--memory",
            help=(
                "Whether to override the 64GB memory limit. Must be only be "
                "used with the --ecs flag. Additionally, the values must be "
                "within the range of [32768, 122880] in increments of 8192."
            ),
            type=int,
        )
        parser.add_argument(
            "--storage",
            help=(
                "Whether to override the 100GB ephemeral storage default. "
                "Must only be used with the --ecs flag. Additionally, values "
                "must be within the range of 20 and 200 (GiBs)"
            ),
            type=int,
        )

    @staticmethod
    def _add_fgb_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            "minimum_zoom",
            type=int,
            help="The minimum zoom level to use in the conversion",
            default=None,
        )
        parser.add_argument(
            "maximum_zoom",
            type=lambda x: int(x) if x != "g" else x,
            help="The maximum zoom level to use in the conversion",
            default=None,
        )
        parser.add_argument(
            "--suffix",
            "-s",
            help=(
                "Add a suffix to the output file. This is useful if you want "
                "to differentiate between different settings for the same "
                "file. For example, passing --suffix=myfile will result in "
                "the file being named myfile-minzoom-maxzoom-myfile.pmtiles"
            ),
            default=""
        )
        parser.add_argument(
            "--config",
            type=str,
            default=None,
            help=(
                "The path to a config file for tippecanoe. If not passed the "
                "default config file is used."
            ),
        )
        parser.add_argument(
            "--tc-kwargs",
            help=(
                "Arguments to pass to tippecanoe. Must be in the form of "
                "key if value is boolean, key=value if value is not boolean. "
                "For example, --tc-kwargs no-tile-size-limit "
                "simplification=10. If you pass --maximum-zoom or "
                "--minimum-zoom to the --tc-kwargs call, then these will "
                "override the ones passed via the CLI"
            ),
            nargs="+",
            action=ParseTCKwargs,
            default={},
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


class ParseTCKwargs(Action):
    """Class to parse the tc-kwargs argument

    The tc-kwargs argument is a list of strings that are passed to tippecanoe
    as CLI options. This class parses the list of strings and converts them
    into a dictionary that can be passed to the TippecanoeSettings class.
    """

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: Optional[Union[str, Sequence[Any]]],
        option_string: Optional[str] = None,
    ) -> None:
        if values is None:
            raise ValueError("No values passed to ParseKwargs")
        setattr(namespace, self.dest, {})
        for value in values:
            if "=" not in value:
                key, value = value, True
            else:
                key, value = map(str.strip, value.split("="))
                if value == "True":
                    value = True
                elif value == "False":
                    value = False
            getattr(namespace, self.dest)[key] = value


def main() -> None:
    """
    Main driver method for the CLI.
    """
    cli = CloudTileCLI()
    cli.main()


if __name__ == "__main__":
    main()
