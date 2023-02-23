"""Contains sub parsers for the CLI"""

from argparse import Action, ArgumentParser, Namespace, _SubParsersAction
from typing import Any, Optional, Sequence, Union
import logging

logger = logging.getLogger(__name__)


class ConvertParser:
    """
    This class represents the convert subparser
    """

    @classmethod
    def build_parser(cls, parser: ArgumentParser) -> None:
        """
        Builds the convert subparser

        Args:
            parser (ArgumentParser): The parser to add the subparser to
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
            default="",
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
            parser (ArgumentParser): The parser to add the subparser to
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
