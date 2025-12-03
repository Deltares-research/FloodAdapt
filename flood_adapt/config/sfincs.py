from pathlib import Path
from typing import Optional

from pydantic import BaseModel, model_validator
from tomli import load as load_toml

from flood_adapt.config.hazard import (
    Cstype,
    CycloneTrackDatabaseModel,
    DemModel,
    FloodFrequencyModel,
    FloodModel,
    ObsPointModel,
    RiverModel,
    SCSModel,
    SlrScenariosModel,
    WaterlevelReferenceModel,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.tide_gauge import TideGauge


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
