from typing import Optional

from pydantic import BaseModel

from flood_adapt.config.impacts import (
    AggregationModel,
    BenefitsModel,
    BFEModel,
    FloodmapType,
    NoFootprintsModel,
    RiskModel,
    SVIModel,
)


class FiatConfigModel(BaseModel):
    """Configuration settings for the FIAT model.

    Attributes
    ----------
    exposure_crs : str
        The coordinate reference system of the exposure data.
    bfe : Optional[BFEModel], default=None
        The base flood elevation model.
    aggregation : list[AggregationModel]
        Configuration for the aggregation model.
    floodmap_type : FloodmapType
        The type of flood map to be used.
    non_building_names : Optional[list[str]], default=None
        List of non-building names to be used in the model.
    damage_unit : str, default="$"
        The unit of damage used in the model.
    building_footprints : Optional[str], default=None
        Path to the building footprints data.
    roads_file_name : Optional[str], default=None
        Path to the roads data.
    new_development_file_name : Optional[str], default="new_development_area.gpkg"
        Path to the new development area data.
    save_simulation : Optional[bool], default=False
        Whether to keep or delete the simulation files after the simulation is finished and all output files are created.
        If True, the simulation files are kept. If False, the simulation files are deleted.
    svi : Optional[SVIModel], default=None
        The social vulnerability index model.
    infographics : Optional[bool], default=False
        Whether to create infographics or not.
    no_footprints : Optional[NoFootprintsModel], default=NoFootprintsModel()
        Configuration for objects with no footprints.
    """

    exposure_crs: str
    bfe: Optional[BFEModel] = None
    aggregation: list[AggregationModel]
    floodmap_type: FloodmapType
    non_building_names: Optional[list[str]]
    damage_unit: str = "$"
    building_footprints: Optional[str] = None
    roads_file_name: Optional[str] = None
    new_development_file_name: Optional[str] = "new_development_area.gpkg"
    save_simulation: Optional[bool] = False
    svi: Optional[SVIModel] = None
    infographics: Optional[bool] = False
    no_footprints: Optional[NoFootprintsModel] = NoFootprintsModel()


class FiatModel(BaseModel):
    """The expected variables and data types of attributes of the Fiat class.

    Attributes
    ----------
    risk : Optional[RiskModel]
        Configuration of probabilistic risk runs. default=None
    config : FiatConfigModel
        Configuration for the FIAT model.
    benefits : Optional[BenefitsModel]
        Configuration for running benefit calculations. default=None
    """

    config: FiatConfigModel

    benefits: Optional[BenefitsModel] = None
    risk: RiskModel = RiskModel()
