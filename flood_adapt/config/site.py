import os
from pathlib import Path
from typing import Union

import tomli
import tomli_w
from pydantic import BaseModel, Field

from flood_adapt.config.fiat import FiatModel
from flood_adapt.config.gui import GuiModel
from flood_adapt.config.hazard import RiverModel
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
            "standard_objects": {
                "events": self.standard_objects.events,
                "projections": self.standard_objects.projections,
                "strategies": self.standard_objects.strategies,
            },
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
        with open(filepath, mode="rb") as fp:
            toml_contents = tomli.load(fp)
        toml_path = Path(filepath)

        return Site(
            name=toml_contents["name"],
            description=toml_contents["description"],
            lat=toml_contents["lat"],
            lon=toml_contents["lon"],
            sfincs=SfincsModel.read_toml(
                toml_path.parent / toml_contents["components"]["sfincs"]
            ),
            fiat=FiatModel.read_toml(
                toml_path.parent / toml_contents["components"]["fiat"]
            ),
            gui=GuiModel.read_toml(
                toml_path.parent / toml_contents["components"]["gui"]
            ),
        )

    def add_river(self, river: RiverModel) -> None:
        """Add a river to the site sfincs model.

        Parameters
        ----------
        river : RiverModel
            River model to add to the site.
        """
        if self.sfincs.river is None:
            self.sfincs.river = []
        self.sfincs.river.append(river)
