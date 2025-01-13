import os
from abc import ABC, abstractmethod
from enum import Enum
from os.path import join
from pathlib import Path
from typing import Any, Dict, Literal, Union

import tomli
import tomli_w
from floodadapt.flood_adapt.object_model.interface.config.fiat import FiatModel
from floodadapt.flood_adapt.object_model.interface.config.gui import GuiModel
from floodadapt.flood_adapt.object_model.interface.config.sfincs import SfincsModel
from pydantic import BaseModel


class Cstype(str, Enum):
    """The accepted input for the variable cstype in Site."""

    projected = "projected"
    spherical = "spherical"


class SiteModel(BaseModel):
    """The expected variables and data types of attributes of the Site class."""

    name: str
    description: str = ""
    lat: float
    lon: float

    gui: GuiModel
    sfincs: SfincsModel
    fiat: FiatModel


class SiteConfigModel(BaseModel):
    name: str
    description: str = ""
    lat: float
    lon: float
    components: Dict[
        Literal["sfincs", "fiat", "gui"], Dict[Literal["config_path"], Path]
    ]

    def load(self) -> SiteModel:
        model_dict = {
            "name": self.name,
            "description": self.description,
            "lat": self.lat,
            "lon": self.lon,
        }
        model_dict["sfincs"] = SfincsModel.read_toml(
            self.components["sfincs"]["config_path"]
        )
        model_dict["gui"] = GuiModel.read_toml(self.components["gui"]["config_path"])
        model_dict["fiat"] = FiatModel.read_toml(self.components["fiat"]["config_path"])

        return SiteModel(**model_dict)


class ISite(ABC):
    _attrs: SiteModel

    @property
    @abstractmethod
    def attrs(self) -> SiteModel:
        """Get the site attributes as a dictionary.

        Returns
        -------
        SiteModel
            Pydantic model with the site attributes
        """
        ...

    @attrs.setter
    @abstractmethod
    def attrs(self, value: SiteModel):
        """Set the site attributes from a dictionary.

        Parameters
        ----------
        value : SiteModel
            Pydantic model with the site attributes
        """
        ...

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Get Site attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """Get Site attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Site attributes to a toml file."""
        ...


class Site(ISite):
    """Class for general variables of the object_model."""

    _attrs: SiteModel

    @property
    def attrs(self) -> SiteModel:
        return self._attrs

    @attrs.setter
    def attrs(self, value: SiteModel):
        self._attrs = value

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Create Site from toml file."""
        obj = Site()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)

        parent_folder = Path(filepath).parent
        for component in toml["components"].values():
            p = Path(component["config_path"])
            if p.is_absolute():
                component["config_path"] = p
            else:
                component["config_path"] = join(parent_folder, p)

        obj.attrs = SiteConfigModel(
            **toml,
        ).load()
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """Create Synthetic from object, e.g. when initialized from GUI."""
        obj = Site()
        obj.attrs = SiteModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]) -> None:
        """Write toml file from model object."""
        parent_folder = Path(filepath).parent
        config_dict = {
            "name": self._attrs.name,
            "description": self._attrs.description,
            "lat": self._attrs.lat,
            "lon": self._attrs.lon,
            "components": {
                "sfincs": {"config_path": "sfincs.toml"},
                "fiat": {"config_path": "fiat.toml"},
                "gui": {"config_path": "gui.toml"},
            },
        }

        with open(filepath, "wb") as f:
            tomli_w.dump(config_dict, f)
        with open(
            parent_folder / config_dict["components"]["sfincs"]["config_path"], "wb"
        ) as f:
            tomli_w.dump(self._attrs.sfincs.model_dump(exclude_none=True), f)
        with open(
            parent_folder / config_dict["components"]["fiat"]["config_path"], "wb"
        ) as f:
            tomli_w.dump(self._attrs.fiat.model_dump(exclude_none=True), f)
        with open(
            parent_folder / config_dict["components"]["gui"]["config_path"], "wb"
        ) as f:
            tomli_w.dump(self._attrs.gui.model_dump(exclude_none=True), f)
