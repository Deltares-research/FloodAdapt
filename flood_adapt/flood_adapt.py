from pathlib import Path
from typing import Any, Literal

import geopandas as gpd
import numpy as np
import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader
from hydromt_sfincs.quadtree import QuadtreeGrid

from flood_adapt.adapter import SfincsAdapter
from flood_adapt.config.settings import Settings
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
from flood_adapt.workflows.benefit_runner import BenefitRunner
from flood_adapt.workflows.scenario_runner import ScenarioRunner

logger = FloodAdaptLogging.getLogger()


class FloodAdapt:
    database: Database

    def __init__(self, database_path: Path) -> None:
        """Initialize the FloodAdapt class with a database path.

        Parameters
        ----------
        database_path : Path
            The path to the database file.
        """
        self._settings = Settings(
            DATABASE_ROOT=database_path.parent,
            DATABASE_NAME=database_path.name,
        )
        self._settings.export_to_env()
        self.database = Database(
            database_root=database_path.parent,
            database_name=database_path.name,
            settings=self._settings,
        )

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
        DatabaseError
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

        Raises
        ------
        ValueError
            If the type is not valid or if the attributes do not adhere to the Measure schema.
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
        overwrite : bool, optional
            Whether to overwrite an existing measure with the same name (default is False).

        Raises
        ------
        DatabaseError
            If the measure object is not valid.
        """
        self.database.measures.add(measure, overwrite=overwrite)
        self.database.measures.flush()

    def delete_measure(self, name: str) -> None:
        """Delete an measure from the database.

        Parameters
        ----------
        name : str
            The name of the measure to delete.

        Raises
        ------
        DatabaseError
            If the measure does not exist.
        """
        self.database.measures.delete(name)
        self.database.measures.flush()

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
        self.database.measures.flush()

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
        DatabaseError
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
            If attrs does not adhere to the Strategy schema.
        """
        return Strategy(**attrs)

    def save_strategy(self, strategy: Strategy, overwrite: bool = False) -> None:
        """
        Save a strategy object to the database.

        Parameters
        ----------
        strategy : Strategy
            The strategy object to save.
        overwrite : bool, optional
            Whether to overwrite an existing strategy with the same name (default is False).

        Raises
        ------
        DatabaseError
            If the strategy object is not valid.
            If the strategy object already exists.
        """
        self.database.strategies.add(strategy, overwrite=overwrite)
        self.database.strategies.flush()

    def delete_strategy(self, name: str) -> None:
        """
        Delete a strategy from the database.

        Parameters
        ----------
        name : str
            The name of the strategy to delete.

        Raises
        ------
        DatabaseError
            If the strategy does not exist.
        """
        self.database.strategies.delete(name)
        self.database.strategies.flush()

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
        self.database.strategies.flush()

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
        event: Event | EventSet
            The event with the given name.

        Raises
        ------
        DatabaseError
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

        Raises
        ------
        ValueError
            If the attributes do not adhere to the Event schema.
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

        Raises
        ------
        ValueError
            If the attributes do not adhere to the EventSet schema.
        """
        return EventSet(**attrs, sub_events=sub_events)

    def save_event(self, event: Event, overwrite: bool = False) -> None:
        """Save an event object to the database.

        Parameters
        ----------
        event : Event
            The event object to save.
        overwrite : bool, optional
            Whether to overwrite an existing event with the same name (default is False).

        Raises
        ------
        DatabaseError
            If the event object is not valid.
        """
        self.database.events.add(event, overwrite=overwrite)
        self.database.events.flush()

    def delete_event(self, name: str) -> None:
        """Delete an event from the database.

        Parameters
        ----------
        name : str
            The name of the event to delete.

        Raises
        ------
        DatabaseError
            If the event does not exist.
            If the event is used in a scenario.
        """
        self.database.events.delete(name)
        self.database.events.flush()

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
        self.database.events.flush()

    def plot_event_forcing(
        self, event: Event, forcing_type: ForcingType
    ) -> tuple[str, list[Exception] | None]:
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
        DatabaseError
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
        DatabaseError
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

    def save_projection(self, projection: Projection, overwrite: bool = False) -> None:
        """Save a projection object to the database.

        Parameters
        ----------
        projection : Projection
            The projection object to save.
        overwrite : bool, optional
            Whether to overwrite an existing projection with the same name (default is False).

        Raises
        ------
        DatabaseError
            If the projection object is not valid.
        """
        self.database.projections.add(projection, overwrite=overwrite)
        self.database.projections.flush()

    def delete_projection(self, name: str) -> None:
        """Delete a projection from the database.

        Parameters
        ----------
        name : str
            The name of the projection to delete.

        Raises
        ------
        DatabaseError
            If the projection does not exist.
            If the projection is used in a scenario.
        """
        self.database.projections.delete(name)
        self.database.projections.flush()

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
        self.database.projections.flush()

    def get_slr_scn_names(self) -> list:
        """
        Get all sea level rise scenario names from the database.

        Returns
        -------
        names : list[str]
            list of scenario names
        """
        return self.database.static.get_slr_scn_names()

    def interp_slr(self, slr_scenario: str, year: float) -> float:
        """Interpolate SLR value and reference it to the SLR reference year from the site toml.

        Parameters
        ----------
        slr_scenario : str
            SLR scenario name from the coulmn names in static/slr/slr.csv
        year : float
            year to evaluate

        Returns
        -------
        interpolated : float
            The interpolated sea level rise for the given scenario and year.

        Raises
        ------
        ValueError
            if the reference year is outside of the time range in the slr.csv file
        ValueError
            if the year to evaluate is outside of the time range in the slr.csv file
        """
        return self.database.get_slr_scenarios().interp_slr(
            scenario=slr_scenario,
            year=year,
            units=self.database.site.gui.units.default_length_units,
        )

    def plot_slr_scenarios(self) -> str:
        """
        Plot sea level rise scenarios.

        Returns
        -------
        html_path : str
            The path to the html plot of the sea level rise scenarios.
        """
        return self.database.get_slr_scenarios().plot_slr_scenarios(
            scenario_names=self.database.static.get_slr_scn_names(),
            output_loc=self.database.input_path.parent.joinpath("temp", "slr.html"),
            units=self.database.site.gui.units.default_length_units,
        )

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
        DatabaseError
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

    def save_scenario(self, scenario: Scenario, overwrite: bool = False) -> None:
        """Save the scenario to the database.

        Parameters
        ----------
        scenario : Scenario
            The scenario to save.
        overwrite : bool, optional
            Whether to overwrite an existing scenario with the same name (default is False).

        Raises
        ------
        DatabaseError
            If the scenario object is not valid or if it already exists and overwrite is False.

        """
        self.database.scenarios.add(scenario, overwrite=overwrite)
        self.database.scenarios.flush()

    def delete_scenario(self, name: str) -> None:
        """Delete a scenario from the database.

        Parameters
        ----------
        name : str
            The name of the scenario to delete.

        Raises
        ------
        DatabaseError
            If the scenario does not exist.
        """
        self.database.scenarios.delete(name)
        self.database.scenarios.flush()

    def run_scenario(self, scenario_name: str | list[str]) -> None:
        """Run a scenario hazard and impacts.

        Parameters
        ----------
        scenario_name : str | list[str]
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
            ScenarioRunner(self.database, scenario=scenario).run()

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

    def get_max_water_level_map(self, name: str, rp: int | None = None) -> np.ndarray:
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

    def get_flood_map_geotiff(self, name: str, rp: int | None = None) -> Path | None:
        """
        Return the path to the geotiff file with the flood map for the given scenario.

        Parameters
        ----------
        name : str
            The name of the scenario.
        rp : int, optional
            The return period of the water level, by default None. Only for event set scenarios.

        Returns
        -------
        flood_map_geotiff : Path | None
            The path to the geotiff file with the flood map for the scenario if it exists, otherwise None.
        """
        return self.database.get_flood_map_geotiff(name, rp)

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

    def get_obs_point_timeseries(self, name: str) -> gpd.GeoDataFrame | None:
        """Return the HTML strings of the water level timeseries for the given scenario.

        Parameters
        ----------
        name : str
            The name of the scenario.

        Returns
        -------
        gdf : GeoDataFrame, optional
            A GeoDataFrame with the observation points and their corresponding HTML paths for the timeseries.
            Each row contains the station name and the path to the HTML file with the timeseries.
            None if no observation points are found or if the scenario has not been run yet.
        """
        obs_points = self.database.static.get_obs_points()
        if obs_points is None:
            logger.info(
                "No observation points found in the sfincs model and site configuration."
            )
            return None

        # Get the impacts objects from the scenario
        scenario = self.database.scenarios.get(name)

        # Check if the scenario has run
        if not ScenarioRunner(self.database, scenario=scenario).has_run_check():
            logger.info(
                f"Cannot retrieve observation point timeseries as the scenario {name} has not been run yet."
            )
            return None

        output_path = self.database.get_flooding_path(scenario.name)
        obs_points["html"] = [
            (output_path / f"{station}_timeseries.html").as_posix()
            for station in obs_points.name
        ]

        return obs_points

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
        event_mode = self.database.events.get(scn.event).mode

        # Check if the scenario has run
        if not self.database.scenarios.has_run_check(scn.name):
            raise ValueError(
                f"Scenario {name} has not been run. Please run the scenario first."
            )

        config_path = database.static_path.joinpath("templates", "infographics")
        output_path = database.scenarios.output_path.joinpath(scn.name)
        metrics_outputs_path = output_path.joinpath(f"Infometrics_{scn.name}.csv")

        infographic_path = InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=event_mode,
            scenario_name=scn.name,
            metrics_full_path=metrics_outputs_path,
            config_base_path=config_path,
            output_base_path=output_path,
        ).get_infographics_html()

        return infographic_path

    def get_infometrics(self, name: str, aggr_name: str | None = None) -> pd.DataFrame:
        """Return the infometrics DataFrame for the given scenario and optional aggregation.

        Parameters
        ----------
        name : str
            The name of the scenario.
        aggr_name : str | None, default None
            The name of the aggregation, if any.

        Returns
        -------
        df : pd.DataFrame
            The infometrics DataFrame for the scenario (and aggregation if specified).

        Raises
        ------
        FileNotFoundError
            If the metrics file does not exist for the given scenario (and aggregation).
        """
        if aggr_name is not None:
            fn = f"Infometrics_{name}_{aggr_name}.csv"
        else:
            fn = f"Infometrics_{name}.csv"
        # Create the infographic path
        metrics_path = self.database.scenarios.output_path.joinpath(name, fn)

        # Check if the file exists
        if not metrics_path.exists():
            raise FileNotFoundError(
                f"The metrics file for scenario {name}({metrics_path.as_posix()}) does not exist."
            )
        # Read the metrics file
        df = MetricsFileReader(metrics_path.as_posix()).read_metrics_from_file(
            include_long_names=True,
            include_description=True,
            include_metrics_table_selection=True,
            include_metrics_map_selection=True,
        )
        if aggr_name is not None:
            df = df.T
        return df

    def get_aggr_metric_layers(
        self,
        name: str,
        aggr_type: str,
        type: Literal["single_event", "risk"] = "single_event",
        rp: int | None = None,
        equity: bool = False,
    ) -> list[dict]:
        # Read infometrics from csv file
        metrics_df = self.get_infometrics(name, aggr_name=aggr_type)

        # Filter based on "Show in Metrics Map" column
        if "Show In Metrics Map" in metrics_df.index:
            mask = metrics_df.loc["Show In Metrics Map"].to_numpy().astype(bool)
            metrics_df = metrics_df.loc[:, mask]

        # Keep only relevant attributes of the infometrics
        keep_rows = [
            "Description",
            "Long Name",
            "Show In Metrics Table",
            "Show In Metrics Map",
        ]
        metrics_df = metrics_df.loc[
            [row for row in keep_rows if row in metrics_df.index]
        ]

        # Transform to list of dicts
        metrics = []
        for col in metrics_df.columns:
            metric_dict = {"name": col}
            # Add the first 4 rows as key-value pairs
            for i, idx in enumerate(metrics_df.index):
                metric_dict[idx] = metrics_df.loc[idx, col]
            metrics.append(metric_dict)

        # Get the filtered metrics layers from the GUI configuration
        filtered_metrics = self.database.site.gui.output_layers.get_aggr_metrics_layers(
            metrics, type, rp, equity
        )

        return filtered_metrics

    # Static
    def load_static_data(self):
        """Read the static data into the cache.

        This is used to speed up the loading of the static data.
        """
        self.database.static.load_static_data()

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
    ) -> gpd.GeoDataFrame | None:
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

    def get_static_map(self, path: str | Path) -> gpd.GeoDataFrame:
        """Get a static map from the database.

        Parameters
        ----------
        path : str | Path
            path to the static map

        Returns
        -------
        static_map : gpd.GeoDataFrame
            gpd.GeoDataFrame with the static map

        Raises
        ------
        DatabaseError
            If the static map with the given path does not exist.
        """
        return self.database.static.get_static_map(path)

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
        DatabaseError
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

    def save_benefit(self, benefit: Benefit, overwrite: bool = False) -> None:
        """Save a benefit object to the database.

        Parameters
        ----------
        benefit : Benefit
            The benefit object to save.
        overwrite : bool, optional
            Whether to overwrite an existing benefit with the same name (default is False).

        Raises
        ------
        DatabaseError
            If the benefit object is not valid.
        """
        self.database.benefits.add(benefit, overwrite=overwrite)
        self.database.benefits.flush()

    def delete_benefit(self, name: str) -> None:
        """Delete a benefit object from the database.

        Parameters
        ----------
        name : str
            The name of the benefit object to delete.

        Raises
        ------
        DatabaseError
            If the benefit object does not exist.
        """
        self.database.benefits.delete(name)
        self.database.benefits.flush()

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
        return BenefitRunner(self.database, benefit=benefit).scenarios

    def create_benefit_scenarios(self, benefit: Benefit) -> None:
        """Create the benefit scenarios.

        Parameters
        ----------
        benefit : Benefit
            The benefit object to create scenarios for.
        """
        BenefitRunner(self.database, benefit=benefit).create_benefit_scenarios()

    def run_benefit(self, name: str | list[str]) -> None:
        """Run the benefit assessment.

        Parameters
        ----------
        name : str | list[str]
            The name of the benefit object to run.
        """
        if not isinstance(name, list):
            benefit_name = [name]
        for name in benefit_name:
            benefit = self.database.benefits.get(name)
            BenefitRunner(self.database, benefit=benefit).run_cost_benefit()

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

    def save_flood_animation(
        self, scenario: str, bbox: list[float] | None = None, zoomlevel: int = 15
    ) -> str:
        """Create an animation of the flood extent over time.

        Produced floodmap is in the units defined in the sfincs config settings.

        Parameters
        ----------
        scenario : str
            Name of the scenario for which to create the floodmap.
        bbox : list[float], optional
            Bounding box to limit the animation to a specific area (default is None, which means no bounding box).
            Format: [lon_min, lat_min, lon_max, lat_max]
        zoomlevel : int, optional
            Zoom level for the animation (default is 15).
        """
        scn = self.get_scenario(scenario)
        results_path = self.database.scenarios.output_path / scn.name / "Flooding"
        sim_path = (
            results_path
            / "simulations"
            / self.database.site.sfincs.config.overland_model.name
        )

        vmin = 0
        vmax = self.database.site.gui.output_layers.floodmap.bins[-1]

        if not sim_path.exists():
            raise FileNotFoundError(
                "Flood simulation path does not exist."
                "This is required to make an animation."
                "In order to save the simulation folder, the config.sfincs.simulation setting must be set to True and the scenario must be run again."
            )

        with SfincsAdapter(model_root=sim_path) as model:
            animation_path = model.create_animation(
                scenario=scn, bbox=bbox, zoomlevel=zoomlevel, vmin=vmin, vmax=vmax
            )

        return animation_path

    def cleanup(self):
        self.database.cleanup()
        self.database.static.stop_docker()

    ## DOCKER
    def __del__(self):
        self.cleanup()
