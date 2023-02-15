"""Unit tests for the tippecanoe module."""
# pylint: disable=missing-function-docstring,redefined-outer-name
# pylint: disable=protected-access

from typing import Optional, Union

import pytest

from cloudtile.tippecanoe import TippecanoeSettings


@pytest.fixture()
def tc_settings() -> TippecanoeSettings:
    tc = TippecanoeSettings()
    yield tc
    tc = TippecanoeSettings()


@pytest.mark.parametrize("cfg_path", [None, "src/cloudtile/tippecanoe.yaml"])
def test_instantiation_kwargs(cfg_path: Optional[str]) -> None:
    tc = TippecanoeSettings(
        cfg_path=cfg_path, force=False, read_parallel=False
    )
    assert tc["force"] is False
    assert tc["read-parallel"] is False
    assert tc["coalesce-densest-as-needed"] is True  # default


def test_instantiation_bad_cfg_path() -> None:
    with pytest.raises(FileNotFoundError):
        TippecanoeSettings(cfg_path="bad/path/to/config.yaml")


def test_insantiation_empty_yaml() -> None:
    with pytest.raises(ValueError):
        TippecanoeSettings(cfg_path="tests/test.yaml")


def test_set_bad_key(tc_settings: TippecanoeSettings) -> None:
    with pytest.raises(KeyError):
        tc_settings["bad-key"] = True


def test_repr(tc_settings: TippecanoeSettings) -> None:
    expected = {k: v for k, v in tc_settings.items()}
    assert repr(tc_settings) == f"TippecanoeSettings({expected})"


def test_zooms_bad_min_first(tc_settings: TippecanoeSettings) -> None:
    min_zoom = 7
    max_zoom = 3
    with pytest.raises(ValueError):
        tc_settings["minimum-zoom"] = min_zoom
        tc_settings["maximum-zoom"] = max_zoom


def test_zooms_bad_max_first(tc_settings: TippecanoeSettings) -> None:
    min_zoom = 7
    max_zoom = 3
    with pytest.raises(ValueError):
        tc_settings["maximum-zoom"] = max_zoom
        tc_settings["minimum-zoom"] = min_zoom


@pytest.mark.parametrize("min_zoom,max_zoom", [(4, 5), (4, "g")])
def test_zooms_good_max_first(
    min_zoom: int, max_zoom: Union[str, int], tc_settings: TippecanoeSettings
) -> None:
    tc_settings["maximum-zoom"] = max_zoom
    tc_settings["minimum-zoom"] = min_zoom
    assert tc_settings["minimum-zoom"] == min_zoom
    assert tc_settings["maximum-zoom"] == max_zoom


def test_read_config() -> None:
    cfg = TippecanoeSettings._read_yaml_config("src/cloudtile/tippecanoe.yaml")
    assert cfg == {
        "read-parallel": True,
        "coalesce-densest-as-needed": True,
        "simplification": 10,
        "maximum-tile-bytes": 2500000,
        "maximum-tile-features": 20000,
        "no-tile-compression": True,
        "force": True,
    }


def test_convert_to_list_args(tc_settings: TippecanoeSettings) -> None:
    arglist = tc_settings.convert_to_list_args()
    assert arglist == [
        "--force",
        "--read-parallel",
        "--coalesce-densest-as-needed",
        "--simplification=10",
        "--maximum-tile-bytes=2500000",
        "--maximum-tile-features=20000",
        "--no-tile-compression",
    ]


def test_convert_to_list_args_bool_false(
    tc_settings: TippecanoeSettings,
) -> None:
    tc_settings["force"] = False
    arglist = tc_settings.convert_to_list_args()
    assert arglist == [
        "--read-parallel",
        "--coalesce-densest-as-needed",
        "--simplification=10",
        "--maximum-tile-bytes=2500000",
        "--maximum-tile-features=20000",
        "--no-tile-compression",
    ]


def test_override_settings(tc_settings: TippecanoeSettings) -> None:
    tc_settings.override_settings(force=False, simplification=10)
    assert tc_settings["force"] is False
    assert tc_settings["simplification"] == 10
