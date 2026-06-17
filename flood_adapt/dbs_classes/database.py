import gc
import os
import shutil
from pathlib import Path
from typing import Any, Literal, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from geopandas import GeoDataFrame

from flood_adapt.adapter.fiat_adapter import FiatAdapter
from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
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
from flood_adapt.misc.exceptions import ConfigError, DatabaseError
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.utils import finished_file_exists
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
                raise DatabaseError(
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
        logger.info(
            f"{re_option}initializing database to {database_name} at {database_path}".capitalize()
        )
        self.database_path = database_path
        self.database_name = database_name

        # Set the paths
        self.base_path = Path(database_path) / database_name
        self.input_path = self.base_path / "input"
        self.static_path = self.base_path / "static"
        self.output_path = self.base_path / "output"

        self.read_site()

        self._init_done = True

        # Bring the database dem and index data up to date with what the GUI expects
        # (single GeoTIFFs instead of the deprecated tiles).
        self._migrate_deprecated_tiles()

        # Delete any unfinished/crashed scenario output after initialization
        self.cleanup()

    def read_site(self, site_name: str = "site"):
        self._site = Site.load_file(self.static_path / "config" / f"{site_name}.toml")

        # Initialize the different database objects
        self._static = DbsStatic(self)
        self._events = DbsEvent(
            self, standard_objects=self.site.standard_objects.events
        )
        self._scenarios = DbsScenario(self)
        self._strategies = DbsStrategy(
            self, standard_objects=self.site.standard_objects.strategies
        )
        self._measures = DbsMeasure(self)
        self._projections = DbsProjection(
            self, standard_objects=self.site.standard_objects.projections
        )
        self._benefits = DbsBenefit(self)

    def shutdown(self):
        """Explicitly shut down the singleton and clear all references."""
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
        all_scenarios = pd.DataFrame(self._scenarios.summarize_objects())
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
                paths = [base_dir / "max_water_level_map.nc"]
            elif _type == FloodmapType.water_depth:
                paths = [base_dir / f"FloodMap_{scenario_name}.tif"]
        elif mode == Mode.risk:
            if _type == FloodmapType.water_level:
                paths = list(base_dir.glob("RP_*_maps.nc"))
            elif _type == FloodmapType.water_depth:
                paths = list(base_dir.glob("RP_*_maps.tif"))
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
        """Return the path of the topobathy GeoTIFF in order to create flood maps with water level maps.

        Returns
        -------
        str
            path to topobathy GeoTIFF
        """
        path = self.static_path / "dem" / self.site.sfincs.dem.filename
        return path.as_posix()

    def get_index_path(self) -> str:
        """Return the path of the index GeoTIFF which is used to connect each water level cell with the topobathy GeoTIFF.

        Returns
        -------
        str
            path to index GeoTIFF
        """
        index_path = self.static_path / "dem" / "index.tif"
        return index_path.as_posix()

    def _migrate_deprecated_tiles(self) -> None:
        """Update the static DEM data to the single-GeoTIFF format the GUI expects.

        Databases built for the old GUI shipped the topobathy/index data as
        PNG tiles under ``static/dem/tiles``. The current GUI
        (Guitares image overlays via cht_tiling) instead reads single GeoTIFFs:
        the subgrid DEM (``{self.site.sfincs.dem.filename}``) and an index raster (``index.tif``).
        This runs once when a database is opened and:
          1. Generates ``index.tif`` from the overland SFINCS model if it is missing.
          2. Deletes the deprecated ``static/dem/tiles`` folder if it is present.

        All actions are logged with a warning explaining why, since this mutates the
        opened database on disk. Failures are caught and logged so that opening the
        database never fails because of this migration; if the index cannot be
        generated the flood map simply will not render until it is available.
        """
        dem_dir = self.static_path / "dem"
        index_path = dem_dir / "index.tif"
        tiles_dir = dem_dir / "tiles"

        # 1. Ensure the index GeoTIFF exists.
        if not index_path.exists():
            logger.warning(
                f"Index GeoTIFF not found at {index_path.as_posix()}. This database "
                "predates the single-GeoTIFF DEM format used by the GUI. Generating it "
                "once from the overland SFINCS model; this may take a moment."
            )
            try:
                self._generate_index_geotiff(index_path)
            except Exception as e:
                raise DatabaseError(
                    f"Could not generate the index GeoTIFF at {index_path.as_posix()}: "
                    f"{e}. The flood map will not render until it is available."
                ) from e

        # 2. Remove the deprecated tile pyramids.
        if tiles_dir.exists():
            logger.warning(
                f"Removing deprecated DEM tile pyramids at {tiles_dir.as_posix()}. The "
                "GUI no longer renders raster layers from PNG tiles; it uses the single "
                f"GeoTIFFs ({self.site.sfincs.dem.filename} / index.tif) instead, so these tiles are no "
                "longer used and are being deleted to avoid confusion and save space."
            )
            try:
                shutil.rmtree(tiles_dir)
            except Exception as e:
                logger.warning(
                    f"Could not delete the deprecated tiles folder {tiles_dir.as_posix()}: "
                    f"{e}. It is unused and can be removed manually."
                )

    def _generate_index_geotiff(self, index_path: Path) -> None:
        """Generate the index GeoTIFF from the overland SFINCS model and the subgrid DEM.

        Mirrors flood_adapt's ``database_builder.create_dem_model``: each high-resolution
        DEM pixel is mapped to its SFINCS grid cell index. Heavy imports are done lazily.
        """
        from hydromt_sfincs import SfincsModel as HydromtSfincsModel
        from hydromt_sfincs.workflows.downscaling import make_index_cog

        overland_root = (
            self.static_path / "templates" / self.site.sfincs.config.overland_model.name
        )
        logger.info(
            f"Generating index GeoTIFF at {index_path.as_posix()} from SFINCS model "
            f"{overland_root.as_posix()} ..."
        )
        index_path.parent.mkdir(parents=True, exist_ok=True)
        model = HydromtSfincsModel(root=overland_root.resolve().as_posix(), mode="r")
        model.read()
        make_index_cog(
            model=model,
            indices_fn=index_path,
            topobathy_fn=self.get_topobathy_path(),
        )

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
            1D per-cell array of maximum water levels,
            matching the cell numbering of the index GeoTIFF
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
        # Flatten to a 1D per-cell array in Fortran order, matching the cell
        # numbering of the index GeoTIFF (make_index_cog), as expected by the
        # cht_tiling FloodMap used by the GUI.
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
        Remove corrupted scenario output.

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
        event = self.events.get(scn.event, load_all=True)
        sub_events = event._events if event.mode == Mode.risk else None

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
