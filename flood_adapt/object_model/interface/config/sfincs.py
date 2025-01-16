from enum import Enum
from pathlib import Path
from typing import Optional, Union

from pydantic import AfterValidator, BaseModel, Field
from tomli import load as load_toml
from typing_extensions import Annotated

from flood_adapt.object_model.hazard.interface.tide_gauge import (
    TideGaugeModel,
)
from flood_adapt.object_model.interface.config import Cstype
from flood_adapt.object_model.io import unit_system as us


def ensure_ascii(s: str):
    assert s.isascii()
    return s


AsciiStr = Annotated[str, AfterValidator(ensure_ascii)]


class SCSModel(BaseModel):
    """Class describing the accepted input for the variable scs.

    Includes the file with the non-dimensional SCS rainfall curves in the site folder and the SCS rainfall curve type.

    """

    file: str
    type: str


class RiverModel(BaseModel):
    """Model that describes the accepted input for the variable river in Site."""

    name: str
    description: Optional[str] = None
    mean_discharge: us.UnitfulDischarge
    x_coordinate: float
    y_coordinate: float


class ObsPointModel(BaseModel):
    """The accepted input for the variable obs_point in Site.

    obs_points is used to define output locations in the hazard model, which will be plotted in the user interface.
    """

    name: Union[int, AsciiStr]
    description: Optional[str] = ""
    ID: Optional[int] = (
        None  # if the observation station is also a tide gauge, this ID should be the same as for obs_station
    )
    file: Optional[str] = None  # for locally stored data
    lat: float
    lon: float


class FloodFrequencyModel(BaseModel):
    """The accepted input for the variable flood_frequency in Site."""

    flooding_threshold: us.UnitfulLength


class DemModel(BaseModel):
    """The accepted input for the variable dem in Site."""

    filename: str
    units: us.UnitTypesLength


class FloodmapType(str, Enum):
    """The accepted input for the variable floodmap in Site."""

    water_level = "water_level"
    water_depth = "water_depth"


class VerticalReferenceModel(BaseModel):
    """The accepted input for the variable vertical_reference in Site."""

    name: str
    height: us.UnitfulLength


class WaterLevelReferenceModel(BaseModel):
    """The accepted input for the variable water_level in Site."""

    localdatum: VerticalReferenceModel
    msl: VerticalReferenceModel
    other: list[VerticalReferenceModel] = Field(
        default_factory=list
    )  # only for plotting


class CycloneTrackDatabaseModel(BaseModel):
    """The accepted input for the variable cyclone_track_database in Site."""

    file: str


class SlrScenariosModel(BaseModel):
    """The accepted input for the variable slr.scenarios ."""

    file: str
    relative_to_year: int


class SlrModel(BaseModel):
    """The accepted input for the variable slr in Site."""

    vertical_offset: us.UnitfulLength
    scenarios: Optional[SlrScenariosModel] = None


class SfincsConfigModel(BaseModel):
    """The accepted input for the variable sfincs in Site."""

    csname: str
    cstype: Cstype
    version: Optional[str] = ""
    offshore_model: Optional[str] = None
    overland_model: str
    floodmap_units: us.UnitTypesLength
    save_simulation: Optional[bool] = False


class SfincsModel(BaseModel):
    config: SfincsConfigModel
    water_level: WaterLevelReferenceModel
    cyclone_track_database: Optional[CycloneTrackDatabaseModel] = None
    slr: SlrModel
    scs: Optional[SCSModel] = None  # optional for the US to use SCS rainfall curves
    dem: DemModel

    flood_frequency: FloodFrequencyModel = FloodFrequencyModel(
        flooding_threshold=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters)
    )
    tide_gauge: Optional[TideGaugeModel] = None
    river: Optional[list[RiverModel]] = None
    obs_point: Optional[list[ObsPointModel]] = None

    @staticmethod
    def read_toml(path: Path) -> "SfincsModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return SfincsModel(**toml_contents)
