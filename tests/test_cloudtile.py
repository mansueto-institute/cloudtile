# -*- coding: utf-8 -*-
"""
Created on Saturday, 12th November 2022 12:50:58 pm
===============================================================================
@filename:  test_cloudtile.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   tests package level imports
===============================================================================
"""
# pylint: disable=import-outside-toplevel,missing-function-docstring
# pylint: disable=unused-import


def test_import_cloudtile():
    import cloudtile  # noqa: F401


def test_import_cli():
    from cloudtile import __main__  # noqa: F401


def test_import_converter():
    from cloudtile import converter  # noqa: F401


def test_import_ecs():
    from cloudtile import ecs  # noqa: F401


def test_import_geofile():
    from cloudtile import geofile  # noqa: F401


def test_import_s3():
    from cloudtile import s3  # noqa: F401
