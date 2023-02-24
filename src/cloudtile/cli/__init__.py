"""This module contains the CLI for the cloudtile package."""

import json
import logging
import sys
from argparse import ArgumentParser
from importlib import metadata
from typing import Optional

from cloudtile.cli.parsers import ConvertParser, ManageParser
from cloudtile.converter import Converter
from cloudtile.ecs import ECSTask

logger = logging.getLogger(__name__)


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
            else:
                self.manage_parser.print_help()
        elif self.args.subcommand == "convert":  # pragma: no cover
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
                        if v:
                            tc_settings.append(f"{k}")
                    else:
                        tc_settings.append(f"{k}={v}")
            elif arg == "suffix":
                if argval != "":
                    args.append("--suffix")
                    args.append(argval)
            elif not isinstance(argval, bool) and argval is not None:
                args.append(str(argval))
        args.append("--s3")
        args.append(" ".join(tc_settings))
        return args
