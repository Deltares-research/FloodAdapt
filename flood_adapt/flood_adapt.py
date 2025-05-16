from pathlib import Path
from typing import Any, List, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader
from hydromt_sfincs.quadtree import QuadtreeGrid

from flood_adapt.dbs_classes.database import Database
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.objects.benefits.benefits import Benefit
from flood_adapt.objects.events.event_factory import (
    EventFactory,
)
from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.events.events import (
    Event,
)
from flood_adapt.objects.forcing.forcing import (
    ForcingType,
)
from flood_adapt.objects.forcing.plotting import (
    plot_forcing as _plot_forcing,
)
from flood_adapt.objects.measures.measures import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    Measure,
    Pump,
)
from flood_adapt.objects.projections.projections import Projection
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.objects.strategies.strategies import Strategy
from flood_adapt.workflows.impacts_integrator import Impacts
from flood_adapt.workflows.scenario_runner import ScenarioRunner


class FloodAdapt:
    database: Database

    def __init__(self, database_path: Path) -> None:
        """Initialize the FloodAdapt class with a database path.

        Parameters
        ----------
        database_path : Path
            The path to the database file.
        """
        self.database = Database(
            database_path=database_path.parent, database_name=database_path.name
        )
        self.logger = FloodAdaptLogging.getLogger()

    # Measures
    def get_measures(self) -> dict[str, Any]:
        """
        Get all measures from the database.

        Returns
        -------
        measures : dict[str, Any]
            A dictionary containing all measures.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each measure.
        """
        return self.database.measures.summarize_objects()

    def get_measure(self, name: str) -> Measure:
        """
        Get a measure from the database by name.

        Parameters
        ----------
        name : str
            The name of the measure to retrieve.

        Returns
        -------
        measure : Measure
            The measure object with the given name.

        Raises
        ------
        ValueError
            If the measure with the given name does not exist.
        """
        return self.database.measures.get(name)

    def create_measure(self, attrs: dict[str, Any], type: str = None) -> Measure:
        """Create a measure from a dictionary of attributes and a type string.

        Parameters
        ----------
        attrs : dict[str, Any]
            Dictionary of attributes for the measure.
        type : str
            Type of measure to create.

        Returns
        -------
        measure : Measure
            Measure object.
        """
        if type == "elevate_properties":
            return Elevate(**attrs)
        elif type == "buyout_properties":
            return Buyout(**attrs)
        elif type == "floodproof_properties":
            return FloodProof(**attrs)
        elif type in ["floodwall", "thin_dam", "levee"]:
            return FloodWall(**attrs)
        elif type in ["pump", "culvert"]:
            return Pump(**attrs)
        elif type in ["water_square", "total_storage", "greening"]:
            return GreenInfrastructure(**attrs)
        else:
            raise ValueError(f"Invalid measure type: {type}")

    def save_measure(self, measure: Measure, overwrite: bool = False) -> None:
        """Save a measure object to the database.

        Parameters
        ----------
        measure : Measure
            The measure object to save.

        Raises
        ------
        ValueError
            If the measure object is not valid.
        """
        self.database.measures.save(measure, overwrite=overwrite)

    def edit_measure(self, measure: Measure) -> None:
        """Edit a measure object in the database.

        Parameters
        ----------
        measure : Measure
            The measure object to edit.

        Raises
        ------
        ValueError
            If the measure object does not exist.
        """
        self.database.measures.edit(measure)

    def delete_measure(self, name: str) -> None:
        """Delete an measure from the database.

        Parameters
        ----------
        name : str
            The name of the measure to delete.

        Raises
        ------
        ValueError
            If the measure does not exist.
        """
        self.database.measures.delete(name)

    def copy_measure(self, old_name: str, new_name: str, new_description: str) -> None:
        """Copy a measure in the database.

        Parameters
        ----------
        old_name : str
            The name of the measure to copy.
        new_name : str
            The name of the new measure.
        new_description : str
            The description of the new measure
        """
        self.database.measures.copy(old_name, new_name, new_description)

    def get_green_infra_table(self, measure_type: str) -> pd.DataFrame:
        """Return a table with different types of green infrastructure measures and their infiltration depths.

        Parameters
        ----------
        measure_type : str
            The type of green infrastructure measure.

        Returns
        -------
        table : pd.DataFrame
            A table with different types of green infrastructure measures and their infiltration depths.

        """
        return self.database.static.get_green_infra_table(measure_type)

    # Strategies
    def get_strategies(self) -> dict[str, Any]:
        """
        Get all strategies from the database.

        Returns
        -------
        strategies : dict[str, Any]
            A dictionary containing all strategies.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each strategy.
        """
        return self.database.strategies.summarize_objects()

    def get_strategy(self, name: str) -> Strategy:
        """
        Get a strategy from the database by name.

        Parameters
        ----------
        name : str
            The name of the strategy to retrieve.

        Returns
        -------
        strategy : Strategy
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
            The attributes of the strategy object to create. Should adhere to the Strategy schema.

        Returns
        -------
        strategy : Strategy
            The strategy object

        Raises
        ------
        ValueError
            If the strategy with the given name does not exist.
            If attrs does not adhere to the Strategy schema.
        """
        return Strategy(**attrs)

    def save_strategy(self, strategy: Strategy) -> None:
        """
        Save a strategy object to the database.

        Parameters
        ----------
        strategy : Strategy
            The strategy object to save.

        Raises
        ------
        ValueError
            If the strategy object is not valid.
            If the strategy object already exists.
        """
        self.database.strategies.save(strategy)

    def delete_strategy(self, name: str) -> None:
        """
        Delete a strategy from the database.

        Parameters
        ----------
        name : str
            The name of the strategy to delete.

        Raises
        ------
        ValueError
            If the strategy does not exist.
        """
        self.database.strategies.delete(name)

    def copy_strategy(self, old_name: str, new_name: str, new_description: str) -> None:
        """Copy a strategy in the database.

        Parameters
        ----------
        old_name : str
            The name of the strategy to copy.
        new_name : str
            The name of the new strategy.
        new_description : str
            The description of the new strategy
        """
        self.database.strategies.copy(old_name, new_name, new_description)

    # Events
    def get_events(self) -> dict[str, Any]:
        """Get all events from the database.

        Returns
        -------
        events : dict[str, Any]
            A dictionary containing all events.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each benefit.
        """
        return self.database.events.summarize_objects()

    def get_event(self, name: str) -> Event | EventSet:
        """Get an event from the database by name.

        Parameters
        ----------
        name : str
            The name of the event to retrieve.

        Returns
        -------
        event: Union[Event, EventSet]
            The event with the given name.

        Raises
        ------
        ValueError
            If the event with the given name does not exist.
        """
        return self.database.events.get(name)

    def create_event(self, attrs: dict[str, Any] | Event) -> Event:
        """Create a event object from a dictionary of attributes.

        Parameters
        ----------
        attrs : Event [str, Any]
            Dictionary of attributes

        Returns
        -------
        event : Event
            Depending on attrs.template an event object.
            Can be of type: Synthetic, Historical, Hurricane.
        """
        return EventFactory.load_dict(attrs)

    def create_event_set(
        self, attrs: dict[str, Any] | EventSet, sub_events: list[Event]
    ) -> EventSet:
        """Create a event set object from a dictionary of attributes.

        Parameters
        ----------
        attrs : EventSet [str, Any]
            Dictionary of attributes
        sub_events : list[Event]
            List of events in the event set

        Returns
        -------
        event_set : EventSet
            EventSet object
        """
        return EventSet(**attrs, sub_events=sub_events)

    def save_event(self, event: Event) -> None:
        """Save an event object to the database.

        Parameters
        ----------
        event : Event
            The event object to save.

        Raises
        ------
        ValueError
            If the event object is not valid.
        """
        self.database.events.save(event)

    def edit_event(self, event: Event) -> None:
        """Edit an event object in the database.

        Parameters
        ----------
        event : Event
            The event object to edit.

        Raises
        ------
        ValueError
            If the event object does not exist.
            If the event is used in a scenario.
        """
        self.database.events.edit(event)

    def delete_event(self, name: str) -> None:
        """Delete an event from the database.

        Parameters
        ----------
        name : str
            The name of the event to delete.

        Raises
        ------
        ValueError
            If the event does not exist.
            If the event is used in a scenario.
        """
        self.database.events.delete(name)

    def copy_event(self, old_name: str, new_name: str, new_description: str) -> None:
        """Copy an event in the database.

        Parameters
        ----------
        old_name : str
            The name of the event to copy.
        new_name : str
            The name of the new event.
        new_description : str
            The description of the new event
        """
        self.database.events.copy(old_name, new_name, new_description)

    def plot_event_forcing(
        self, event: Event, forcing_type: ForcingType
    ) -> tuple[str, Optional[List[Exception]]]:
        """Plot forcing data for an event.

        Parameters
        ----------
        event : Event
            The event object
        forcing_type : ForcingType
            The type of forcing data to plot
        """
        return _plot_forcing(event, self.database.site, forcing_type)

    def get_cyclone_track_by_index(self, index: int) -> TropicalCyclone:
        """
        Get a cyclone track from the database by index.

        Parameters
        ----------
        index : int
            The index of the cyclone track to retrieve.

        Returns
        -------
        cyclone : TropicalCyclone
            The cyclone track object with the given index.

        Raises
        ------
        ValueError
            If the cyclone track database is not defined in the site configuration.
            If the cyclone track with the given index does not exist.
        """
        return self.database.static.get_cyclone_track_database().get_track(index)

    # Projections
    def get_projections(self) -> dict[str, Any]:
        """
        Get all projections from the database.

        Returns
        -------
        projections: dict[str, Any]
            A dictionary containing all projections.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each projection.
        """
        return self.database.projections.summarize_objects()

    def get_projection(self, name: str) -> Projection:
        """Get a projection from the database by name.

        Parameters
        ----------
        name : str
            The name of the projection to retrieve.

        Returns
        -------
        projection : Projection
            The projection object with the given name.

        Raises
        ------
        ValueError
            If the projection with the given name does not exist.
        """
        return self.database.projections.get(name)

    def create_projection(self, attrs: dict[str, Any]) -> Projection:
        """Create a new projection object.

        Parameters
        ----------
        attrs : dict[str, Any]
            The attributes of the projection object to create. Should adhere to the Projection schema.

        Returns
        -------
        projection : Projection
            The projection object created from the attributes.

        Raises
        ------
        ValueError
            If the attributes do not adhere to the Projection schema.
        """
        return Projection(**attrs)

    def save_projection(self, projection: Projection) -> None:
        """Save a projection object to the database.

        Parameters
        ----------
        projection : Projection
            The projection object to save.

        Raises
        ------
        ValueError
            If the projection object is not valid.
        """
        self.database.projections.save(projection)

    def edit_projection(self, projection: Projection) -> None:
        """Edit a projection object in the database.

        Parameters
        ----------
        projection : Projection
            The projection object to edit.

        Raises
        ------
        ValueError
            If the projection object does not exist.
        """
        self.database.projections.edit(projection)

    def delete_projection(self, name: str) -> None:
        """Delete a projection from the database.

        Parameters
        ----------
        name : str
            The name of the projection to delete.

        Raises
        ------
        ValueError
            If the projection does not exist.
            If the projection is used in a scenario.
        """
        self.database.projections.delete(name)

    def copy_projection(
        self, old_name: str, new_name: str, new_description: str
    ) -> None:
        """Copy a projection in the database.

        Parameters
        ----------
        old_name : str
            The name of the projection to copy.
        new_name : str
            The name of the new projection.
        new_description : str
            The description of the new projection
        """
        self.database.projections.copy(old_name, new_name, new_description)

    def get_slr_scn_names(
        self,
    ) -> list:
        """
        Get all sea level rise scenario names from the database.

        Returns
        -------
        names : List[str]
            List of scenario names
        """
        return self.database.static.get_slr_scn_names()

    def interp_slr(self, slr_scenario: str, year: float) -> float:
        """
        Interpolate sea level rise for a given scenario and year.

        Parameters
        ----------
        slr_scenario : str
            The name of the sea level rise scenario.
        year : float
            The year to interpolate sea level rise for.

        Returns
        -------
        interpolated : float
            The interpolated sea level rise for the given scenario and year.
        """
        return self.database.interp_slr(slr_scenario, year)

    def plot_slr_scenarios(self) -> str:
        """
        Plot sea level rise scenarios.

        Returns
        -------
        html_path : str
            The path to the html plot of the sea level rise scenarios.
        """
        return self.database.plot_slr_scenarios()

    # Scenarios
    def get_scenarios(self) -> dict[str, Any]:
        """Get all scenarios from the database.

        Returns
        -------
        scenarios : dict[str, Any]
            A dictionary containing all scenarios.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'.
            Each value is a list of the corresponding attribute for each scenario.
        """
        return self.database.scenarios.summarize_objects()

    def get_scenario(self, name: str) -> Scenario:
        """Get a scenario from the database by name.

        Parameters
        ----------
        name : str
            The name of the scenario to retrieve.

        Returns
        -------
        scenario : Scenario
            The scenario object with the given name.

        Raises
        ------
        ValueError
            If the scenario with the given name does not exist.
        """
        return self.database.scenarios.get(name)

    def create_scenario(self, attrs: dict[str, Any]) -> Scenario:
        """Create a new scenario object.

        Parameters
        ----------
        attrs : dict[str, Any]
            The attributes of the scenario object to create. Should adhere to the Scenario schema.

        Returns
        -------
        scenario : Scenario
            The scenario object created from the attributes.

        Raises
        ------
        ValueError
            If the attributes do not adhere to the Scenario schema.
        """
        return Scenario(**attrs)

    def save_scenario(self, scenario: Scenario) -> tuple[bool, str]:
        """Save the scenario to the database.

        Parameters
        ----------
        scenario : Scenario
            The scenario to save.

        Returns
        -------
        run_success : bool
            Whether the scenario was saved successfully.
        error_msg : str
            The error message if the scenario was not saved successfully.
        """
        try:
            self.database.scenarios.save(scenario)
            return True, ""
        except Exception as e:
            return False, str(e)

    def edit_scenario(self, scenario: Scenario) -> None:
        """Edit a scenario object in the database.

        Parameters
        ----------
        scenario : Scenario
            The scenario object to edit.

        Raises
        ------
        ValueError
            If the scenario object does not exist.
        """
        self.database.scenarios.edit(scenario)

    def delete_scenario(self, name: str) -> None:
        """Delete a scenario from the database.

        Parameters
        ----------
        name : str
            The name of the scenario to delete.

        Raises
        ------
        ValueError
            If the scenario does not exist.
        """
        self.database.scenarios.delete(name)

    def run_scenario(self, scenario_name: Union[str, list[str]]) -> None:
        """Run a scenario hazard and impacts.

        Parameters
        ----------
        scenario_name : Union[str, list[str]]
            name(s) of the scenarios to run.

        Raises
        ------
        RuntimeError
            If an error occurs while running one of the scenarios
        """
        if not isinstance(scenario_name, list):
            scenario_name = [scenario_name]

        for scn in scenario_name:
            scenario = self.get_scenario(scn)
            runner = ScenarioRunner(self.database, scenario=scenario)
            runner.run()

    # Outputs
    def get_completed_scenarios(
        self,
    ) -> dict[str, Any]:
        """Get all completed scenarios from the database.

        Returns
        -------
        scenarios : dict[str, Any]
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
        topo_path : str
            The path to the topobathy file.

        """
        return self.database.get_topobathy_path()

    def get_index_path(self) -> str:
        """
        Return the path of the index tiles which are used to connect each water level cell with the topobathy tiles.

        Returns
        -------
        index_path : str
            The path to the index file.
        """
        return self.database.get_index_path()

    def get_depth_conversion(self) -> float:
        """
        Return the flood depth conversion that is need in the gui to plot the flood map.

        Returns
        -------
        fdc : float
            The flood depth conversion.
        """
        return self.database.get_depth_conversion()

    def get_max_water_level_map(self, name: str, rp: int = None) -> np.ndarray:
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
        water_level_map : np.ndarray
            2D gridded map with the maximum waterlevels for each cell.
        """
        return self.database.get_max_water_level(name, rp)

    def get_building_footprint_impacts(self, name: str) -> gpd.GeoDataFrame:
        """
        Return a geodataframe of the impacts at the footprint level.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        footprints : gpd.GeoDataFrame
            The impact footprints for the scenario.
        """
        return self.database.get_building_footprints(name)

    def get_aggregated_impacts(self, name: str) -> dict[str, gpd.GeoDataFrame]:
        """
        Return a dictionary with the aggregated impacts as geodataframes.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        aggr_impacts : dict[str, gpd.GeoDataFrame]
            The aggregated impacts for the scenario.
        """
        return self.database.get_aggregation(name)

    def get_road_impacts(self, name: str) -> gpd.GeoDataFrame:
        """
        Return a geodataframe of the impacts at roads.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        roads : gpd.GeoDataFrame
            The impacted roads for the scenario.
        """
        return self.database.get_roads(name)

    def get_obs_point_timeseries(self, name: str) -> gpd.GeoDataFrame:
        """Return the HTML strings of the water level timeseries for the given scenario.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        html_path : str
            The HTML strings of the water level timeseries
        """
        # Get the impacts objects from the scenario
        scenario = self.database.scenarios.get(name)
        hazard = Impacts(scenario).hazard

        # Check if the scenario has run
        if not hazard.has_run:
            raise ValueError(
                f"Scenario {name} has not been run. Please run the scenario first."
            )

        output_path = self.database.scenarios.output_path.joinpath(hazard.name)
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
        html: str
            The HTML string of the infographic.
        """
        # Get the impacts objects from the scenario
        database = self.database
        scn = database.scenarios.get(name)
        impact = Impacts(scenario=scn)
        event_mode = self.database.events.get(scn.event).mode

        # Check if the scenario has run
        if not impact.has_run_check():
            raise ValueError(
                f"Scenario {name} has not been run. Please run the scenario first."
            )

        config_path = database.static_path.joinpath("templates", "infographics")
        output_path = database.scenarios.output_path.joinpath(impact.name)
        metrics_outputs_path = output_path.joinpath(f"Infometrics_{impact.name}.csv")

        infographic_path = InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=event_mode,
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
        metrics: pd.DataFrame
            The metrics for the scenario.

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
    def get_aggregation_areas(
        self,
    ) -> dict[str, gpd.GeoDataFrame]:
        """Get a list of the aggregation areas that are provided in the site configuration.

        These are expected to much the ones in the FIAT model.

        Returns
        -------
        aggregation_areas : dict[str, GeoDataFrame]
            list of geodataframes with the polygons defining the aggregation areas
        """
        return self.database.static.get_aggregation_areas()

    def get_obs_points(
        self,
    ) -> gpd.GeoDataFrame:
        """Get the observation points specified in the site.toml.

        These are also added to the flood hazard model. They are used as marker locations to plot water level time series in the output tab.

        Returns
        -------
        observation_points : gpd.GeoDataFrame
            gpd.GeoDataFrame with observation points from the site.toml.
        """
        return self.database.static.get_obs_points()

    def get_model_boundary(
        self,
    ) -> gpd.GeoDataFrame:
        """Get the model boundary that is used in SFINCS.

        Returns
        -------
        model_boundary : GeoDataFrame
            GeoDataFrame with the model boundary
        """
        return self.database.static.get_model_boundary()

    def get_model_grid(
        self,
    ) -> QuadtreeGrid:
        """Get the model grid that is used in SFINCS.

        Returns
        -------
        grid : QuadtreeGrid
            QuadtreeGrid with the model grid
        """
        return self.database.static.get_model_grid()

    def get_svi_map(
        self,
    ) -> Union[gpd.GeoDataFrame, None]:
        """Get the SVI map that are used in Fiat.

        Returns
        -------
        svi_map : gpd.GeoDataFrame
            gpd.GeoDataFrames with the SVI map, None if not available
        """
        if self.database.site.fiat.config.svi:
            return self.database.static.get_static_map(
                self.database.site.fiat.config.svi.geom
            )
        else:
            return None

    def get_static_map(self, path: Union[str, Path]) -> Union[gpd.GeoDataFrame, None]:
        """Get a static map from the database.

        Parameters
        ----------
        path : Union[str, Path]
            path to the static map

        Returns
        -------
        static_map : Union[gpd.GeoDataFrame, None]
            gpd.GeoDataFrame with the static map if available, None if not found
        """
        try:
            return self.database.static.get_static_map(path)
        except FileNotFoundError:
            self.logger.warning(f"Static map {path} not found.")
            return None

    def get_building_geometries(self) -> gpd.GeoDataFrame:
        """Get the buildings exposure that are used in Fiat.

        Returns
        -------
        buildings : gpd.GeoDataFrame
            gpd.GeoDataFrames with the buildings from FIAT exposure
        """
        return self.database.static.get_buildings()

    def get_building_types(self) -> list:
        """Get the building types/categories that are used in the exposure.

        These are used to filter the buildings in the FIAT model, and can include types like:
        'Residential', 'Commercial', 'Industrial', etc.

        Returns
        -------
        building_types: list[str]
            list of building types
        """
        return self.database.static.get_property_types()

    # Benefits
    def get_benefits(self) -> dict[str, Any]:
        """Get all benefits from the database.

        Returns
        -------
        benefits : dict[str, Any]
            A dictionary containing all benefits.
            Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
            Each value is a list of the corresponding attribute for each benefit.
        """
        # sorting and filtering either with PyQt table or in the API
        return self.database.benefits.summarize_objects()

    def get_benefit(self, name: str) -> Benefit:
        """Get a benefit from the database by name.

        Parameters
        ----------
        name : str
            The name of the benefit to retrieve.

        Returns
        -------
        benefit: Benefit
            The benefit object with the given name. See [Benefit](/api_ref/) for details.

        Raises
        ------
        ValueError
            If the benefit with the given name does not exist.
        """
        return self.database.benefits.get(name)

    def create_benefit(self, attrs: dict[str, Any]) -> Benefit:
        """Create a new benefit object.

        Parameters
        ----------
        attrs : dict[str, Any]
            The attributes of the benefit object to create. Should adhere to the Benefit schema.

        Returns
        -------
        benefit : Benefit
            The benefit object created from the attributes.

        Raises
        ------
        ValueError
            If the attributes do not adhere to the Benefit schema.
        """
        return Benefit(**attrs)

    def save_benefit(self, benefit: Benefit) -> None:
        """Save a benefit object to the database.

        Parameters
        ----------
        benefit : Benefit
            The benefit object to save.

        Raises
        ------
        ValueError
            If the benefit object is not valid.
        """
        self.database.benefits.save(benefit)

    def edit_benefit(self, benefit: Benefit) -> None:
        """Edit a benefit object in the database.

        Parameters
        ----------
        benefit : Benefit
            The benefit object to edit.

        Raises
        ------
        ValueError
            If the benefit object does not exist.
        """
        self.database.benefits.edit(benefit)

    def delete_benefit(self, name: str) -> None:
        """Delete a benefit object from the database.

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

    def check_benefit_scenarios(self, benefit: Benefit) -> pd.DataFrame:
        """Return a dataframe with the scenarios needed for this benefit assessment run.

        Parameters
        ----------
        benefit : Benefit
            The benefit object to check.

        Returns
        -------
        scenarios : pd.DataFrame
            A dataframe with the scenarios needed for this benefit assessment run.
        """
        return self.database.check_benefit_scenarios(benefit)

    def create_benefit_scenarios(self, benefit: Benefit):
        """Create the benefit scenarios.

        Parameters
        ----------
        benefit : Benefit
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

    def get_aggregated_benefits(self, name: str) -> dict[str, gpd.GeoDataFrame]:
        """Get the aggregation benefits for a benefit assessment.

        Parameters
        ----------
        name : str
            The name of the benefit assessment.

        Returns
        -------
        aggregated_benefits : gpd.GeoDataFrame
            The aggregation benefits for the benefit assessment.
        """
        return self.database.get_aggregation_benefits(name)
