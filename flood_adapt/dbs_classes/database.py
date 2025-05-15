import gc
import os
import shutil
import time
from pathlib import Path
from typing import Any, Literal, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from cht_cyclones.tropical_cyclone import TropicalCyclone
from geopandas import GeoDataFrame
from plotly.express import line
from plotly.express.colors import sample_colorscale

from flood_adapt.config.config import Settings
from flood_adapt.config.site import Site
from flood_adapt.dbs_classes.dbs_benefit import DbsBenefit
from flood_adapt.dbs_classes.dbs_event import DbsEvent
from flood_adapt.dbs_classes.dbs_measure import DbsMeasure
from flood_adapt.dbs_classes.dbs_projection import DbsProjection
from flood_adapt.dbs_classes.dbs_scenario import DbsScenario
from flood_adapt.dbs_classes.dbs_static import DbsStatic
from flood_adapt.dbs_classes.dbs_strategy import DbsStrategy
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.path_builder import (
    TopLevelDir,
    db_path,
)
from flood_adapt.misc.utils import finished_file_exists
from flood_adapt.objects.benefits.benefits import Benefit
from flood_adapt.objects.events.events import Event
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.benefit_runner import BenefitRunner
from flood_adapt.workflows.scenario_runner import ScenarioRunner


class Database(IDatabase):
    """Implementation of IDatabase class that holds the site information and has methods to get static data info, and all the input information.

    Additionally it can manipulate (add, edit, copy and delete) any of the objects in the input.
    """

    _instance = None

    database_path: Union[str, os.PathLike]
    database_name: str
    _init_done: bool = False

    base_path: Path
    input_path: Path
    static_path: Path
    output_path: Path

    _site: Site

    _events: DbsEvent
    _scenarios: DbsScenario
    _strategies: DbsStrategy
    _measures: DbsMeasure
    _projections: DbsProjection
    _benefits: DbsBenefit

    _static: DbsStatic

    def __new__(cls, *args, **kwargs):
        if not cls._instance:  # Singleton pattern
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        database_path: Union[str, os.PathLike, None] = None,
        database_name: Optional[str] = None,
    ) -> None:
        """
        Initialize the DatabaseController object.

        Parameters
        ----------
        database_path : Union[str, os.PathLike]
            The path to the database root
        database_name : str
            The name of the database.
        -----
        """
        if database_path is None or database_name is None:
            if not self._init_done:
                raise ValueError(
                    """Database path and name must be provided for the first initialization.
                    To do this, run `flood_adapt.api.static.read_database(database_path, site_name)` first."""
                )
            else:
                return  # Skip re-initialization

        if (
            self._init_done
            and self.database_path == database_path
            and self.database_name == database_name
        ):
            return  # Skip re-initialization

        # If the database is not initialized, or a new path or name is provided, (re-)initialize
        re_option = "re-" if self._init_done else ""
        self.logger = FloodAdaptLogging.getLogger("Database")
        self.logger.info(
            f"{re_option}initializing database to {database_name} at {database_path}".capitalize()
        )
        self.database_path = database_path
        self.database_name = database_name

        # Set the paths

        self.base_path = Path(database_path) / database_name
        self.input_path = db_path(TopLevelDir.input)
        self.static_path = db_path(TopLevelDir.static)
        self.output_path = db_path(TopLevelDir.output)

        self._site = Site.load_file(self.static_path / "config" / "site.toml")

        # Initialize the different database objects
        self._static = DbsStatic(self)
        self._events = DbsEvent(self)
        self._scenarios = DbsScenario(self)
        self._strategies = DbsStrategy(self)
        self._measures = DbsMeasure(self)
        self._projections = DbsProjection(self)
        self._benefits = DbsBenefit(self)

        # Delete any unfinished/crashed scenario output
        self.cleanup()

        self._init_done = True

    def shutdown(self):
        """Explicitly shut down the singleton and clear all references."""
        import gc

        self._instance = None
        self._init_done = False

        self.__class__._instance = None
        self.__dict__.clear()
        gc.collect()

    # Property methods
    @property
    def site(self) -> Site:
        return self._site

    @property
    def static(self) -> DbsStatic:
        return self._static

    @property
    def events(self) -> DbsEvent:
        return self._events

    @property
    def scenarios(self) -> DbsScenario:
        return self._scenarios

    @property
    def strategies(self) -> DbsStrategy:
        return self._strategies

    @property
    def measures(self) -> DbsMeasure:
        return self._measures

    @property
    def projections(self) -> DbsProjection:
        return self._projections

    @property
    def benefits(self) -> DbsBenefit:
        return self._benefits

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
        float
            _description_

        Raises
        ------
        ValueError
            if the reference year is outside of the time range in the slr.csv file
        ValueError
            if the year to evaluate is outside of the time range in the slr.csv file
        """
        if self.site.sfincs.slr_scenarios is None:
            raise ValueError("No SLR scenarios defined in the site configuration.")

        input_file = self.static_path / self.site.sfincs.slr_scenarios.file
        df = pd.read_csv(input_file)
        if year > df["year"].max() or year < df["year"].min():
            raise ValueError(
                "The selected year is outside the range of the available SLR scenarios"
            )
        else:
            slr = np.interp(year, df["year"], df[slr_scenario])
            ref_year = self.site.sfincs.slr_scenarios.relative_to_year
            if ref_year > df["year"].max() or ref_year < df["year"].min():
                raise ValueError(
                    f"The reference year {ref_year} is outside the range of the available SLR scenarios"
                )
            else:
                ref_slr = np.interp(ref_year, df["year"], df[slr_scenario])
                new_slr = us.UnitfulLength(
                    value=slr - ref_slr,
                    units=df["units"][0],
                )
                gui_units = self.site.gui.units.default_length_units
                return np.round(new_slr.convert(gui_units), decimals=2)

    # TODO: should probably be moved to frontend
    def plot_slr_scenarios(self) -> str:
        if self.site.sfincs.slr_scenarios is None:
            raise ValueError("No SLR scenarios defined in the site configuration.")
        input_file = self.input_path.parent.joinpath(
            "static", self.site.sfincs.slr_scenarios.file
        )
        df = pd.read_csv(input_file)
        ncolors = len(df.columns) - 2
        if "units" not in df.columns:
            raise ValueError(f"Expected column `units` in {input_file}.")

        units = df["units"].iloc[0]
        units = us.UnitTypesLength(units)

        if "Year" not in df.columns:
            if "year" not in df.columns:
                raise ValueError(f"Expected column `year` in {input_file}.")
            else:
                df = df.rename(columns={"year": "Year"})

        ref_year = self.site.sfincs.slr_scenarios.relative_to_year
        if ref_year > df["Year"].max() or ref_year < df["Year"].min():
            raise ValueError(
                f"The reference year {ref_year} is outside the range of the available SLR scenarios"
            )
        else:
            scenarios = self._static.get_slr_scn_names()
            for scn in scenarios:
                ref_slr = np.interp(ref_year, df["Year"], df[scn])
                df[scn] -= ref_slr

        df = df.drop(columns="units").melt(id_vars=["Year"]).reset_index(drop=True)
        # convert to units used in GUI
        slr_current_units = us.UnitfulLength(value=1.0, units=units)
        conversion_factor = slr_current_units.convert(
            self.site.gui.units.default_length_units
        )
        df.iloc[:, -1] = (conversion_factor * df.iloc[:, -1]).round(decimals=2)

        # rename column names that will be shown in html
        df = df.rename(
            columns={
                "variable": "Scenario",
                "value": f"Sea level rise [{self.site.gui.units.default_length_units.value}]",
            }
        )

        colors = sample_colorscale(
            "rainbow", [n / (ncolors - 1) for n in range(ncolors)]
        )
        fig = line(
            df,
            x="Year",
            y=f"Sea level rise [{self.site.gui.units.default_length_units.value}]",
            color="Scenario",
            color_discrete_sequence=colors,
        )

        # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

        fig.update_layout(
            autosize=False,
            height=100 * 1.2,
            width=280 * 1.3,
            margin={"r": 0, "l": 0, "b": 0, "t": 0},
            font={"size": 10, "color": "black", "family": "Arial"},
            title_font={"size": 10, "color": "black", "family": "Arial"},
            legend_font={"size": 10, "color": "black", "family": "Arial"},
            legend_grouptitlefont={"size": 10, "color": "black", "family": "Arial"},
            legend={"entrywidthmode": "fraction", "entrywidth": 0.2},
            yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            xaxis_title=None,
            xaxis_range=[ref_year, df["Year"].max()],
            legend_title=None,
            # paper_bgcolor="#3A3A3A",
            # plot_bgcolor="#131313",
        )

        # write html to results folder
        output_loc = self.input_path.parent.joinpath("temp", "slr.html")
        output_loc.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(output_loc)
        return str(output_loc)

    def write_to_csv(self, name: str, event: Event, df: pd.DataFrame):
        df.to_csv(
            self.events.input_path.joinpath(event.name, f"{name}.csv"),
            header=False,
        )

    def write_cyc(self, event: Event, track: TropicalCyclone):
        cyc_file = self.events.input_path / event.name / f"{event.track_name}.cyc"
        # cht_cyclone function to write TropicalCyclone as .cyc file
        track.write_track(filename=cyc_file, fmt="ddb_cyc")

    def check_benefit_scenarios(self, benefit: Benefit) -> pd.DataFrame:
        """Return a dataframe with the scenarios needed for this benefit assessment run.

        Parameters
        ----------
        benefit : Benefit
        """
        runner = BenefitRunner(self, benefit=benefit)
        return runner.check_scenarios()

    def create_benefit_scenarios(self, benefit: Benefit) -> None:
        """Create any scenarios that are needed for the (cost-)benefit assessment and are not there already.

        Parameters
        ----------
        benefit : Benefit
        """
        runner = BenefitRunner(self, benefit=benefit)
        runner.check_scenarios()

        # Iterate through the scenarios needed and create them if not existing
        for index, row in runner.scenarios.iterrows():
            if row["scenario created"] == "No":
                scenario_dict = {}
                scenario_dict["event"] = row["event"]
                scenario_dict["projection"] = row["projection"]
                scenario_dict["strategy"] = row["strategy"]
                scenario_dict["name"] = "_".join(
                    [row["projection"], row["event"], row["strategy"]]
                )

                scenario_obj = Scenario(**scenario_dict)
                # Check if scenario already exists (because it was created before in the loop)
                try:
                    self.scenarios.save(scenario_obj)
                except ValueError as e:
                    if "name is already used" not in str(e):
                        # some other error was raised, so we re-raise it
                        raise e
                    # otherwise, if it already exists and we dont need to save it, we can just continue

        # Update the scenarios check
        runner.check_scenarios()

    def run_benefit(self, benefit_name: Union[str, list[str]]) -> None:
        """Run a (cost-)benefit analysis.

        Parameters
        ----------
        benefit_name : Union[str, list[str]]
            name(s) of the benefits to run.
        """
        if not isinstance(benefit_name, list):
            benefit_name = [benefit_name]
        for name in benefit_name:
            benefit = self.benefits.get(name)
            runner = BenefitRunner(self, benefit=benefit)
            runner.run_cost_benefit()

    def get_outputs(self) -> dict[str, Any]:
        """Return a dictionary with info on the outputs that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'path', 'last_modification_date' and "finished" info
        """
        all_scenarios = pd.DataFrame(self._scenarios.summarize_objects())
        if len(all_scenarios) > 0:
            df = all_scenarios[all_scenarios["finished"]]
        else:
            df = all_scenarios
        finished = df.drop(columns="finished").reset_index(drop=True)
        return finished.to_dict()

    def get_topobathy_path(self) -> str:
        """Return the path of the topobathy tiles in order to create flood maps with water level maps.

        Returns
        -------
        str
            path to topobathy tiles
        """
        path = self.input_path.parent.joinpath("static", "dem", "tiles", "topobathy")
        return str(path)

    def get_index_path(self) -> str:
        """Return the path of the index tiles which are used to connect each water level cell with the topobathy tiles.

        Returns
        -------
        str
            path to index tiles
        """
        path = self.input_path.parent.joinpath("static", "dem", "tiles", "indices")
        return str(path)

    def get_depth_conversion(self) -> float:
        """Return the flood depth conversion that is need in the gui to plot the flood map.

        Returns
        -------
        float
            conversion factor
        """
        # Get conresion factor need to get from the sfincs units to the gui units
        units = us.UnitfulLength(
            value=1, units=self.site.gui.units.default_length_units
        )
        unit_cor = units.convert(new_units=us.UnitTypesLength.meters)

        return unit_cor

    def get_max_water_level(
        self,
        scenario_name: str,
        return_period: Optional[int] = None,
    ) -> np.ndarray:
        """Return an array with the maximum water levels during an event.

        Parameters
        ----------
        scenario_name : str
            name of scenario
        return_period : int, optional
            return period in years, by default None

        Returns
        -------
        np.array
            2D map of maximum water levels
        """
        # If single event read with hydromt-sfincs
        if not return_period:
            map_path = self.scenarios.output_path.joinpath(
                scenario_name,
                "Flooding",
                "max_water_level_map.nc",
            )
            with xr.open_dataarray(map_path) as map:
                zsmax = map.to_numpy()
        else:
            file_path = self.scenarios.output_path.joinpath(
                scenario_name,
                "Flooding",
                f"RP_{return_period:04d}_maps.nc",
            )
            with xr.open_dataset(file_path) as ds:
                zsmax = ds["risk_map"][:, :].to_numpy().T
        return zsmax

    def get_building_footprints(self, scenario_name: str) -> GeoDataFrame:
        """Return a geodataframe of the impacts at the footprint level.

        Parameters
        ----------
        scenario_name : str
            name of scenario

        Returns
        -------
        GeoDataFrame
            impacts at footprint level
        """
        out_path = self.scenarios.output_path.joinpath(scenario_name, "Impacts")
        footprints = out_path / f"Impacts_building_footprints_{scenario_name}.gpkg"
        gdf = gpd.read_file(footprints, engine="pyogrio")
        gdf = gdf.to_crs(4326)
        return gdf

    def get_roads(self, scenario_name: str) -> GeoDataFrame:
        """Return a geodataframe of the impacts at roads.

        Parameters
        ----------
        scenario_name : str
            name of scenario

        Returns
        -------
        GeoDataFrame
            Impacts at roads
        """
        out_path = self.scenarios.output_path.joinpath(scenario_name, "Impacts")
        roads = out_path / f"Impacts_roads_{scenario_name}.gpkg"
        gdf = gpd.read_file(roads, engine="pyogrio")
        gdf = gdf.to_crs(4326)
        return gdf

    def get_aggregation(self, scenario_name: str) -> dict[str, gpd.GeoDataFrame]:
        """Return a dictionary with the aggregated impacts as geodataframes.

        Parameters
        ----------
        scenario_name : str
            name of the scenario

        Returns
        -------
        dict[GeoDataFrame]
            dictionary with aggregated damages per aggregation type
        """
        out_path = self.scenarios.output_path.joinpath(scenario_name, "Impacts")
        gdfs = {}
        for aggr_area in out_path.glob(f"Impacts_aggregated_{scenario_name}_*.gpkg"):
            label = aggr_area.stem.split(f"{scenario_name}_")[-1]
            gdfs[label] = gpd.read_file(aggr_area, engine="pyogrio")
            gdfs[label] = gdfs[label].to_crs(4326)
        return gdfs

    def get_aggregation_benefits(
        self, benefit_name: str
    ) -> dict[str, gpd.GeoDataFrame]:
        """Get a dictionary with the aggregated benefits as geodataframes.

        Parameters
        ----------
        benefit_name : str
            name of the benefit analysis

        Returns
        -------
        dict[GeoDataFrame]
            dictionary with aggregated benefits per aggregation type
        """
        out_path = self.benefits.output_path.joinpath(
            benefit_name,
        )
        gdfs = {}
        for aggr_area in out_path.glob("benefits_*.gpkg"):
            label = aggr_area.stem.split("benefits_")[-1]
            gdfs[label] = gpd.read_file(aggr_area, engine="pyogrio")
            gdfs[label] = gdfs[label].to_crs(4326)
        return gdfs

    def get_object_list(
        self,
        object_type: Literal[
            "projections", "events", "measures", "strategies", "scenarios", "benefits"
        ],
    ) -> dict[str, Any]:
        """Get a dictionary with all the toml paths and last modification dates that exist in the database that correspond to object_type.

        Parameters
        ----------
        object_type : str
            Can be 'projections', 'events', 'measures', 'strategies' or 'scenarios'

        Returns
        -------
        dict[str, Any]
            Includes 'path' and 'last_modification_date' info
        """
        match object_type:
            case "projections":
                return self.projections.summarize_objects()
            case "events":
                return self.events.summarize_objects()
            case "measures":
                return self.measures.summarize_objects()
            case "strategies":
                return self.strategies.summarize_objects()
            case "scenarios":
                return self.scenarios.summarize_objects()
            case "benefits":
                return self.benefits.summarize_objects()
            case _:
                raise ValueError(
                    f"Object type '{object_type}' is not valid. Must be one of 'projections', 'events', 'measures', 'strategies' or 'scenarios'."
                )

    def has_run_hazard(self, scenario_name: str) -> None:
        """Check if there is already a simulation that has the exact same hazard component.

        If yes that is copied to avoid running the hazard model twice.

        Parameters
        ----------
        scenario_name : str
            name of the scenario to check if needs to be rerun for hazard
        """
        scenario = self.scenarios.get(scenario_name)
        runner = ScenarioRunner(self, scenario=scenario)

        # Dont do anything if the hazard model has already been run in itself
        if runner.impacts.hazard.has_run:
            return

        scenarios = [
            self.scenarios.get(scn)
            for scn in self.scenarios.summarize_objects()["name"]
        ]
        scns_simulated = [
            sim
            for sim in scenarios
            if self.scenarios.output_path.joinpath(sim.name, "Flooding").is_dir()
        ]

        for scn in scns_simulated:
            if self.scenarios.equal_hazard_components(scn, scenario):
                existing = self.scenarios.output_path.joinpath(scn.name, "Flooding")
                path_new = self.scenarios.output_path.joinpath(
                    scenario.name, "Flooding"
                )
                _runner = ScenarioRunner(self, scenario=scn)

                if _runner.impacts.hazard.has_run:  # only copy results if the hazard model has actually finished and skip simulation folders
                    shutil.copytree(
                        existing,
                        path_new,
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("simulations"),
                    )
                    self.logger.info(
                        f"Hazard simulation is used from the '{scn.name}' scenario"
                    )

    def cleanup(self) -> None:
        """
        Remove corrupted scenario output.

        This method removes any scenario output that:
            - is corrupted due to unfinished runs
            - does not have a corresponding input

        """
        if not Settings().delete_crashed_runs:
            return

        if not self.scenarios.output_path.is_dir():
            return

        input_scenarios = [
            (self.scenarios.input_path / dir).resolve()
            for dir in os.listdir(self.scenarios.input_path)
        ]
        output_scenarios = [
            (self.scenarios.output_path / dir).resolve()
            for dir in os.listdir(self.scenarios.output_path)
        ]

        def _call_garbage_collector(func, path, exc_info, retries=5, delay=0.1):
            """Retry deletion up to 5 times if the file is locked."""
            for attempt in range(retries):
                gc.collect()
                time.sleep(delay)
                try:
                    func(path)  # Retry deletion
                    return  # Exit if successful
                except Exception as e:
                    print(
                        f"Attempt {attempt + 1}/{retries} failed to delete {path}: {e}"
                    )

            print(f"Giving up on deleting {path} after {retries} attempts.")

        for dir in output_scenarios:
            # Delete if: input was deleted or corrupted output due to unfinished run
            if dir.name not in [
                path.name for path in input_scenarios
            ] or not finished_file_exists(dir):
                shutil.rmtree(dir, onerror=_call_garbage_collector)
