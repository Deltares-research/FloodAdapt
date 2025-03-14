import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal, Union

import tomli
import tomli_w
from pydantic import BaseModel, Field

from flood_adapt.object_model.interface.config.fiat import FiatModel
from flood_adapt.object_model.interface.config.gui import GuiModel
from flood_adapt.object_model.interface.config.sfincs import SfincsModel


class StandardObjectModel(BaseModel):
    """The accepted input for the variable standard_object in Site."""

    events: list[str] = Field(default_factory=list)
    projections: list[str] = Field(default_factory=list)
    strategies: list[str] = Field(default_factory=list)


class SiteModel(BaseModel):
    """The expected variables and data types of attributes of the Site class."""

    name: str
    description: str = ""
    lat: float
    lon: float
    standard_objects: StandardObjectModel = StandardObjectModel()

    gui: GuiModel
    sfincs: SfincsModel
    fiat: FiatModel


class SiteBuilder(BaseModel):
    """Pydantic model that reads the site configuration file and builds the site model.

    Note that the components are not required, as the site may not have all of them.
    Second, note that the components are assumed to be the file names of the component configs, located in the same directory as the site configuration file.
    """

    name: str
    description: str = ""
    lat: float
    lon: float
    components: dict[Literal["sfincs", "fiat", "gui"], str]

    @staticmethod
    def load_file(file_path: Path) -> "SiteModel":
        with open(file_path, "rb") as f:
            model_dict = tomli.load(f)

        toml_dir = file_path.parent
        if (sfincs_config := model_dict["components"].get("sfincs")) is not None:
            model_dict["sfincs"] = SfincsModel.read_toml(toml_dir / sfincs_config)

        if (gui_config := model_dict["components"].get("gui")) is not None:
            model_dict["gui"] = GuiModel.read_toml(toml_dir / gui_config)

        if (fiat_config := model_dict["components"].get("fiat")) is not None:
            model_dict["fiat"] = FiatModel.read_toml(toml_dir / fiat_config)

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
    def load_file(filepath: Union[str, os.PathLike]) -> "ISite":
        """Get Site attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]) -> "ISite":
        """Get Site attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Site attributes to a toml file."""
        ...


class Site(ISite):
    """Class for general variables of the object_model."""

    _attrs: SiteModel

    def __init__(self, site_config: dict[str, Any] | SiteModel):
        if isinstance(site_config, dict):
            self.attrs = SiteModel(**site_config)
        elif isinstance(site_config, SiteModel):
            self.attrs = site_config
        else:
            raise TypeError("site_config must be a dict or SiteModel")

    @property
    def attrs(self) -> SiteModel:
        return self._attrs

    @attrs.setter
    def attrs(self, value: SiteModel):
        self._attrs = value

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> "Site":
        """Create Site from toml file."""
        return Site(SiteBuilder.load_file(Path(filepath)))

    @staticmethod
    def load_dict(data: dict[str, Any]) -> "Site":
        """Create Synthetic from object, e.g. when initialized from GUI."""
        return Site(data)

    def save(
        self,
        filepath: Union[str, os.PathLike],
        sfincs: str = "sfincs.toml",
        fiat: str = "fiat.toml",
        gui: str = "gui.toml",
    ) -> None:
        """Write toml file from model object."""
        parent_folder = Path(filepath).parent
        config_dict = {
            "name": self.attrs.name,
            "description": self.attrs.description,
            "lat": self.attrs.lat,
            "lon": self.attrs.lon,
            "components": {},
        }

        if self.attrs.sfincs is not None:
            config_dict["components"]["sfincs"] = sfincs
            with open(parent_folder / sfincs, "wb") as f:
                tomli_w.dump(self.attrs.sfincs.model_dump(exclude_none=True), f)

        if self.attrs.fiat is not None:
            config_dict["components"]["fiat"] = fiat
            with open(parent_folder / fiat, "wb") as f:
                tomli_w.dump(self.attrs.fiat.model_dump(exclude_none=True), f)

        if self.attrs.gui is not None:
            config_dict["components"]["gui"] = gui
            with open(parent_folder / gui, "wb") as f:
                tomli_w.dump(self.attrs.gui.model_dump(exclude_none=True), f)

        with open(filepath, "wb") as f:
            tomli_w.dump(config_dict, f)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Site):
            return False
        return self.attrs == other.attrs
