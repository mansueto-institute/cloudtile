"""Unit tests for the CLI module."""
# pylint: disable=import-outside-toplevel,missing-function-docstring
# pylint: disable=unused-import

import pytest

from cloudtile.__main__ import CloudTileCLI


@pytest.fixture
def cli():
    return CloudTileCLI()
