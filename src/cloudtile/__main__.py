"""Main driver for the cloudtile package."""

import logging

from cloudtile.cli import CloudTileCLI

logging.basicConfig(level=logging.INFO)


def main() -> None:
    """
    Main driver method for the CLI.
    """
    cli = CloudTileCLI()
    cli.main()


if __name__ == "__main__":  # pragma: no cover
    main()
