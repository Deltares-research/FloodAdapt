import math
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from pydantic import AfterValidator, BaseModel, Field, model_validator
from tomli import load as load_toml
from typing_extensions import Annotated

from flood_adapt.object_model.hazard.interface.tide_gauge import (
    TideGaugeModel,
)
from flood_adapt.object_model.io import unit_system as us


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


class DatumModel(BaseModel):
    """
    The accepted input for the variable datums in WaterlevelReferenceModel.

    Attributes
    ----------
    name : str
        The name of the vertical reference model.
    height : us.UnitfulLength
        The height of the vertical reference model relative to the main reference.
    correction : Optional[us.UnitfulLength], default = None
        The correction of the vertical reference model relative to the main reference.
        Given that the height of the vertical reference model is often determined by external sources,
        this correction can be used to correct systematic over-/underestimation of a vertical reference model.
    """

    name: str
    height: us.UnitfulLength

    # this used to be water_level_offset from events
    correction: Optional[us.UnitfulLength] = None

    @property
    def total_height(self) -> us.UnitfulLength:
        """The height of the vertical reference model, including the correction if provided."""
        if self.correction:
            return self.height + self.correction
        return self.height


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
    """The accepted input for the variable cyclone_track_database in Site."""

    file: str


class SlrScenariosModel(BaseModel):
    """The accepted input for the variable slr in Site."""

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
    """

    name: str
    reference: str


class SfincsConfigModel(BaseModel):
    """The accepted input for the variable sfincs in Site."""

    csname: str
    cstype: Cstype
    version: Optional[str] = None
    offshore_model: Optional[FloodModel] = None
    overland_model: FloodModel
    floodmap_units: us.UnitTypesLength
    save_simulation: Optional[bool] = False


class SfincsModel(BaseModel):
    config: SfincsConfigModel
    water_level: WaterlevelReferenceModel
    cyclone_track_database: Optional[CycloneTrackDatabaseModel] = None
    slr_scenarios: Optional[SlrScenariosModel] = None
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
