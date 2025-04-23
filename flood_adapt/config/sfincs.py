import math
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from pydantic import AfterValidator, BaseModel, Field, model_validator
from tomli import load as load_toml
from typing_extensions import Annotated

from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.tide_gauge import TideGauge
from flood_adapt.objects.forcing.timeseries import Scstype


def ensure_ascii(s: str):
    assert s.isascii()
    return s


AsciiStr = Annotated[str, AfterValidator(ensure_ascii)]


class Cstype(str, Enum):
    """The accepted input for the variable cstype in Site."""

    projected = "projected"
    spherical = "spherical"


class SCSModel(BaseModel):
    """Class describing the accepted input for the variable scs.

    Includes the file with the non-dimensional SCS rainfall curves in the site folder and the SCS rainfall curve type.

    Attributes
    ----------
    file : str
        The path to the SCS rainfall curves file.
    type : Scstype
        The type of the SCS rainfall curve.
    """

    file: str
    type: Scstype


class RiverModel(BaseModel):
    """Model that describes the accepted input for the variable river in Site.

    Attributes
    ----------
    name : str
        The name of the river.
    description : Optional[str], default=None
        description of the river.
    mean_discharge : us.UnitfulDischarge
        The mean discharge of the river.
    x_coordinate : float
        The x coordinate of the river.
    y_coordinate : float
        The y coordinate of the river.
    """

    name: str
    description: Optional[str] = None
    mean_discharge: us.UnitfulDischarge
    x_coordinate: float
    y_coordinate: float


class ObsPointModel(BaseModel):
    """The accepted input for the variable obs_point in Site.

    obs_points is used to define output locations in the hazard model, which will be plotted in the user interface.

    Attributes
    ----------
    name : Union[int, AsciiStr]
        The name of the observation point.
    description : Optional[str], default=""
        The description of the observation point.
    ID : Optional[int], default=None
        The ID of the observation point.
    file : Optional[str], default=None
        The path to the observation point data file.
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
    """The accepted input for the variable dem in Site.

    Attributes
    ----------
    filename : str
        The path to the digital elevation model file.
    units : us.UnitTypesLength
        The units of the digital elevation model file.
    """

    filename: str
    units: us.UnitTypesLength


class FloodmapType(str, Enum):
    """The accepted input for the variable floodmap in Site."""

    water_level = "water_level"
    water_depth = "water_depth"


class DatumModel(BaseModel):
    """
    The accepted input for the variable datums in WaterlevelReferenceModel.

    Attributes
    ----------
    name : str
        The name of the vertical reference model.
    height : us.UnitfulLength
        The height of the vertical reference model relative to the main reference.
    """

    name: str
    height: us.UnitfulLength


class WaterlevelReferenceModel(BaseModel):
    """The accepted input for the variable water_level in Site.

    Waterlevels timeseries are calculated from user input, assumed to be relative to the `reference` vertical reference model.

    For plotting in the GUI, the `reference` vertical reference model is used as the main zero-reference, all values are relative to this.
    All other vertical reference models are plotted as dashed lines.

    Attributes
    ----------
    reference : str
        The name of the vertical reference model that is used as the main zero-reference.
    datums : list[DatumModel]
        The vertical reference models that are used to calculate the waterlevels timeseries.
        The datums are used to calculate the waterlevels timeseries, which are relative to the `reference` vertical reference model.
    """

    reference: str
    datums: list[DatumModel] = Field(default_factory=list)

    def get_datum(self, name: str) -> DatumModel:
        for datum in self.datums:
            if datum.name == name:
                return datum
        raise ValueError(f"Could not find datum with name {name}")

    @model_validator(mode="after")
    def main_reference_should_be_in_datums_and_eq_zero(self):
        if self.reference not in [datum.name for datum in self.datums]:
            raise ValueError(f"Reference {self.reference} not in {self.datums}")
        if not math.isclose(
            self.get_datum(self.reference).height.value, 0, abs_tol=1e-6
        ):
            raise ValueError(f"Reference {self.reference} height is not zero")
        return self

    @model_validator(mode="after")
    def all_datums_should_have_unique_names(self):
        datum_names = [datum.name for datum in self.datums]
        if len(set(datum_names)) != len(datum_names):
            raise ValueError(f"Duplicate datum names found: {datum_names}")
        return self


class CycloneTrackDatabaseModel(BaseModel):
    """The accepted input for the variable cyclone_track_database in Site.

    Attributes
    ----------
    file : str
        The path to the cyclone track database file.
    """

    file: str


class SlrScenariosModel(BaseModel):
    """The accepted input for the variable slr_scenarios.

    Attributes
    ----------
    file : str
        The path to the sea level rise scenarios file.
    relative_to_year : int
        The year to which the sea level rise scenarios are relative.
    """

    file: str
    relative_to_year: int


class FloodModel(BaseModel):
    """The accepted input for the variable overland_model and offshore_model in Site.

    Attributes
    ----------
    name : str
        The name of the directory in `static/templates/<directory>` that contains the template model files.
    reference : str
        The name of the vertical reference model that is used as the reference datum. Should be defined in water_level.datums.
    vertical_offset : Optional[us.UnitfulLength], default = None
        The vertical offset of the vertical reference model relative to the main reference.
        Given that the height of the vertical reference model is often determined by external sources,
        this vertical offset can be used to correct systematic over-/underestimation of a vertical reference model.
    """

    name: str
    reference: str

    # this used to be water_level_offset from events
    vertical_offset: Optional[us.UnitfulLength] = None


class SfincsConfigModel(BaseModel):
    """The expected variables and data types of attributes of the SfincsConfig class.

    Attributes
    ----------
    csname : str
        The name of the CS model.
    cstype : Cstype
        Cstype of the CS model. must be either "projected" or "spherical".
    version : Optional[str], default = None
        The version of the CS model. If None, the version is not specified.
    offshore_model : Optional[FloodModel], default = None
        The offshore model. If None, the offshore model is not specified.
    overland_model : FloodModel
        The overland model. This is the main model used for the simulation.
    floodmap_units : us.UnitTypesLength
        The units used for the output floodmap. Sfincs always produces in metric units, this is used to convert the floodmap to the correct units.
    save_simulation : Optional[bool], default = False
        Whether to keep or delete the simulation files after the simulation is finished and all output files are created.
        If True, the simulation files are kept. If False, the simulation files are deleted.
    """

    csname: str
    cstype: Cstype
    version: Optional[str] = None
    offshore_model: Optional[FloodModel] = None
    overland_model: FloodModel
    floodmap_units: us.UnitTypesLength
    save_simulation: Optional[bool] = False


class SfincsModel(BaseModel):
    """The expected variables and data types of attributes of the Sfincs class.

    Attributes
    ----------
    config : SfincsConfigModel
        The configuration of the Sfincs model.
    water_level : WaterlevelReferenceModel
        The collection of all datums and the main reference datum.
    dem : DemModel
        The digital elevation model.
    flood_frequency : FloodFrequencyModel, default = FloodFrequencyModel()
        The flood frequency model.
    slr : SlrScenariosModel
        Specification of the sea level rise scenarios.
    cyclone_track_database : CycloneTrackDatabaseModel, optional, default = None
        The cyclone track database model.
    scs : SCSModel, optional, default = None
        The SCS model.
    tide_gauge : TideGauge, optional, default = None
        The tide gauge model.
    river : list[RiverModel], optional, default = None
        The river model.
    obs_point : list[ObsPointModel], optional, default = None
        The observation point model.
    """

    config: SfincsConfigModel
    water_level: WaterlevelReferenceModel
    cyclone_track_database: Optional[CycloneTrackDatabaseModel] = None
    slr_scenarios: Optional[SlrScenariosModel] = None
    scs: Optional[SCSModel] = None  # optional for the US to use SCS rainfall curves
    dem: DemModel

    flood_frequency: FloodFrequencyModel = FloodFrequencyModel(
        flooding_threshold=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters)
    )  # TODO we dont actually use this anywhere?

    tide_gauge: Optional[TideGauge] = None
    river: Optional[list[RiverModel]] = None
    obs_point: Optional[list[ObsPointModel]] = None

    @staticmethod
    def read_toml(path: Path) -> "SfincsModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return SfincsModel(**toml_contents)

    @model_validator(mode="after")
    def ensure_references_exist(self):
        datum_names = [d.name for d in self.water_level.datums]

        if self.config.overland_model.reference not in datum_names:
            raise ValueError(
                f"Could not find reference `{self.config.overland_model.reference}` in available datums: {datum_names}."
            )

        if self.config.offshore_model is not None:
            if self.config.offshore_model.reference not in datum_names:
                raise ValueError(
                    f"Could not find reference `{self.config.offshore_model.reference}` in available datums: {datum_names}."
                )

        if self.tide_gauge is not None:
            if self.tide_gauge.reference not in datum_names:
                raise ValueError(
                    f"Could not find reference `{self.tide_gauge.reference}` in available datums: {datum_names}."
                )

        return self
