"""Module that handles passing settings to the tippecanoe CLI."""
import logging
from collections import UserDict
from dataclasses import dataclass
from importlib.resources import open_text
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass(init=False, repr=False)
class TippecanoeSettings(UserDict):
    """
    A class that represents the settings for the tippecanoe CLI.

    Attributes:
        _all_settings (dict): A dictionary of all the possible settings. Used
            to validate the settings passed in.
    """

    def __init__(self, cfg_path: Optional[str] = None, **kwargs) -> None:
        self._all_settings = self._read_yaml_config(read_all=True)
        super().__init__()
        # here we set the default values from the yaml file
        for k, v in self._read_yaml_config(cfg_path=cfg_path).items():
            self[k] = v
        # here we override the defaults with any kwargs passed in
        for k, v in kwargs.items():
            self[k] = v

    def __repr__(self) -> str:
        data = {k: v for k, v in self.items() if v is not False}
        return f"TippecanoeSettings({data})"

    def __setitem__(self, key: str, value: Any) -> None:
        key = key.replace("_", "-")

        if key not in self._all_settings:
            raise KeyError(f"Setting {key} is not a valid Tippecanoe setting.")

        if key == "maximum-zoom":
            if value != "g":
                if "minimum-zoom" in self and value < self["minimum-zoom"]:
                    raise ValueError(
                        "Maximum zoom cannot be less than minimum zoom."
                    )

        if key == "minimum-zoom":
            if "maximum-zoom" in self and self["maximum-zoom"] != "g":
                if value > self["maximum-zoom"]:
                    raise ValueError(
                        "Minimum zoom cannot be greater than maximum zoom."
                    )

        super().__setitem__(key, value)

    def convert_to_list_args(self) -> list[str]:
        """
        Converts a dictionary of Tippecanoe settings into a list of arguments
        that can be pased to the CLI call.

        Returns:
            list[str]: List of CLI string arguments to be passed into the CLI.
        """
        result = []
        for k, v in self.items():
            if isinstance(v, bool):
                if v:
                    result.append(f"--{k}")
            else:
                result.append(f"--{k}={v}")
        return result

    def override_settings(self, **kwargs) -> None:
        """
        Overrides any settings already set in the TippecanoeSettings object.
        Otherwise the new settings are added.
        """
        for k, v in kwargs.items():
            self[k] = v

    @staticmethod
    def _parse_settings_dict(settings: dict[str, Any]) -> dict[str, Any]:
        flat_dict = {}
        for v in settings.values():
            if isinstance(v, dict):
                flat_dict.update(v)
        return flat_dict

    @staticmethod
    def _read_yaml_config(
        cfg_path: Optional[str] = None, read_all: bool = False
    ) -> dict[str, Any]:

        if cfg_path is None:
            with open_text("cloudtile", "tippecanoe.yaml") as f:
                data: str = f.read()
        else:
            path = Path(cfg_path).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Config file {path} not found")
            logger.info("Using custom Tippecanoe config file from %s", path)
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = f.read()

        if read_all:
            data = data.replace("  # ", "  ")

        config_dict = yaml.safe_load(data)

        if config_dict is None:
            raise ValueError(f"{path} seems to be empty")

        return TippecanoeSettings._parse_settings_dict(config_dict)
