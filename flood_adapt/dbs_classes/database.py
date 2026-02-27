import gc
import os
import shutil
from pathlib import Path
from typing import Any, Literal, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from geopandas import GeoDataFrame

from flood_adapt.adapter.fiat_adapter import FiatAdapter
from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.config.config import Settings
from flood_adapt.config.hazard import SlrScenariosModel
from flood_adapt.config.impacts import FloodmapType
from flood_adapt.config.site import Site
from flood_adapt.dbs_classes.dbs_benefit import DbsBenefit
from flood_adapt.dbs_classes.dbs_event import DbsEvent
from flood_adapt.dbs_classes.dbs_measure import DbsMeasure
from flood_adapt.dbs_classes.dbs_projection import DbsProjection
from flood_adapt.dbs_classes.dbs_scenario import DbsScenario
from flood_adapt.dbs_classes.dbs_static import DbsStatic
from flood_adapt.dbs_classes.dbs_strategy import DbsStrategy
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.dbs_classes.interface.element import AbstractDatabaseElement
from flood_adapt.misc.exceptions import ConfigError, DatabaseError
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.utils import finished_file_exists
from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.events.events import Mode
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.output.floodmap import FloodMap
from flood_adapt.workflows.scenario_runner import ScenarioRunner

logger = FloodAdaptLogging.getLogger("Database")


class Database(IDatabase):
    """Implementation of IDatabase class that holds the site information and has methods to get static data info, and all the input information.

    Additionally it can manipulate (add, edit, copy and delete) any of the objects in the input.
    """

    _instance = None
    _init_done: bool = False
    _settings: Settings

    base_path: Path
    input_path: Path
    static_path: Path
    output_path: Path

    site: Site

    events: DbsEvent
    scenarios: DbsScenario
    strategies: DbsStrategy
    measures: DbsMeasure
    projections: DbsProjection
    benefits: DbsBenefit

    static: DbsStatic

    def __new__(cls, *args, **kwargs):
        if not cls._instance:  # Singleton pattern
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        database_root: Path | None = None,
        database_name: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        """
        Initialize the DatabaseController object.

        Parameters
        ----------
        database_root : Union[str, os.PathLike]
            The path to the database root
        database_name : str
            The name of the database.
        settings : Settings, optional
            Settings object to configure behavior, by default None

        -----
        """
        if database_root is None or database_name is None:
            if not self._init_done:
                raise DatabaseError(
                    "``database_root`` and ``database_name`` are required for the first initialization of the Database."
                )
            else:
                return  # Skip re-initialization

        if self._init_done and self.base_path == Path(database_root) / database_name:
            return  # Skip re-initialization

        # If the database is not initialized, or a new path or name is provided, (re-)initialize
        re_option = "re-" if self._init_done else ""
        logger.info(
            f"{re_option}initializing database to {database_name} at {database_root}".capitalize()
        )

        # Set the paths
        self.base_path = Path(database_root) / database_name
        self.input_path = self.base_path / "input"
        self.static_path = self.base_path / "static"
        self.output_path = self.base_path / "output"

        # Settings
        if settings is None:
            settings = Settings(
                DATABASE_ROOT=database_root, DATABASE_NAME=database_name
            )
            settings.export_to_env()
        self._settings = settings

        # Read site configuration
        self.read_site()
        self._init_done = True

        # Initialize the different database objects
        self._initialize_repositories()
        self.load()
        self.static.start_docker()

        # Delete any unfinished/crashed scenario output after initialization
        self.cleanup()

    def read_site(self, site_name: str = "site") -> None:
        """Read the site configuration from the static config folder and update database attributes."""
        site_path = self.static_path / "config" / f"{site_name}.toml"
        if not site_path.exists():
            raise ConfigError(
                f"Site configuration file '{site_path}' does not exist in the database."
            )
        self.site = Site.load_file(site_path)

    def _initialize_repositories(self):
        """Initialize object repositories and store them in `self._repositories`."""
        self.static = DbsStatic(self)
        self.events = DbsEvent(self, standard_objects=self.site.standard_objects.events)
        self.scenarios = DbsScenario(self)
        self.strategies = DbsStrategy(
            self, standard_objects=self.site.standard_objects.strategies
        )
        self.measures = DbsMeasure(self)
        self.projections = DbsProjection(
            self, standard_objects=self.site.standard_objects.projections
        )
        self.benefits = DbsBenefit(self)
        self._repositories: list[AbstractDatabaseElement] = [
            self.events,
            self.projections,
            self.measures,
            self.strategies,
            self.scenarios,
            self.benefits,
        ]

    def load(self):
        """Load all repositories from disk into memory."""
        logger.info("Loading database into memory")
        for repo in self._repositories:
            repo.load()

    def flush(self):
        """Write all repository changes from memory to disk."""
        logger.info("Writing database changes to disk")
        for repo in self._repositories:
            repo.flush()

    def clear(self):
        """Clear all repositories from memory without writing to disk."""
        logger.info("Clearing database")
        for repo in self._repositories:
            repo.clear()
        self.static.clear()

    def shutdown(self):
        """Explicitly shut down the singleton and clear all references."""
        # clear singleton references
        self._instance = None
        self._init_done = False
        self.__class__._instance = None

        # clear paths
        self.database_path = None
        self.database_name = None
        self.base_path = None
        self.input_path = None
        self.static_path = None
        self.output_path = None

        # clear site
        self.site = None

        # clear repositories
        self.clear()

        gc.collect()

    def get_slr_scenarios(self) -> SlrScenariosModel:
        """Get the path to the SLR scenarios file.

        Returns
        -------
        SlrScenariosModel
            SLR scenarios configuration model with the file path set to the static path.
        """
        if self.site.sfincs.slr_scenarios is None:
            raise ConfigError("No SLR scenarios defined in the site configuration.")
        slr = self.site.sfincs.slr_scenarios
        slr.file = (self.static_path / slr.file).as_posix()
        return slr

    def get_outputs(self) -> dict[str, Any]:
        """Return a dictionary with info on the outputs that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'path', 'last_modification_date' and "finished" info
        """
        all_scenarios = pd.DataFrame(self.scenarios.summarize_objects())
        if len(all_scenarios) > 0:
            df = all_scenarios[all_scenarios["finished"]]
        else:
            df = all_scenarios
        finished = df.drop(columns="finished").reset_index(drop=True)
        return finished.to_dict()

    def get_floodmap(self, scenario_name: str) -> FloodMap:
        """Return the flood map for a given scenario.

        Parameters
        ----------
        scenario_name : str
            Name of the scenario

        Returns
        -------
        FloodMap
            Flood map object containing the paths to the flood map files and their type.
        """
        _type = self.site.fiat.config.floodmap_type
        event = self.scenarios.get(scenario_name).event
        mode = self.events.get(event).mode
        base_dir = self.scenarios.output_path / scenario_name / "Flooding"

        if mode == Mode.single_event:
            if _type == FloodmapType.water_level:
                paths = [base_dir / "max_water_level_map.tif"]
            elif _type == FloodmapType.water_depth:
                paths = [base_dir / f"FloodMap_{scenario_name}.tif"]
        elif mode == Mode.risk:
            if _type == FloodmapType.water_level:
                paths = list(base_dir.glob("RP_*_max_water_level_map.tif"))
            elif _type == FloodmapType.water_depth:
                paths = list(base_dir.glob("RP_*_FloodMap.tif"))
        else:
            raise DatabaseError(
                f"Flood map type '{_type}' is not valid. Must be one of 'water_level' or 'water_depth'."
            )

        return FloodMap(name=scenario_name, map_type=_type, mode=mode, paths=paths)

    def get_impacts_path(self, scenario_name: str) -> Path:
        """Return the path to the impacts folder containing the impact runs for a given scenario.

        Parameters
        ----------
        scenario_name : str
            Name of the scenario

        Returns
        -------
        Path
            Path to the impacts folder for the given scenario
        """
        return self.scenarios.output_path.joinpath(scenario_name, "Impacts")

    def get_flooding_path(self, scenario_name: str) -> Path:
        """Return the path to the flooding folder containing the hazard runs for a given scenario.

        Parameters
        ----------
        scenario_name : str
            Name of the scenario

        Returns
        -------
        Path
            Path to the flooding folder for the given scenario
        """
        return self.scenarios.output_path.joinpath(scenario_name, "Flooding")

    def get_topobathy_path(self) -> str:
        """Return the path of the topobathy tiles in order to create flood maps with water level maps.

        Returns
        -------
        str
            path to topobathy tiles
        """
        path = self.static_path / "dem" / self.site.sfincs.dem.filename
        return path.as_posix()

    def get_index_path(self) -> str:
        """Return the path of the index tiles which are used to connect each water level cell with the topobathy tiles.

        Returns
        -------
        str
            path to index tiles
        """
        path = self.static_path / "dem" / self.site.sfincs.dem.index_filename
        return path.as_posix()

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
        output_path = self.scenarios.output_path.joinpath(scenario_name, "Flooding")
        # Check which file to use (if quadtree or regular)
        if not return_period:
            qt_path = output_path.joinpath("max_water_level_map_qt.nc")
            if qt_path.is_file():
                map_path = qt_path
            else:
                map_path = output_path.joinpath("max_water_level_map.tif")
        else:
            qt_path = output_path.joinpath(
                f"RP_{return_period:04d}_max_water_level_map_qt.nc"
            )
            if qt_path.is_file():
                map_path = qt_path
            else:
                map_path = output_path.joinpath(
                    f"RP_{return_period:04d}_max_water_level_map.tif"
                )
        # Open file
        with xr.open_dataarray(map_path) as map:
            zsmax = map.to_numpy()
        # Make sure output is 1D array
        if zsmax.ndim >= 2:
            zsmax = zsmax.flatten("F")
        return zsmax

    def get_flood_map_geotiff(
        self,
        scenario_name: str,
        return_period: Optional[int] = None,
    ) -> Optional[Path]:
        """Return the path to the geotiff file with the flood map for the given scenario.

        Parameters
        ----------
        scenario_name : str
            name of scenario
        return_period : int, optional
            return period in years, by default None. Only for risk scenarios.

        Returns
        -------
        Optional[Path]
            path to the flood map geotiff file, or None if it does not exist
        """
        if not return_period:
            file_path = self.scenarios.output_path.joinpath(
                scenario_name,
                "Flooding",
                f"FloodMap_{scenario_name}.tif",
            )
        else:
            file_path = self.scenarios.output_path.joinpath(
                scenario_name,
                "Flooding",
                f"RP_{return_period:04d}_maps.tif",
            )
        if not file_path.is_file():
            logger.warning(
                f"Flood map for scenario '{scenario_name}' at {file_path} does not exist."
            )
            return None
        return file_path

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
                raise DatabaseError(
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

        # Dont do anything if the hazard model has already been run in itself
        if ScenarioRunner(self, scenario=scenario).hazard_run_check():
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

                if ScenarioRunner(self, scenario=scn).hazard_run_check():
                    # only copy results if the hazard model has actually finished and skip simulation folders
                    shutil.copytree(
                        existing,
                        path_new,
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("simulations"),
                    )
                    logger.info(
                        f"Hazard simulation is used from the '{scn.name}' scenario"
                    )

    def cleanup(self) -> None:
        """
        Remove any corrupted scenario output.

        This method removes any scenario output that:
            - is corrupted due to unfinished runs
            - does not have a corresponding input

        """
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

        # Init model instances outside the loop
        overland = self.static.get_overland_sfincs_model()
        fiat = self.static.get_fiat_model()
        if self.site.sfincs.config.offshore_model is not None:
            offshore = self.static.get_offshore_sfincs_model()
        else:
            offshore = None

        for _dir in output_scenarios:
            # Delete if: input was deleted or corrupted output due to unfinished run
            if _dir.name not in [
                path.name for path in input_scenarios
            ] or not finished_file_exists(_dir):
                logger.info(f"Cleaning up corrupted outputs of scenario: {_dir.name}.")
                shutil.rmtree(_dir, ignore_errors=True)
            # If the scenario is finished, delete the simulation folders depending on `save_simulation`
            elif finished_file_exists(_dir):
                self._delete_simulations(_dir.name, overland, fiat, offshore)

    def _delete_simulations(
        self,
        scenario_name: str,
        overland: SfincsAdapter,
        fiat: FiatAdapter,
        offshore: Optional[SfincsAdapter],
    ) -> None:
        """Delete all simulation folders for a given scenario.

        Parameters
        ----------
        scenario_name : str
            Name of the scenario to delete simulations for.
        """
        scn = self.scenarios.get(scenario_name)
        event = self.events.get(scn.event)
        if isinstance(event, EventSet):
            event = self.events.get_event_set(scn.event)
            sub_events = event._events
        else:
            sub_events = None

        if not self.site.sfincs.config.save_simulation:
            # Delete SFINCS overland
            if sub_events:
                for sub_event in sub_events:
                    overland._delete_simulation_folder(scn, sub_event=sub_event)
            else:
                overland._delete_simulation_folder(scn)

            # Delete SFINCS offshore
            if self.site.sfincs.config.offshore_model and offshore is not None:
                if sub_events:
                    for sub_event in sub_events:
                        sim_path = offshore._get_simulation_path_offshore(
                            scn, sub_event=sub_event
                        )
                        if sim_path.exists():
                            shutil.rmtree(sim_path, ignore_errors=True)
                            logger.info(f"Deleted simulation folder: {sim_path}")
                        if sim_path.parent.exists() and not any(
                            sim_path.parent.iterdir()
                        ):
                            # Remove the parent directory `simulations` if it is empty
                            shutil.rmtree(sim_path.parent, ignore_errors=True)
                else:
                    sim_path = offshore._get_simulation_path_offshore(scn)
                    if sim_path.exists():
                        shutil.rmtree(sim_path, ignore_errors=True)
                        logger.info(f"Deleted simulation folder: {sim_path}")

                    if sim_path.parent.exists() and not any(sim_path.parent.iterdir()):
                        # Remove the parent directory `simulations` if it is empty
                        shutil.rmtree(sim_path.parent, ignore_errors=True)

        if not self.site.fiat.config.save_simulation:
            # Delete FIAT
            fiat._delete_simulation_folder(scn)
