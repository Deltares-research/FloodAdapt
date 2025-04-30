import os
from pathlib import Path
from typing import Literal, Union

import tomli
import tomli_w
from pydantic import BaseModel, Field

from flood_adapt.config.fiat import FiatModel
from flood_adapt.config.gui import GuiModel
from flood_adapt.config.sfincs import SfincsModel


class StandardObjectModel(BaseModel):
    """The accepted input for the variable standard_object in Site."""

    events: list[str] = Field(default_factory=list)
    projections: list[str] = Field(default_factory=list)
    strategies: list[str] = Field(default_factory=list)


class Site(BaseModel):
    """The expected variables and data types of attributes of the Site class.

    Attributes
    ----------
    name : str
        Name of the site.
    description : str
        Description of the site. Defaults to "".
    lat : float
        Latitude of the site.
    lon : float
        Longitude of the site.
    standard_objects : StandardObjectModel, default=StandardObjectModel()
        Standard objects of the site.
    gui : GuiModel
        GUI model of the site.
    sfincs : SfincsModel
        SFincs model of the site.
    fiat : FiatModel
        Fiat model of the site.
    """

    name: str
    description: str = ""
    lat: float
    lon: float
    standard_objects: StandardObjectModel = StandardObjectModel()

    gui: GuiModel
    sfincs: SfincsModel
    fiat: FiatModel

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
            "name": self.name,
            "description": self.description,
            "lat": self.lat,
            "lon": self.lon,
            "components": {},
        }

        if self.sfincs is not None:
            config_dict["components"]["sfincs"] = sfincs
            with open(parent_folder / sfincs, "wb") as f:
                tomli_w.dump(self.sfincs.model_dump(exclude_none=True), f)

        if self.fiat is not None:
            config_dict["components"]["fiat"] = fiat
            with open(parent_folder / fiat, "wb") as f:
                tomli_w.dump(self.fiat.model_dump(exclude_none=True), f)

        if self.gui is not None:
            config_dict["components"]["gui"] = gui
            with open(parent_folder / gui, "wb") as f:
                tomli_w.dump(self.gui.model_dump(exclude_none=True), f)

        with open(filepath, "wb") as f:
            tomli_w.dump(config_dict, f)

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> "Site":
        """Create Site from toml file."""
        return SiteBuilder.load_file(Path(filepath))


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
    def load_file(file_path: Path) -> "Site":
        with open(file_path, "rb") as f:
            model_dict = tomli.load(f)

        toml_dir = file_path.parent
        if (sfincs_config := model_dict["components"].get("sfincs")) is not None:
            model_dict["sfincs"] = SfincsModel.read_toml(toml_dir / sfincs_config)

        if (gui_config := model_dict["components"].get("gui")) is not None:
            model_dict["gui"] = GuiModel.read_toml(toml_dir / gui_config)

        if (fiat_config := model_dict["components"].get("fiat")) is not None:
            model_dict["fiat"] = FiatModel.read_toml(toml_dir / fiat_config)

        return Site(**model_dict)
