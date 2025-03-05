import logging
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader
from hydromt_sfincs.quadtree import QuadtreeGrid

from flood_adapt import __version__
from flood_adapt.adapter.impacts_integrator import Impacts
from flood_adapt.adapter.interface.hazard_adapter import IHazardAdapter
from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.dbs_classes.database import Database
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.interface.events import IEvent, Mode
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.measure_factory import MeasureFactory
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.strategy import Strategy
from flood_adapt.object_model.utils import write_finished_file


class DatabaseObject(Enum):
    BENEFIT = "BENEFIT"
    EVENT = "EVENT"
    STRATEGY = "STRATEGY"
    MEASURE = "MEASURE"
    PROJECTION = "PROJECTION"
    SCENARIO = "SCENARIO"


class FloodAdapt:
    database: Database
    site: Site
    logger: logging.Logger = FloodAdaptLogging.getLogger()

    def __init__(self, database_path: Path) -> None:
        self.database = Database(database_path=database_path)
        self.site = self.database.site

    # General database functions
    def get_object(self, type: DatabaseObject, name: str) -> Any:
        match type:
            case DatabaseObject.EVENT:
                return self.get_event(name)
            case DatabaseObject.MEASURE:
                return self.get_measure(name)
            case DatabaseObject.STRATEGY:
                return self.get_strategy(name)
            case DatabaseObject.PROJECTION:
                return self.get_projection(name)
            case DatabaseObject.SCENARIO:
                return self.get_scenario(name)
            case DatabaseObject.BENEFIT:
                return self.get_benefit(name)
            case _:
                raise ValueError(f"Invalid type: {type}")

    def get_objects(self, type: DatabaseObject) -> dict[str, Any]:
        match type:
            case DatabaseObject.EVENT:
                return self.get_events()
            case DatabaseObject.MEASURE:
                return self.get_measures()
            case DatabaseObject.STRATEGY:
                return self.get_strategies()
            case DatabaseObject.PROJECTION:
                return self.get_projections()
            case DatabaseObject.SCENARIO:
                return self.get_scenarios()
            case DatabaseObject.BENEFIT:
                return self.get_benefits()
            case _:
                raise ValueError(f"Invalid type: {type}")

    def create_object(self, type: DatabaseObject, attrs: dict[str, Any]) -> Any:
        match type:
            case DatabaseObject.EVENT:
                self.create_event(attrs)
            case DatabaseObject.MEASURE:
                self.create_measure(attrs)
            case DatabaseObject.STRATEGY:
                self.create_strategy(attrs)
            case DatabaseObject.PROJECTION:
                self.create_projection(attrs)
            case DatabaseObject.SCENARIO:
                self.create_scenario(attrs)
            case DatabaseObject.BENEFIT:
                self.create_benefit(attrs)
            case _:
                raise ValueError(f"Invalid type: {type}")

    def save_object(
        self, type: DatabaseObject, obj: Any, overwrite: bool = False
    ) -> None:
        match type:
            case DatabaseObject.EVENT:
                self.save_event(obj, overwrite=overwrite)
            case DatabaseObject.MEASURE:
                self.save_measure(obj, overwrite=overwrite)
            case DatabaseObject.STRATEGY:
                self.save_strategy(obj, overwrite=overwrite)
            case DatabaseObject.PROJECTION:
                self.save_projection(obj, overwrite=overwrite)
            case DatabaseObject.SCENARIO:
                self.save_scenario(obj, overwrite=overwrite)
            case DatabaseObject.BENEFIT:
                self.save_benefit(obj)
            case _:
                raise ValueError(f"Invalid type: {type}")

    def edit_object(self, type: DatabaseObject, obj: Any) -> None:
        match type:
            case DatabaseObject.EVENT:
                self.edit_event(obj)
            case DatabaseObject.MEASURE:
                self.edit_measure(obj)
            case DatabaseObject.STRATEGY:
                self.edit_strategy(obj)
            case DatabaseObject.SCENARIO:
                self.edit_scenario(obj)
            case DatabaseObject.PROJECTION:
                self.edit_projection(obj)
            case DatabaseObject.BENEFIT:
                self.edit_benefit(obj)
            case _:
                raise ValueError(f"Invalid type: {type}")

    def copy_object(
        self,
        type: DatabaseObject,
        old_name: str,
        new_name: str,
        new_description: str = "",
    ) -> None:
        match type:
            case DatabaseObject.EVENT:
                self.copy_event(old_name, new_name, new_description)
            case DatabaseObject.MEASURE:
                self.copy_measure(old_name, new_name, new_description)
            case DatabaseObject.STRATEGY:
                self.copy_strategy(old_name, new_name, new_description)
            case DatabaseObject.PROJECTION:
                self.copy_projection(old_name, new_name, new_description)
            case DatabaseObject.SCENARIO:
                self.copy_scenario(old_name, new_name, new_description)
            case DatabaseObject.BENEFIT:
                self.copy_benefit(old_name, new_name, new_description)
            case _:
                raise ValueError(f"Invalid type: {type}")

    def delete_object(self, type: DatabaseObject, name: str) -> None:
        match type:
            case DatabaseObject.EVENT:
                self.delete_event(name)
            case DatabaseObject.MEASURE:
                self.delete_measure(name)
            case DatabaseObject.STRATEGY:
                self.delete_strategy(name)
            case DatabaseObject.SCENARIO:
                self.delete_scenario(name)
            case DatabaseObject.PROJECTION:
                self.delete_projection(name)
            case DatabaseObject.BENEFIT:
                self.delete_benefit(name)
            case _:
                raise ValueError(f"Invalid type: {type}")

    def check_higher_level_usage(self, type: DatabaseObject, name: str) -> list[str]:
        """
        Check if an object is used in another object.

        Parameters
        ----------
        type: DatabaseObject
            The type of object to check.
        name : str
            name of the event to be checked

        Returns
        -------
        list[str]
        """
        match type:
            case DatabaseObject.EVENT:
                return self.database.events.check_higher_level_usage(name)
            case DatabaseObject.MEASURE:
                return self.database.measures.check_higher_level_usage(name)
            case DatabaseObject.STRATEGY:
                return self.database.strategies.check_higher_level_usage(name)
            case DatabaseObject.PROJECTION:
                return self.database.projections.check_higher_level_usage(name)
            case DatabaseObject.SCENARIO:
                return self.database.scenarios.check_higher_level_usage(name)
            case DatabaseObject.BENEFIT:
                return self.database.benefits.check_higher_level_usage(name)
            case _:
                raise ValueError(f"Invalid type: {type}")

    # Measures
    def get_measures(self) -> dict[str, Any]:
        """
        Get all measures from the database.

        Returns
        -------
        dict[str, Any]
            A dictionary containing all measures.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each measure.
        """
        return self.database.measures.list_objects()

    def get_measure(self, name: str) -> Any:
        """
        Get a measure from the database by name.

        Parameters
        ----------
        name : str
            The name of the measure to retrieve.

        Returns
        -------
        Any
            The measure object with the given name.

        Raises
        ------
        ValueError
            If the measure with the given name does not exist.
        """
        return self.database.measures.get(name)

    def create_measure(self, attrs: dict[str, Any]) -> IMeasure:
        """
        Create a new measure object.

        Parameters
        ----------
        attrs : dict[str, Any]
            The attributes of the measure object to create. Should adhere to the MeasureModel schema.
        """
        return MeasureFactory.create_measure(attrs)

    def save_measure(self, measure: IMeasure, overwrite: bool = False) -> None:
        """
        Save a measure object to the database.

        Parameters
        ----------
        measure : IMeasure
            The measure object to save.
        """
        self.database.measures.save(measure)

    def edit_measure(self, measure: IMeasure) -> None:
        """
        Edit a measure object in the database.

        Parameters
        ----------
        measure : IMeasure
            The measure object to edit.
        """
        self.database.measures.edit(measure)

    def copy_measure(self, old_name: str, new_name: str, new_description: str = ""):
        """
        Copy a measure object in the database.

        Parameters
        ----------
        measure : IMeasure
            The measure object to copy.
        """
        self.database.measures.copy(
            old_name=old_name, new_name=new_name, new_description=new_description
        )

    def delete_measure(self, name: str) -> None:
        """
        Delete a measure object from the database.

        Parameters
        ----------
        name : str
            The name of the measure object to delete.

        Raises
        ------
        ValueError
            If the measure object does not exist.
        """
        self.database.measures.delete(name)

    def get_green_infra_table(self, measure_type: str) -> pd.DataFrame:
        """Return a table with different types of green infrastructure measures and their infiltration depths.

        Parameters
        ----------
        measure_type : str
            The type of green infrastructure measure.

        Returns
        -------
        pd.DataFrame
            A table with different types of green infrastructure measures and their infiltration depths.

        """
        return self.database.static.get_green_infra_table(measure_type)

    # Strategies
    def get_strategies(self) -> dict[str, Any]:
        """
        Get all strategies from the database.

        Returns
        -------
        dict[str, Any]
            A dictionary containing all strategies.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each strategy.
        """
        return self.database.strategies.list_objects()

    def get_strategy(self, name: str) -> IStrategy:
        """
        Get a strategy from the database by name.

        Parameters
        ----------
        name : str
            The name of the strategy to retrieve.

        Returns
        -------
        IStrategy
            The strategy object with the given name.

        Raises
        ------
        ValueError
            If the strategy with the given name does not exist.
        """
        return self.database.strategies.get(name)

    def create_strategy(self, attrs: dict[str, Any]) -> Strategy:
        """Create a new strategy object.

        Parameters
        ----------
        attrs : dict[str, Any]
            The attributes of the strategy object to create. Should adhere to the StrategyModel schema.

        Returns
        -------
        IStrategy
            The strategy object

        Raises
        ------
        ValueError
            If the strategy with the given name does not exist.
            If attrs does not adhere to the StrategyModel schema.
        """
        return Strategy(attrs)

    def save_strategy(self, strategy: Strategy, overwrite: bool = False) -> None:
        """
        Save a strategy object to the database.

        Parameters
        ----------
        strategy : IStrategy
            The strategy object to save.

        Raises
        ------
        ValueError
            If the strategy object is not valid.
        """
        self.database.strategies.save(strategy, overwrite=overwrite)

    def edit_strategy(self, strategy: Strategy) -> None:
        """
        Edit a strategy object in the database.

        Parameters
        ----------
        strategy : IStrategy
            The strategy object to edit.

        Raises
        ------
        ValueError
            If the strategy object is not valid.
        """
        self.database.strategies.edit(strategy)

    def copy_strategy(self, old_name: str, new_name: str, new_description: str = ""):
        """
        Copy a strategy object in the database.

        Parameters
        ----------
        old_name : str
            The name of the strategy to copy.
        new_name : str
            The name of the new strategy.
        new_description : str
            The description of the new strategy.
        """
        self.database.strategies.copy(
            old_name=old_name, new_name=new_name, new_description=new_description
        )

    def delete_strategy(self, name: str) -> None:
        """
        Delete a strategy object from the database.

        Parameters
        ----------
        name : str
            The name of the strategy object to delete.

        Raises
        ------
        ValueError
            If the strategy object does not exist.
        """
        self.database.strategies.delete(name)

    # Events
    def get_events(self) -> dict[str, Any]:
        """
        Get all events from the database.

        Returns
        -------
        dict[str, Any]
            A dictionary containing all events.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each event.
        """
        return self.database.events.list_objects()

    def get_event(self, name: str) -> IEvent:
        """
        Get an event from the database by name.

        Parameters
        ----------
        name : str
            The name of the event to retrieve.

        Returns
        -------
        Any
            The event object with the given name.

        Raises
        ------
        ValueError
            If the event with the given name does not exist.
        """
        return self.database.events.get(name)

    def get_event_mode(self, name: str) -> Mode:
        """
        Get the mode of an event from the database by name.

        Parameters
        ----------
        name : str

        Returns
        -------
        Mode
        """
        return self.database.events.get(name).attrs.mode

    def create_event(self, attrs: dict[str, Any]) -> Any:
        """
        Create an event object from a dictionary of attributes.

        Parameters
        ----------
        attrs : dict[str, Any]

        Returns
        -------
        Any
        """
        return EventFactory.load_dict(attrs)

    def save_event(self, event: IEvent, overwrite: bool = False) -> None:
        """
        Save an event object to the database.

        Parameters
        ----------
        event : IEvent
            The event object to save.
        overwrite: bool
            Whether to overwrite the event if it already exists.
        """
        self.database.events.save(event, overwrite=overwrite)

    def edit_event(self, event: IEvent) -> None:
        """
        Edit an event object in the database.

        Parameters
        ----------
        event : IEvent
            The event object to edit.
        """
        self.database.events.edit(event)

    def delete_event(self, name: str) -> None:
        """
        Delete an event from the database.

        Parameters
        ----------
        name : str
            The name of the event to delete.

        Raises
        ------
        ValueError
            If the event does not exist.
        """
        self.database.events.delete(name)

    def copy_event(self, old_name: str, new_name: str, new_description: str = ""):
        """
        Copy an event in the database.

        Parameters
        ----------
        old_name : str
            The name of the event to copy.
        new_name : str
            The name of the new event.
        new_description : str
            The description of the new event
        """
        self.database.events.copy(
            old_name=old_name, new_name=new_name, new_description=new_description
        )

    # Projections
    def get_projections(self) -> dict[str, Any]:
        """
        Get all projections from the database.

        Returns
        -------
        dict[str, Any]
            A dictionary containing all projections.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each projection.
        """
        return self.database.projections.list_objects()

    def get_projection(self, name: str) -> Projection:
        """
        Get a projection from the database by name.

        Parameters
        ----------
        name : str
            The name of the projection to retrieve.

        Returns
        -------
        Projection
            The projection object with the given name.

        Raises
        ------
        ValueError
            If the projection with the given name does not exist.
        """
        return self.database.projections.get(name)

    def create_projection(self, attrs: dict[str, Any]) -> Projection:
        """
        Create a projection object from a dictionary of attributes.

        Parameters
        ----------
        attrs : dict[str, Any]

        Returns
        -------
        Projection
        """
        return Projection(attrs)

    def save_projection(self, projection: Projection, overwrite: bool = False) -> None:
        """
        Save a projection object to the database.

        Parameters
        ----------
        projection : Projection
            The projection object to save.
        overwrite: bool
            Whether to overwrite the projection if it already exists.
        """
        self.database.projections.save(projection, overwrite=overwrite)

    def edit_projection(self, projection: Projection) -> None:
        """
        Edit a projection object in the database.

        Parameters
        ----------
        projection : Projection
            The projection object to edit.
        """
        self.database.projections.edit(projection)

    def copy_projection(self, old_name: str, new_name: str, new_description: str = ""):
        """
        Copy a projection in the database.

        Parameters
        ----------
        old_name : str
            The name of the projection to copy.
        new_name : str
            The name of the new projection.
        new_description : str
            The description of the new projection
        """
        self.database.projections.copy(
            old_name=old_name, new_name=new_name, new_description=new_description
        )

    def delete_projection(self, name: str) -> None:
        """
        Delete a projection object from the database.

        Parameters
        ----------
        name : str
            The name of the projection object to delete.

        Raises
        ------
        ValueError
            If the projection object does not exist.
        """
        self.database.projections.delete(name)

    # Scenarios
    def get_scenarios(self) -> dict[str, Any]:
        """
        Get all scenarios from the database.

        Returns
        -------
        dict[str, Any]
            A dictionary containing all scenarios.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each scenario.
        """
        return self.database.scenarios.list_objects()

    def get_scenario(self, name: str) -> Scenario:
        """
        Get a scenario from the database by name.

        Parameters
        ----------
        name : str
            The name of the scenario to retrieve.

        Returns
        -------
        Scenario
            The scenario object with the given name.

        Raises
        ------
        ValueError
            If the scenario with the given name does not exist.
        """
        return self.database.scenarios.get(name)

    def create_scenario(self, attrs: dict[str, Any]) -> Scenario:
        """
        Create a scenario object from a dictionary of attributes.

        Parameters
        ----------
        attrs : dict[str, Any]

        Returns
        -------
        Scenario
        """
        return Scenario(attrs)

    def save_scenario(self, scenario: Scenario, overwrite: bool = False) -> None:
        """
        Save a scenario object to the database.

        Parameters
        ----------
        scenario : Scenario
            The scenario object to save.
        overwrite: bool
            Whether to overwrite the scenario if it already exists.
        """
        self.database.scenarios.save(scenario, overwrite=overwrite)

    def edit_scenario(self, scenario: Scenario) -> None:
        """
        Edit a scenario object in the database.

        Parameters
        ----------
        scenario : Scenario
            The scenario object to edit.
        """
        self.database.scenarios.edit(scenario)

    def copy_scenario(self, old_name: str, new_name: str, new_description: str = ""):
        """
        Copy a scenario in the database.

        Parameters
        ----------
        old_name : str
            The name of the scenario to copy.
        new_name : str
            The name of the new scenario.
        new_description : str
            The description of the new scenario
        """
        self.database.scenarios.copy(
            old_name=old_name, new_name=new_name, new_description=new_description
        )

    def delete_scenario(self, name: str) -> None:
        """
        Delete a scenario object from the database.

        Parameters
        ----------
        name : str
            The name of the scenario object to delete.

        Raises
        ------
        ValueError
            If the scenario object does not exist.
        """
        self.database.scenarios.delete(name)

    def run_scenario(self, name: str | list[str]) -> None:
        """
        Run a scenario.

        Parameters
        ----------
        name : str
            The name of the scenario to run.
        """
        if not isinstance(name, list):
            name = [name]

        errors = []
        for scn in name:
            try:
                self.database.has_run_hazard(scn)

                scenario = self.database.scenarios.get(scn)
                scenario.load_objects(self.database)

                results_path = self.database.scenarios.output_path / scenario.attrs.name
                log_file = results_path.joinpath(f"logfile_{scenario.attrs.name}.log")

                # Initiate the logger for all the integrator scripts.
                with FloodAdaptLogging.to_file(file_path=log_file):
                    self.logger.info(f"FloodAdapt version `{__version__}`")
                    self.logger.info(f"Started evaluation of `{scenario.attrs.name}`")

                    hazard_models: list[IHazardAdapter] = self.get_hazard_models()
                    for hazard in hazard_models:
                        if not hazard.has_run(scenario, self.database):
                            hazard.run(scenario=scenario, database=self.database)
                        else:
                            self.logger.info(
                                f"Hazard for scenario '{scenario.attrs.name}' has already been run."
                            )

                    if floodmap := self.database.scenarios.get_floodmap(scn):
                        impact = Impacts(
                            scenario=scenario,
                            flood_map=floodmap,
                            impact_models=self.get_impact_models(),
                            site_info=self.site,
                            output_path=self.database.scenarios.output_path,
                        )
                        impact.run(self.database)
                    else:
                        self.logger.error(
                            f"No floodmap found for scenario '{scenario.attrs.name}'."
                        )
                        raise RuntimeError(
                            f"No floodmap found for scenario '{scenario.attrs.name}'."
                        )

                    self.logger.info(f"Finished evaluation of `{scenario.attrs.name}`")

                # write finished file to indicate that the scenario has been run
                write_finished_file(results_path)
            except RuntimeError as e:
                if "SFINCS model failed to run." in str(e):
                    errors.append(str(scn))

        if errors:
            raise RuntimeError(
                "FloodAdapt failed to run for the following scenarios: "
                + ", ".join(errors)
                + ". Check the logs for more information."
            )

    # Benefits
    def get_benefits(self) -> dict[str, Any]:
        """
        Get all benefits from the database.

        Returns
        -------
        dict[str, Any]
            A dictionary containing all benefits.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each benefit.
        """
        return self.database.benefits.list_objects()

    def get_benefit(self, name: str) -> Any:
        """
        Get a benefit from the database by name.

        Parameters
        ----------
        name : str
            The name of the benefit to retrieve.

        Returns
        -------
        Any
            The benefit object with the given name.

        Raises
        ------
        ValueError
            If the benefit with the given name does not exist.
        """
        return self.database.benefits.get(name)

    def create_benefit(self, attrs: dict[str, Any]) -> Any:
        """
        Create a new benefit object.

        Parameters
        ----------
        attrs : dict[str, Any]
            The attributes of the benefit object to create. Should adhere to the BenefitModel schema.
        """
        return Benefit(attrs)

    def save_benefit(self, benefit: Benefit) -> None:
        """
        Save a benefit object to the database.

        Parameters
        ----------
        benefit : Benefit
            The benefit object to save.
        """
        self.database.benefits.save(benefit)

    def edit_benefit(self, benefit: Benefit) -> None:
        """
        Edit a benefit object in the database.

        Parameters
        ----------
        benefit : Benefit
            The benefit object to edit.
        """
        self.database.benefits.edit(benefit)

    def copy_benefit(self, old_name: str, new_name: str, new_description: str = ""):
        """
        Copy a benefit object in the database.

        Parameters
        ----------
        old_name : str
            The name of the benefit to copy.
        new_name : str
            The name of the new benefit.
        new_description : str
            The description of the new benefit.
        """
        self.database.benefits.copy(
            old_name=old_name, new_name=new_name, new_description=new_description
        )

    def delete_benefit(self, name: str) -> None:
        """
        Delete a benefit object from the database.

        Parameters
        ----------
        name : str
            The name of the benefit object to delete.

        Raises
        ------
        ValueError
            If the benefit object does not exist.
        """
        self.database.benefits.delete(name)

    def check_benefit_scenarios(self, benefit: IBenefit) -> pd.DataFrame:
        """Return a dataframe with the scenarios needed for this benefit assessment run.

        Parameters
        ----------
        benefit : IBenefit
            The benefit object to check.

        Returns
        -------
        pd.DataFrame
            A dataframe with the scenarios needed for this benefit assessment run.
        """
        return self.database.check_benefit_scenarios(benefit)

    def create_benefit_scenarios(self, benefit: IBenefit):
        """Create the benefit scenarios.

        Parameters
        ----------
        benefit : IBenefit
            The benefit object to create scenarios for.
        """
        self.database.create_benefit_scenarios(benefit)

    def run_benefit(self, name: Union[str, list[str]]) -> None:
        """Run the benefit assessment.

        Parameters
        ----------
        name : Union[str, list[str]]
            The name of the benefit object to run.
        """
        self.database.run_benefit(name)

    def get_aggregation_benefits(self, name: str) -> dict[str, gpd.GeoDataFrame]:
        """Get the aggregation benefits for a benefit assessment.

        Parameters
        ----------
        name : str
            The name of the benefit assessment.

        Returns
        -------
        gpd.GeoDataFrame
            The aggregation benefits for the benefit assessment.
        """
        return self.database.get_aggregation_benefits(name)

    # Output
    def get_outputs(self) -> dict[str, Any]:
        """Get all completed scenarios from the database.

        Returns
        -------
        dict[str, Any]
            A dictionary containing all scenarios.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each output.
        """
        return self.database.get_outputs()

    def get_topobathy_path(self) -> str:
        """
        Return the path of the topobathy tiles in order to create flood maps with water level maps.

        Returns
        -------
        str
            The path to the topobathy file.

        """
        return self.database.get_topobathy_path()

    def get_index_path(self) -> str:
        """
        Return the path of the index tiles which are used to connect each water level cell with the topobathy tiles.

        Returns
        -------
        str
            The path to the index file.
        """
        return self.database.get_index_path()

    def get_depth_conversion(self) -> float:
        """
        Return the flood depth conversion that is need in the gui to plot the flood map.

        Returns
        -------
        float
            The flood depth conversion.
        """
        return self.database.get_depth_conversion()

    def get_max_water_level(self, name: str, rp: Optional[int] = None) -> np.ndarray:
        """
        Return the maximum water level for the given scenario.

        Parameters
        ----------
        name : str
            The name of the scenario.
        rp : int, optional
            The return period of the water level, by default None

        Returns
        -------
        np.ndarray
            2D gridded map with the maximum waterlevels for each cell.
        """
        return self.database.get_max_water_level(name, rp)

    def get_building_footprints(self, name: str) -> gpd.GeoDataFrame:
        """
        Return a gpd.GeoDataFrame of the impacts at the footprint level.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        gpd.GeoDataFrame
            The impact footprints for the scenario.
        """
        return self.database.get_building_footprints(name)

    def get_aggregation(self, name: str) -> dict[str, gpd.GeoDataFrame]:
        """
        Return a dictionary with the aggregated impacts as gpd.GeoDataFrames.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        dict[str, gpd.GeoDataFrame]
            The aggregated impacts for the scenario.
        """
        return self.database.get_aggregation(name)

    def get_roads(self, name: str) -> gpd.GeoDataFrame:
        """
        Return a gpd.GeoDataFrame of the impacts at roads.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        gpd.GeoDataFrame
            The impacted roads for the scenario.
        """
        return self.database.get_roads(name)

    def hazard_has_run(self, scenario_name: str) -> bool:
        # if self.mode == Mode.single_event:
        #     return self.path.exists()
        # elif self.mode == Mode.risk:
        #     check_files = [RP_map.exists() for RP_map in self.path]
        #     check_rps = len(self.path) == len(
        #         self.database.site.attrs.fiat.risk.return_periods
        #     )
        #     return all(check_files) & check_rps
        # else:
        #     return False

        scn = self.database.scenarios.get(scenario_name)
        return self.database.has_run_hazard(scn)

    def get_obs_point_timeseries(self, name: str) -> gpd.GeoDataFrame:
        """Return the HTML strings of the water level timeseries for the given scenario.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        str
            The HTML strings of the water level timeseries
        """
        # Check if the scenario has run
        flood_map = self.database.scenarios.get_floodmap(name)
        if flood_map is None:
            raise ValueError(
                f"Scenario {name} has not been run. Please run the scenario first."
            )

        output_path = self.database.scenarios.output_path.joinpath(flood_map.name)
        gdf = self.database.static.get_obs_points()
        gdf["html"] = [
            str(output_path.joinpath("Flooding", f"{station}_timeseries.html"))
            for station in gdf.name
        ]

        return gdf

    def get_infographic(self, name: str) -> str:
        """Return the HTML string of the infographic for the given scenario.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        str
            The HTML string of the infographic.
        """
        # Get the impacts objects from the scenario
        scn = self.database.scenarios.get(name)
        flood_map = self.database.scenarios.get_floodmap(name)
        if flood_map is None:
            raise ValueError(
                f"Scenario {name} has not been run. Please run the scenario first."
            )
        impact = Impacts(
            scenario=scn,
            flood_map=flood_map,
            impact_models=self.get_impact_models(),
            site_info=self.site,
            output_path=self.database.scenarios.output_path,
        )

        # Check if the scenario has run
        if not impact.has_run_check(self.database):
            raise ValueError(
                f"Scenario {name} has not been run. Please run the scenario first."
            )

        config_path = self.database.static_path.joinpath("templates", "infographics")
        output_path = self.database.scenarios.output_path.joinpath(impact.name)
        metrics_outputs_path = output_path.joinpath(f"Infometrics_{impact.name}.csv")

        infographic_path = InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=scn.event.attrs.mode,
            scenario_name=impact.name,
            metrics_full_path=metrics_outputs_path,
            config_base_path=config_path,
            output_base_path=output_path,
        ).get_infographics_html()

        return infographic_path

    def get_infometrics(self, name: str) -> pd.DataFrame:
        """Return the metrics for the given scenario.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        pd.DataFrame

        Raises
        ------
        FileNotFoundError
            If the metrics file does not exist.
        """
        # Create the infographic path
        metrics_path = self.database.scenarios.output_path.joinpath(
            name,
            f"Infometrics_{name}.csv",
        )

        # Check if the file exists
        if not metrics_path.exists():
            raise FileNotFoundError(
                f"The metrics file for scenario {name}({str(metrics_path)}) does not exist."
            )

        # Read the metrics file
        return MetricsFileReader(str(metrics_path)).read_metrics_from_file(
            include_long_names=True,
            include_description=True,
            include_metrics_table_selection=True,
        )

    # Static
    def get_aggregation_areas(self) -> list[gpd.GeoDataFrame]:
        """Get a list of the aggregation areas that are provided in the site configuration.

        These are expected to much the ones in the FIAT model.

        Returns
        -------
        dict[str, gpd.GeoDataFrame]
            list of gpd.GeoDataFrames with the polygons defining the aggregation areas
        """
        return self.database.static.get_aggregation_areas()

    def get_obs_points(self) -> gpd.GeoDataFrame:
        """Get the observation points specified in the site.toml.

        These are also added to the flood hazard model. They are used as marker locations to plot water level time series in the output tab.

        Returns
        -------
        gpd.GeoDataFrame
            gpd.GeoDataFrame with observation points from the site.toml.
        """
        return self.database.static.get_obs_points()

    def get_model_boundary(self) -> gpd.GeoDataFrame:
        """Get the model boundary that is used in SFINCS.

        Returns
        -------
        gpd.GeoDataFrame
            gpd.GeoDataFrame with the model boundary
        """
        return self.database.static.get_model_boundary()

    def get_model_grid(self) -> QuadtreeGrid:
        """Get the model grid that is used in SFINCS.

        Returns
        -------
        QuadtreeGrid
            QuadtreeGrid with the model grid
        """
        return self.database.static.get_model_grid()

    def get_svi_map(self) -> Union[gpd.GeoDataFrame, None]:
        """Get the SVI map that are used in Fiat.

        Returns
        -------
        gpd.GeoDataFrame
            gpd.GeoDataFrames with the SVI map, None if not available
        """
        try:
            return self.database.static.get_static_map(
                self.database.site.attrs.fiat.config.svi.geom
            )
        except Exception:
            return None

    def get_static_map(self, path: Union[str, Path]) -> Union[gpd.GeoDataFrame, None]:
        """Get a static map from the database.

        Parameters
        ----------
        path : Union[str, Path]
            path to the static map

        Returns
        -------
        gpd.GeoDataFrame
            gpd.GeoDataFrame with the static map
        """
        return self.database.static.get_static_map(path)

    def get_buildings(self) -> gpd.GeoDataFrame:
        """Get the buildings exposure that are used in Fiat.

        Returns
        -------
        gpd.GeoDataFrame
            gpd.GeoDataFrames with the buildings from FIAT exposure
        """
        return self.database.static.get_buildings()

    def get_property_types(self) -> list:
        """Get the property types that are used in the exposure.

        Returns
        -------
        list
            list of property types
        """
        return self.database.static.get_property_types()

    def get_hazard_models(self) -> list[IHazardAdapter]:
        """Get the hazard models that are used in the scenario.

        Returns
        -------
        list[IHazardAdapter]
            list of hazard models
        """
        return [
            self.database.static.get_overland_sfincs_model(),
        ]

    def get_impact_models(self) -> list[IImpactAdapter]:
        """Get the impact models that are used in the scenario.

        Returns
        -------
        list[IImpactAdapter]
            list of impact models
        """
        return [
            self.database.static.get_fiat_model(),
        ]


# Static functions
# TODO give these functions a better place?


# Measures
def calculate_polygon_area(gdf: gpd.GeoDataFrame, site: Site) -> float:
    """
    Calculate the area of a polygon from a gpd.GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        A gpd.GeoDataFrame containing the polygon geometry.
    site : ISite
        An instance of ISite representing the site information.

    Returns
    -------
        float: The area of the polygon in the specified units.
    """
    return GreenInfrastructure.calculate_polygon_area(gdf=gdf, site=site)


@staticmethod
def calculate_volume(
    area: us.UnitfulArea,
    height: us.UnitfulHeight = us.UnitfulHeight(
        value=0.0, units=us.UnitTypesLength.meters
    ),
    percent_area: float = 100.0,
) -> float:
    """
    Calculate the volume of green infrastructure based on the given area, height, and percent area.

    Parameters
    ----------
    area : float
        The area of the green infrastructure in square units.
    height : float
        The height of the green infrastructure in units. Defaults to 0.0.
    percent_area : float
        The percentage of the area to be considered. Defaults to 100.0.


    Returns
    -------
        float: The calculated volume of the green infrastructure.
    """
    return GreenInfrastructure.calculate_volume(
        area=area, height=height, percent_area=percent_area
    )
