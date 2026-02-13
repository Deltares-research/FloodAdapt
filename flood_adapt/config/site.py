import enum
import os
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseModel, Field

from flood_adapt.config.fiat import FiatModel
from flood_adapt.config.gui import GuiModel
from flood_adapt.config.sfincs import SfincsModel
from flood_adapt.misc.io import read_toml, write_toml


class StandardObjectModel(BaseModel):
    """The accepted input for the variable standard_object in Site."""

    events: list[str] = Field(default_factory=list)
    projections: list[str] = Field(default_factory=list)
    strategies: list[str] = Field(default_factory=list)


class GeoGraphicMode(enum.StrEnum):
    COASTAL = enum.auto()
    INLAND_OUTFLOW = enum.auto()
    INLAND_BND = enum.auto()


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
    geographic_mode: GeoGraphicMode
        The geographic mode of the site, which can be coastal, inland with outflow, or inland with boundary.
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
    geographic_mode: GeoGraphicMode

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
        config_dict = self.model_dump(
            exclude_none=True, exclude={"gui", "sfincs", "fiat"}
        )
        config_dict["components"] = {}

        if self.sfincs is not None:
            config_dict["components"]["sfincs"] = sfincs
            write_toml(
                self.sfincs.model_dump(exclude_none=True), parent_folder / sfincs
            )

        if self.fiat is not None:
            config_dict["components"]["fiat"] = fiat
            write_toml(self.fiat.model_dump(exclude_none=True), parent_folder / fiat)

        if self.gui is not None:
            config_dict["components"]["gui"] = gui
            write_toml(self.gui.model_dump(exclude_none=True), parent_folder / gui)

        write_toml(config_dict, filepath)

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
        model_dict = read_toml(file_path)
        toml_dir = file_path.parent
        if (sfincs_config := model_dict["components"].get("sfincs")) is not None:
            model_dict["sfincs"] = SfincsModel(**read_toml(toml_dir / sfincs_config))

        if (gui_config := model_dict["components"].get("gui")) is not None:
            model_dict["gui"] = GuiModel(**read_toml(toml_dir / gui_config))

        if (fiat_config := model_dict["components"].get("fiat")) is not None:
            model_dict["fiat"] = FiatModel(**read_toml(toml_dir / fiat_config))

        return Site(**model_dict)
