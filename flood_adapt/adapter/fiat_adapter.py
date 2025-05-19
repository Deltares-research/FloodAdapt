import logging
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional, Union

import geopandas as gpd
import pandas as pd
import tomli
from fiat_toolbox import FiatColumns, get_fiat_columns
from fiat_toolbox.equity.equity import Equity
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_write_metrics_file import MetricsFileWriter
from fiat_toolbox.metrics_writer.fiat_write_return_period_threshold import (
    ExceedanceProbabilityCalculator,
)
from fiat_toolbox.spatial_output.aggregation_areas import AggregationAreas
from fiat_toolbox.spatial_output.footprints import Footprints
from fiat_toolbox.utils import extract_variables, matches_pattern, replace_pattern
from hydromt_fiat.fiat import FiatModel

from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.config.fiat import FiatConfigModel
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.path_builder import (
    ObjectDir,
)
from flood_adapt.misc.utils import cd, resolve_filepath
from flood_adapt.objects.events.events import Mode
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.measures.measures import (
    Buyout,
    Elevate,
    FloodProof,
    Measure,
    MeasureType,
)
from flood_adapt.objects.projections.projections import Projection
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.floodmap import FloodMap, FloodmapType
from flood_adapt.workflows.impacts_integrator import Impacts

# Define naming structure for saved files
_IMPACT_COLUMNS = FiatColumns(
    object_id="Object ID",
    object_name="Object Name",
    primary_object_type="Primary Object Type",
    secondary_object_type="Secondary Object Type",
    extraction_method="Extraction Method",
    ground_floor_height="Ground Floor Height",
    ground_elevation="Ground Elevation",
    damage_function="Damage Function: {name}",
    max_potential_damage="Max Potential Damage: {name}",
    aggregation_label="Aggregation Label: {name}",
    inundation_depth="Inundation Depth",
    inundation_depth_rp="Inundation Depth ({years}Y)",
    reduction_factor="Reduction Factor",
    reduction_factor_rp="Reduction Factor ({years}Y)",
    damage="Damage: {name}",
    damage_rp="Damage: {name} ({years}Y)",
    total_damage="Total Damage",
    total_damage_rp="Total Damage ({years}Y)",
    risk_ead="Risk (EAD)",
    segment_length="Segment Length",
)

# Define column naming of FIAT model
_FIAT_COLUMNS: FiatColumns = get_fiat_columns(
    fiat_version="0.2.1"
)  # columns of FIAT # TODO add version from config


class FiatAdapter(IImpactAdapter):
    """
    ImpactAdapter for Delft-FIAT.

    It includes:
    - preprocessing methods for adding measures, projections and hazards
    - executing method for running a Delft-FIAT simulation
    - postprocessing methods for saving impact results
    """

    # TODO deal with all the relative paths for the files used
    # TODO IImpactAdapter and general Adapter class should NOT use the database

    _model: FiatModel  # hydroMT-FIAT model
    config: Optional[FiatConfigModel] = None
    exe_path: Optional[os.PathLike] = None
    fiat_columns: FiatColumns
    impact_columns: FiatColumns

    def __init__(
        self,
        model_root: Path,
        config: Optional[FiatConfigModel] = None,
        exe_path: Optional[os.PathLike] = None,
        delete_crashed_runs: bool = True,
        config_base_path: Optional[os.PathLike] = None,
    ) -> None:
        # TODO should exe_path and delete_crashed_runs be part of the config?
        # Load FIAT template
        self.logger = FloodAdaptLogging.getLogger("FiatAdapter")
        self.config = config
        self.config_base_path = config_base_path
        self.exe_path = exe_path
        self.delete_crashed_runs = delete_crashed_runs
        self._model = FiatModel(root=str(model_root.resolve()), mode="r")
        self._model.read()
        self.fiat_columns = _FIAT_COLUMNS
        self.impact_columns = _IMPACT_COLUMNS  # columns of FA impact output

    @property
    def model_root(self):
        return Path(self._model.root)

    @property
    def damage_types(self):
        """Get the damage types that are present in the exposure."""
        types = []
        for col in self._model.exposure.exposure_db.columns:
            if matches_pattern(col, self.fiat_columns.damage_function):
                name = extract_variables(col, self.fiat_columns.damage_function)["name"]
                types.append(name)
        return types

    def read(self, path: Path) -> None:
        """Read the fiat model from the current model root."""
        if Path(self._model.root).resolve() != Path(path).resolve():
            self._model.set_root(root=str(path), mode="r")
        self._model.read()

    def write(self, path_out: Union[str, os.PathLike], overwrite: bool = True) -> None:
        """Write the fiat model configuration to a directory."""
        if not isinstance(path_out, Path):
            path_out = Path(path_out).resolve()

        if not path_out.exists():
            path_out.mkdir(parents=True)

        write_mode = "w+" if overwrite else "w"
        with cd(path_out):
            self._model.set_root(root=str(path_out), mode=write_mode)
            self._model.write()

    def close_files(self):
        """Close all open files and clean up file handles."""
        if hasattr(self.logger, "handlers"):
            for handler in self.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    self.logger.removeHandler(handler)

    def __enter__(self) -> "FiatAdapter":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close_files()
        return False

    def has_run(self, scenario: Scenario) -> bool:
        # TODO this should include a check for all output files , and then maybe save them as output paths and types
        """
        Check if the impact results file for the given scenario exists.

        Parameters
        ----------
        scenario : Scenario
            The scenario for which to check the FIAT results.

        Returns
        -------
        bool
            True if the FIAT results file exists, False otherwise.
        """
        impacts_path = Impacts(scenario=scenario).impacts_path

        fiat_results_path = impacts_path.joinpath(
            f"Impacts_detailed_{scenario.name}.csv"
        )
        return fiat_results_path.exists()

    def delete_model(self):
        """
        Delete the Delft-FIAT simulation folder.

        This method attempts to delete the directory specified by `self.model_root`.

        Raises
        ------
            OSError: If the directory cannot be deleted.
        """
        self.logger.info("Deleting Delft-FIAT simulation folder")
        try:
            shutil.rmtree(self.model_root)
        except OSError as e_info:
            self.logger.warning(f"{e_info}\nCould not delete {self.model_root}.")

    def fiat_completed(self) -> bool:
        """Check if fiat has run as expected.

        Returns
        -------
        boolean
            True if fiat has run, False if something went wrong
        """
        log_file = self.model_root.joinpath(
            self._model.config["output"]["path"], "fiat.log"
        )
        if not log_file.exists():
            return False
        try:
            with open(log_file, "r", encoding="cp1252") as f:
                return "Geom calculation are done!" in f.read()
        except Exception as e:
            self.logger.error(f"Error while checking if FIAT has run: {e}")
            return False

    def preprocess(self, scenario: Scenario) -> None:
        """
        Preprocess the FIAT-model given a scenario by setting up projections, measures, and hazards, and then saves any changes made to disk.

        Args:
            scenario (Scenario): The scenario to preprocess, which includes projection,
                                  strategy, and hazard.

        Returns
        -------
            None
        """
        self.logger.info("Pre-processing Delft-FIAT model")
        # Projection
        projection = self.database.projections.get(scenario.projection)
        self.add_projection(projection)

        # Measures
        strategy = self.database.strategies.get(scenario.strategy)
        for measure in strategy.get_impact_measures():
            self.add_measure(measure)

        # Hazard
        floodmap = FloodMap(scenario.name)
        var = "risk_maps" if floodmap.mode == Mode.risk else "zsmax"
        is_risk = floodmap.mode == Mode.risk
        self.set_hazard(
            map_fn=floodmap.path,
            map_type=floodmap.type,
            var=var,
            is_risk=is_risk,
            units=us.UnitTypesLength.meters,
        )

        # Save any changes made to disk as well
        output_path = Impacts(scenario).impacts_path / "fiat_model"
        self.write(path_out=output_path)

    def run(self, scenario) -> None:
        """
        Execute the full process for a given scenario, including preprocessing, executing the simulation, and postprocessing steps.

        Args:
            scenario: An object containing the scenario data.

        Returns
        -------
            None
        """
        sim_path = Impacts(scenario=scenario).impacts_path / "fiat_model"

        self.preprocess(scenario)
        self.execute(sim_path)
        self.postprocess(scenario)

    def execute(
        self,
        path: Optional[os.PathLike] = None,
        exe_path: Optional[os.PathLike] = None,
        delete_crashed_runs: Optional[bool] = None,
        strict=True,
    ) -> bool:
        """
        Execute the FIAT model.

        Parameters
        ----------
        path : Optional[os.PathLike], optional
            The path to the model directory. If not provided, defaults to `self.model_root`.
        exe_path : Optional[os.PathLike], optional
            The path to the FIAT executable. If not provided, defaults to `self.exe_path`.
        delete_crashed_runs : Optional[bool], optional
            Whether to delete files from crashed runs. If not provided, defaults to `self.delete_crashed_runs`.
        strict : bool, optional
            Whether to raise an error if the FIAT model fails to run. Defaults to True.

        Returns
        -------
        bool
            True if the FIAT model run successfully, False otherwise.

        Raises
        ------
        ValueError
            If `exe_path` is not provided and `self.exe_path` is None.
        RuntimeError
            If the FIAT model fails to run and `strict` is True.
        """
        if path is None:
            path = self.model_root
        if exe_path is None:
            if self.exe_path is None:
                raise ValueError(
                    "'exe_path' needs to be provided either when calling FiatAdapter.execute() or during initialization of the FiatAdapter object."
                )
            exe_path = self.exe_path
        if delete_crashed_runs is None:
            delete_crashed_runs = self.delete_crashed_runs
        path = Path(path)
        fiat_log = path / "fiat.log"
        with cd(path):
            with FloodAdaptLogging.to_file(file_path=fiat_log):
                FiatAdapter._ensure_correct_hash_spacing_in_csv(path)

                self.logger.info(f"Running FIAT in {path}")
                process = subprocess.run(
                    args=[Path(exe_path).resolve().as_posix(), "run", "settings.toml"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.logger.debug(process.stdout)

        if process.returncode != 0:
            if delete_crashed_runs:
                # Remove all files in the simulation folder except for the log files
                for subdir, dirs, files in os.walk(path, topdown=False):
                    for file in files:
                        if not file.endswith(".log"):
                            os.remove(os.path.join(subdir, file))

                    if not os.listdir(subdir):
                        os.rmdir(subdir)

            if strict:
                raise RuntimeError(f"FIAT model failed to run in {path}.")
            else:
                self.logger.error(f"FIAT model failed to run in {path}.")

        if process.returncode == 0:
            self.read_outputs()

        return process.returncode == 0

    def read_outputs(self) -> None:
        """
        Read the output FIAT CSV file specified in the model configuration and stores the data in the `outputs` attribute.

        Attributes
        ----------
        outputs : dict
            A dictionary containing the following keys:
            - "path" : Path
                The path to the output directory.
            - "table" : DataFrame
                The contents of the output CSV file.
        """
        # Get output path
        outputs_path = self.model_root.joinpath(self._model.config["output"]["path"])

        # Get all csvs and concatenate them in a single table
        csv_outputs_df = []
        for output_csv in self._model.config["output"]["csv"]:
            csv_path = outputs_path.joinpath(
                self._model.config["output"]["csv"][output_csv]
            )
            output_csv_df = pd.read_csv(csv_path)
            csv_outputs_df.append(output_csv_df)
        output_csv = pd.concat(csv_outputs_df)

        # Store them
        self.outputs = {}
        self.outputs["path"] = outputs_path
        self.outputs["table"] = output_csv

    def _get_aggr_ind(self, aggr_label: str):
        """
        Retrieve the index of the aggregation configuration that matches the given label.

        Parameters
        ----------
        aggr_label : str
            The label of the aggregation to find.

        Returns
        -------
        int
            The index of the aggregation configuration that matches the given label.

        Raises
        ------
        IndexError
            If no aggregation with the given label is found.
        """
        ind = [
            i
            for i, aggr in enumerate(self.config.aggregation)
            if aggr.name == aggr_label
        ][0]

        return ind

    def postprocess(self, scenario):
        """
        Post-process the results of the Delft-FIAT simulation for a given scenario.

        Parameters
        ----------
        scenario : Scenario
            The scenario object containing all relevant data and configurations.

        Raises
        ------
        RuntimeError
            If the Delft-FIAT simulation did not run successfully.

        Post-processing steps include:
        - Reading the outputs of the Delft-FIAT simulation.
        - Adding exceedance probabilities for risk mode scenarios.
        - Saving detailed impacts per object to a CSV file.
        - Creating infometrics files based on different metric configurations.
        - Generating infographic files if configured.
        - Calculating equity-based damages for risk mode scenarios.
        - Saving aggregated metrics to shapefiles.
        - Merging points data to building footprints.
        - Creating a roads spatial file if configured.
        - Deleting the simulation folder if the site configuration is set to not keep the simulation.

        Logging
        -------
        Logs the start and completion of the post-processing steps.
        """
        if not self.fiat_completed():
            raise RuntimeError("Delft-FIAT did not run successfully!")

        self.logger.info("Post-processing Delft-FIAT results")

        if not self.outputs:
            self.read_outputs()
        mode = self.database.events.get(scenario.event).mode

        # Define scenario output path
        impacts = Impacts(scenario=scenario)
        scenario_output_path = impacts.results_path
        impacts_output_path = impacts.impacts_path

        # Create column mapping to update column names
        name_translation = {}
        for col in self.outputs["table"].columns:  # iterate through output columns
            for field in list(self.impact_columns.model_fields):  # check for each field
                fiat_col = getattr(self.fiat_columns, field)
                if matches_pattern(col, fiat_col):
                    impact_col = getattr(self.impact_columns, field)
                    new_col = replace_pattern(col, fiat_col, impact_col)
                    if (
                        ".0Y" in new_col
                    ):  # TODO for now quick fix to account for float RP years, while metrics have integers
                        new_col = new_col.replace(".0Y", "Y")
                    name_translation[col] = new_col  # save mapping
        self.name_mapping = name_translation

        # Rename save outputs
        self.outputs["table"] = self.outputs["table"].rename(columns=self.name_mapping)

        # Save impacts per object
        fiat_results_path = impacts_output_path.joinpath(
            f"Impacts_detailed_{scenario.name}.csv"
        )
        self.outputs["table"].to_csv(fiat_results_path, index=False)

        # Add exceedance probabilities if needed (only for risk)
        if mode == Mode.risk:
            # Get config path
            # TODO check where this configs should be read from
            config_path = self.database.static_path.joinpath(
                "templates", "infometrics", "metrics_additional_risk_configs.toml"
            )
            with open(config_path, mode="rb") as fp:
                config = tomli.load(fp)["flood_exceedance"]
            self.add_exceedance_probability(
                column=config[
                    "column"
                ],  # TODO check how to the correct version of column
                threshold=config["threshold"],
                period=config["period"],
            )

        # Create the infometrics files
        if mode == Mode.risk:
            ext = "_risk"
        else:
            ext = ""

        # Get options for metric configurations
        metric_types = ["mandatory", "additional"]  # these are checked always

        if self.config.infographics:  # if infographics are created
            metric_types += ["infographic"]

        metric_config_paths = [
            self.database.static_path.joinpath(
                "templates", "infometrics", f"{name}_metrics_config{ext}.toml"
            )
            for name in metric_types
        ]

        # Specify the metrics output path
        metrics_outputs_path = scenario_output_path.joinpath(
            f"Infometrics_{scenario.name}.csv"
        )
        self.create_infometrics(metric_config_paths, metrics_outputs_path)

        # Get paths of created aggregated infometrics
        aggr_metrics_paths = list(
            metrics_outputs_path.parent.glob(f"{metrics_outputs_path.stem}_*.csv")
        )

        # Create the infographic files
        if self.config.infographics:
            config_base_path = self.database.static_path.joinpath(
                "templates", "Infographics"
            )
            self.create_infographics(
                name=scenario.name,
                output_base_path=scenario_output_path,
                config_base_path=config_base_path,
                metrics_path=metrics_outputs_path,
                mode=mode,
            )

        # Calculate equity based damages
        if mode == Mode.risk:
            for file in aggr_metrics_paths:
                # Load metrics
                aggr_label = file.stem.split(f"{metrics_outputs_path.stem}_")[-1]
                self.add_equity(aggr_label=aggr_label, metrics_path=file)

        # Save aggregated metrics to shapefiles
        for file in aggr_metrics_paths:
            aggr_label = file.stem.split(f"{metrics_outputs_path.stem}_")[-1]
            output_path = impacts_output_path.joinpath(
                f"Impacts_aggregated_{scenario.name}_{aggr_label}.gpkg"
            )
            self.save_aggregation_spatial(
                aggr_label=aggr_label, metrics_path=file, output_path=output_path
            )

        # Merge points data to building footprints
        self.save_building_footprints(
            output_path=impacts_output_path.joinpath(
                f"Impacts_building_footprints_{scenario.name}.gpkg"
            )
        )

        # Create a roads spatial file
        if self.config.roads_file_name:
            self.save_roads(
                output_path=impacts_output_path.joinpath(
                    f"Impacts_roads_{scenario.name}.gpkg"
                )
            )

        self.logger.info("Delft-FIAT post-processing complete!")

        # If site config is set to not keep FIAT simulation, delete folder
        if not self.config.save_simulation:
            self.delete_model()

    def add_measure(self, measure: Measure):
        """
        Add and apply a specific impact measure to the properties of the FIAT model.

        Parameters
        ----------
        measure : Measure
            The impact measure to be applied. It can be of type Elevate, FloodProof, or Buyout.

        Notes
        -----
        The method logs the application of the measure and calls the appropriate method based on the measure type:
            - Elevate: Calls elevate_properties(measure)
            - FloodProof: Calls floodproof_properties(measure)
            - Buyout: Calls buyout_properties(measure)

            If the measure type is unsupported, a warning is logged.
        """
        self.logger.info(f"Applying impact measure '{measure.name}'")
        if isinstance(measure, Elevate):
            self.elevate_properties(measure)
        elif isinstance(measure, FloodProof):
            self.floodproof_properties(measure)
        elif isinstance(measure, Buyout):
            self.buyout_properties(measure)
        else:
            self.logger.warning(
                f"Skipping unsupported measure type {measure.__class__.__name__}"
            )

    def add_projection(self, projection: Projection):
        """
        Add the socioeconomic changes part of a projection to the FIAT model.

        Parameters
        ----------
        projection : Projection
            The projection object containing socioeconomic changes to be applied.

        Notes
        -----
        - Economic growth is applied to all existing buildings if specified.
        - New population growth areas are added if specified, taking into account
        economic growth.
        - Population growth is applied to existing objects if specified.
        """
        self.logger.info(
            f"Applying socioeconomic changes from projection '{projection.name}'"
        )
        socio_economic_change = projection.socio_economic_change

        ids_all_buildings = self.get_all_building_ids()

        # Implement socioeconomic changes if needed
        # First apply economic growth to existing objects
        if not math.isclose(socio_economic_change.economic_growth, 0, abs_tol=1e-6):
            self.apply_economic_growth(
                economic_growth=socio_economic_change.economic_growth,
                ids=ids_all_buildings,  #
            )

        # Then the new population growth area is added if provided
        # In the new areas, the economic growth is taken into account!
        # Order matters since for the pop growth new, we only want the economic growth!
        if not math.isclose(
            socio_economic_change.population_growth_new, 0, abs_tol=1e-6
        ):
            # Get path of new development area geometry
            area_path = resolve_filepath(
                object_dir=ObjectDir.projection,
                obj_name=projection.name,
                path=socio_economic_change.new_development_shapefile,
            )

            # Get DEM location for assigning elevation to new areas
            dem = (
                self.database.static_path
                / "dem"
                / self.database.site.sfincs.dem.filename
            )
            # Call adapter method to add the new areas
            self.apply_population_growth_new(
                population_growth=socio_economic_change.population_growth_new,
                ground_floor_height=socio_economic_change.new_development_elevation.value,
                elevation_type=socio_economic_change.new_development_elevation.type,
                area_path=area_path,
                ground_elevation=dem,
            )

        # Then apply population growth to existing objects
        if not math.isclose(
            socio_economic_change.population_growth_existing, 0, abs_tol=1e-6
        ):
            self.apply_population_growth_existing(
                population_growth=socio_economic_change.population_growth_existing,
                ids=ids_all_buildings,
            )

    def set_hazard(
        self,
        map_fn: Union[os.PathLike, list[os.PathLike]],
        map_type: FloodmapType,
        var: str,
        is_risk: bool = False,
        units: str = us.UnitTypesLength.meters,
    ) -> None:
        """
        Set the hazard map and type for the FIAT model.

        Parameters
        ----------
        map_fn : str
            The filename of the hazard map.
        map_type : FloodmapType
            The type of the flood map.
        var : str
            The variable name in the hazard map.
        is_risk : bool, optional
            Flag indicating if the map is a risk output. Defaults to False.
        units : str, optional
            The units of the hazard map. Defaults to us.UnitTypesLength.meters.
        """
        self.logger.info(f"Setting hazard to the {map_type} map {map_fn}")
        # Add the floodmap data to a data catalog with the unit conversion
        wl_current_units = us.UnitfulLength(value=1.0, units=units)
        conversion_factor = wl_current_units.convert(self._model.exposure.unit)

        self._model.setup_hazard(
            map_fn=map_fn,
            map_type=map_type,
            rp=None,
            crs=None,  # change this in new version (maybe to str(floodmap.crs.split(':')[1]))
            nodata=-999,  # change this in new version
            var=var,
            chunks="auto",
            risk_output=is_risk,
            unit_conversion_factor=conversion_factor,
        )

    # PROJECTIONS

    def apply_economic_growth(
        self, economic_growth: float, ids: Optional[list] = None
    ) -> None:
        """
        Apply economic growth to the FIAT-Model by adjusting the maximum potential damage values in the exposure database.

        This method updates the max potential damage values in the exposure database by
        applying a given economic growth rate. It can optionally filter the updates to
        specific objects identified by their IDs.

        Parameters
        ----------
        economic_growth : float
            The economic growth rate to apply, expressed as a percentage.
        ids : Optional[list], default=None
            A list of object IDs to which the economic growth should be applied. If None, the growth is applied to all buildings.
        """
        self.logger.info(f"Applying economic growth of {economic_growth} %.")
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self._model.exposure.exposure_db.columns
            if matches_pattern(c, self.fiat_columns.max_potential_damage)
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self._model.exposure.exposure_db[
            self.fiat_columns.primary_object_type
        ].isin(self.config.non_building_names)

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self._model.exposure.exposure_db[
                self.fiat_columns.object_id
            ].isin(ids)

        # Update columns using economic growth value
        updated_max_pot_damage = self._model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + economic_growth / 100.0
        )

        # update fiat model
        self._model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def apply_population_growth_existing(
        self, population_growth: float, ids: Optional[list[str]] = None
    ) -> None:
        """
        Apply population growth to the FIAT-Model by adjusting the existing max potential damage values for buildings.

        This method updates the max potential damage values in the exposure database by
        applying a given population growth rate. It can optionally filter the updates to
        specific objects identified by their IDs.

        Parameters
        ----------
        population_growth : float
            The population growth rate as a percentage.
        ids : Optional[list[str]]
            A list of object IDs to filter the updates. If None, the updates are applied to all buildings.
        """
        self.logger.info(f"Applying population growth of {population_growth} %.")
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self._model.exposure.exposure_db.columns
            if matches_pattern(c, self.fiat_columns.max_potential_damage)
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self._model.exposure.exposure_db[
            self.fiat_columns.primary_object_type
        ].isin(self.config.non_building_names)

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self._model.exposure.exposure_db[
                self.fiat_columns.object_id
            ].isin(ids)

        # Update columns using economic growth value
        updated_max_pot_damage = self._model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + population_growth / 100.0
        )

        # update fiat model
        self._model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def apply_population_growth_new(
        self,
        population_growth: float,
        ground_floor_height: float,
        elevation_type: str,
        area_path: str,
        ground_elevation: Union[None, str, Path] = None,
    ) -> None:
        """
        Apply population growth in a new area by adding new objects in the model.

        Parameters
        ----------
        population_growth : float
            The percentage of population growth to apply.
        ground_floor_height : float
            The height of the ground floor.
        elevation_type : str
            The type of elevation reference to use. Must be either 'floodmap' or 'datum'.
        area_path : str
            The path to the area file.
        ground_elevation : Union[None, str, Path], optional
            The ground elevation reference. Default is None.

        Raises
        ------
        ValueError
            If `elevation_type` is 'floodmap' and base flood elevation (bfe) map is not provided.
            If `elevation_type` is not 'floodmap' or 'datum'.
        """
        self.logger.info(
            f"Applying population growth of {population_growth} %, by creating a new development area using the geometries from {area_path} and a ground floor height of {ground_floor_height} {self._model.exposure.unit} above '{elevation_type}'."
        )
        # Get reference type to align with hydromt
        if elevation_type == "floodmap":
            if not self.config.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            kwargs = {
                "elevation_reference": "geom",
                "path_ref": self.database.static_path.joinpath(self.config.bfe.geom),
                "attr_ref": self.config.bfe.field_name,
            }
        elif elevation_type == "datum":
            kwargs = {"elevation_reference": "datum"}
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")
        # Get aggregation areas info
        aggregation_areas = [
            self.database.static_path.joinpath(aggr.file)
            for aggr in self.config.aggregation
        ]
        attribute_names = [aggr.field_name for aggr in self.config.aggregation]
        label_names = [
            self.fiat_columns.aggregation_label.format(name=aggr.name)
            for aggr in self.config.aggregation
        ]
        new_dev_geom_name = Path(self.config.new_development_file_name).stem
        # Use hydromt function
        self._model.exposure.setup_new_composite_areas(
            percent_growth=population_growth,
            geom_file=Path(area_path),
            ground_floor_height=ground_floor_height,
            damage_types=self.damage_types,
            vulnerability=self._model.vulnerability,
            ground_elevation=ground_elevation,
            aggregation_area_fn=aggregation_areas,
            attribute_names=attribute_names,
            label_names=label_names,
            geom_name=new_dev_geom_name,
            **kwargs,
        )

    # MEASURES
    @staticmethod
    def _get_area_name(measure: Measure):
        """
        Determine the area name based on the selection type of the measure.

        Parameters
        ----------
        measure : Measure
            An instance of Measure containing attributes that define the selection type and area.

        Returns
        -------
        str
            The name of the area. It returns the aggregation area name if the selection type is "aggregation_area",
            the polygon file name if the selection type is "polygon", and "all" for any other selection type.
        """
        if measure.selection_type == "aggregation_area":
            area = measure.aggregation_area_name
        elif measure.selection_type == "polygon":
            area = measure.polygon_file
        else:
            area = "all"
        return area

    def elevate_properties(self, elevate: Elevate) -> None:
        """
        Elevate the ground floor height of properties based on the provided Elevate measure.

        Parameters
        ----------
        elevate : Elevate
            The Elevate measure containing the elevation details.

        Raises
        ------
        ValueError
            If the elevation type is 'floodmap' and the base flood elevation (bfe) map is not provided.
            If the elevation type is not 'floodmap' or 'datum'.
        """
        area = self._get_area_name(elevate)
        self.logger.info(
            f"Elevating '{elevate.property_type}' type properties in '{area}' by {elevate.elevation} relative to '{elevate.elevation.type}'."
        )
        # If ids are given use that as an additional filter
        objectids = self.get_object_ids(elevate)

        # Get reference type to align with hydromt
        if elevate.elevation.type == "floodmap":
            if not self.config.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            if self.config.bfe.table:
                path_ref = self.config_base_path.joinpath(self.config.bfe.table)
                height_reference = "table"
            else:
                path_ref = self.config_base_path.joinpath(self.config.bfe.geom)
                height_reference = "geom"
            # Use hydromt function
            self._model.exposure.raise_ground_floor_height(
                raise_by=elevate.elevation.value,
                objectids=objectids,
                height_reference=height_reference,
                path_ref=path_ref,
                attr_ref=self.config.bfe.field_name,
            )

        elif elevate.elevation.type == "datum":
            # Use hydromt function
            self._model.exposure.raise_ground_floor_height(
                raise_by=elevate.elevation.value,
                objectids=objectids,
                height_reference="datum",
            )
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")

    def buyout_properties(self, buyout: Buyout) -> None:
        """
        Apply the buyout measure to the properties by setting their maximum potential damage to zero.

        Parameters
        ----------
        buyout : Buyout
            The Buyout measure containing the details of the properties to be bought out.

        """
        area = self._get_area_name(buyout)
        self.logger.info(
            f"Buying-out '{buyout.property_type}' type properties in '{area}'."
        )
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self._model.exposure.exposure_db.columns
            if matches_pattern(c, self.fiat_columns.max_potential_damage)
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self._model.exposure.exposure_db[
            self.fiat_columns.primary_object_type
        ].isin(self.config.non_building_names)

        # Get rows that are affected
        objectids = self.get_object_ids(buyout)
        rows = (
            self._model.exposure.exposure_db[self.fiat_columns.object_id].isin(
                objectids
            )
            & buildings_rows
        )

        # Update columns
        updated_max_pot_damage = self._model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[rows, damage_cols] *= 0

        # update fiat model
        self._model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def floodproof_properties(self, floodproof: FloodProof) -> None:
        """
        Apply floodproofing measures to the properties by truncating the damage function.

        Parameters
        ----------
        floodproof : FloodProof
            The FloodProof measure containing the details of the properties to be floodproofed.
        """
        area = self._get_area_name(floodproof)
        self.logger.info(
            f"Flood-proofing '{floodproof.property_type}' type properties in '{area}' by {floodproof.elevation}."
        )
        # If ids are given use that as an additional filter
        objectids = self.get_object_ids(floodproof)

        # Use hydromt function
        self._model.exposure.truncate_damage_function(
            objectids=objectids,
            floodproof_to=floodproof.elevation.value,
            damage_function_types=self.damage_types,
            vulnerability=self._model.vulnerability,
        )

    # STATIC METHODS

    def get_buildings(self) -> gpd.GeoDataFrame:
        """
        Retrieve the building geometries from the FIAT model's exposure database.

        Returns
        -------
        gpd.GeoDataFrame
            A GeoDataFrame containing the geometries of all buildings in the FIAT model.

        Raises
        ------
        ValueError
            If the FIAT model does not have an exposure database initialized.
        """
        if self._model.exposure is None:
            raise ValueError(
                "FIAT model does not have exposure, make sure your model has been initialized."
            )
        gdf_0 = self._model.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self.config.non_building_names,
            return_gdf=True,
        )
        # Rename columns
        name_translation = {}
        for col in gdf_0.columns:  # iterate through output columns
            for field in list(self.impact_columns.model_fields):  # check for each field
                fiat_col = getattr(self.fiat_columns, field)
                if matches_pattern(col, fiat_col):
                    impact_col = getattr(self.impact_columns, field)
                    new_col = replace_pattern(col, fiat_col, impact_col)
                    name_translation[col] = new_col  # save mapping
        gdf = gdf_0.rename(columns=name_translation)
        return gdf

    def get_property_types(self) -> list:
        """
        Retrieve the list of property types from the FIAT model's exposure database.

        Returns
        -------
        list
            A list of property types available in the FIAT model.

        Raises
        ------
        ValueError
            If no property types are found in the FIAT model.
        """
        types = self._model.exposure.get_primary_object_type()
        if types is None:
            raise ValueError("No property types found in the FIAT model.")
        types.append("all")  # Add "all" type for using as identifier

        names = self.config.non_building_names
        if names:
            for name in names:
                if name in types:
                    types.remove(name)

        return types

    def get_all_building_ids(self):
        """
        Retrieve the IDs of all buildings in the FIAT model.

        Returns
        -------
        list
            A list of IDs for all buildings in the FIAT model.
        """
        # Get ids of existing buildings
        ids = self._model.exposure.get_object_ids(
            "all", non_building_names=self.config.non_building_names
        )
        return ids

    def get_object_ids(self, measure: Measure) -> list[Any]:
        """
        Retrieve the object IDs for a given impact measure.

        Parameters
        ----------
        measure : Measure
            The impact measure for which to retrieve object IDs.

        Returns
        -------
        list[Any]
            A list of object IDs that match the criteria of the given measure.

        Raises
        ------
        ValueError
            If the measure type is not an impact measure.
        """
        if not MeasureType.is_impact(measure.type):
            raise ValueError(
                f"Measure type {measure.type} is not an impact measure. "
                "Can only retrieve object ids for impact measures."
            )

        # check if polygon file is used, then get the absolute path
        if measure.polygon_file:
            polygon_file = resolve_filepath(
                object_dir=ObjectDir.measure,
                obj_name=measure.name,
                path=measure.polygon_file,
            )
        else:
            polygon_file = None

        # use the hydromt-fiat method to the ids
        ids = self._model.exposure.get_object_ids(
            selection_type=measure.selection_type,
            property_type=measure.property_type,
            non_building_names=self.config.non_building_names,
            aggregation=measure.aggregation_area_type,
            aggregation_area_name=measure.aggregation_area_name,
            polygon_file=str(polygon_file),
        )

        return ids

    # POST-PROCESSING METHODS

    def add_exceedance_probability(
        self, column: str, threshold: float, period: int
    ) -> pd.DataFrame:
        """Calculate exceedance probabilities and append them to the results table.

        Parameters
        ----------
        column : str
            The name of the column to calculate exceedance probabilities for.
        threshold : float
            The threshold value for exceedance probability calculation.
        period : int
            The return period for exceedance probability calculation.

        Returns
        -------
        pd.DataFrame
            The updated results table with exceedance probabilities appended.
        """
        self.logger.info("Calculating exceedance probabilities")
        fiat_results_df = ExceedanceProbabilityCalculator(column).append_probability(
            self.outputs["table"], threshold, period
        )
        self.outputs["table"] = fiat_results_df
        return self.outputs["table"]

    def create_infometrics(
        self, metric_config_paths: list[os.PathLike], metrics_output_path: os.PathLike
    ) -> None:
        """
        Create infometrics files based on the provided metric configuration paths.

        Parameters
        ----------
        metric_config_paths : list[os.PathLike]
            A list of paths to the metric configuration files.
        metrics_output_path : os.PathLike
            The path where the metrics output file will be saved.

        Raises
        ------
        FileNotFoundError
            If a mandatory metric configuration file does not exist.
        """
        # Get the metrics configuration
        self.logger.info("Calculating infometrics")

        # Write the metrics to file
        # Check if type of metric configuration is available
        for metric_file in metric_config_paths:
            if metric_file.exists():
                metrics_writer = MetricsFileWriter(
                    metric_file,
                    aggregation_label_fmt=self.impact_columns.aggregation_label,
                )

                metrics_writer.parse_metrics_to_file(
                    df_results=self.outputs["table"],
                    metrics_path=metrics_output_path,
                    write_aggregate=None,
                )

                metrics_writer.parse_metrics_to_file(
                    df_results=self.outputs["table"],
                    metrics_path=metrics_output_path,
                    write_aggregate="all",
                )
            else:
                if "mandatory" in metric_file.name.lower():
                    raise FileNotFoundError(
                        f"Mandatory metric configuration file {metric_file} does not exist!"
                    )

    def create_infographics(
        self,
        name: str,
        output_base_path: os.PathLike,
        config_base_path: os.PathLike,
        metrics_path: os.PathLike,
        mode: Mode = Mode.single_event,
    ):
        """Create infographic files based on the provided metrics and configuration.

        Parameters
        ----------
        name : str
            The name of the scenario.
        output_base_path : os.PathLike
            The base path where the output files will be saved.
        config_base_path : os.PathLike
            The base path where the configuration files are located.
        metrics_path : os.PathLike
            The path to the metrics file.
        mode : Mode, optional
            The mode of the infographic, by default Mode.single_event.
        """
        self.logger.info("Creating infographics")

        # Check if infographics config file exists
        if mode == Mode.risk:
            config_path = config_base_path.joinpath("config_risk_charts.toml")
            if not config_path.exists():
                self.logger.warning(
                    "Risk infographic cannot be created, since 'config_risk_charts.toml' is not available"
                )
                return

        # Get the infographic
        InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=mode,
            scenario_name=name,
            metrics_full_path=metrics_path,
            config_base_path=config_base_path,
            output_base_path=output_base_path,
        ).write_infographics_to_file()

    def add_equity(
        self,
        aggr_label: str,
        metrics_path: os.PathLike,
        damage_column_pattern: str = "TotalDamageRP{rp}",
        gamma: float = 1.2,
    ):
        """Calculate equity-based damages for a given aggregation label.

        Parameters
        ----------
        aggr_label : str
            The label of the aggregation area.
        metrics_path : os.PathLike
            The path to the metrics file.
        damage_column_pattern : str, optional
            The pattern for the damage column names, by default "TotalDamageRP{rp}".
        gamma : float, optional
            The equity weight parameter, by default 1.2
        """
        # TODO gamma in configuration file?

        ind = self._get_aggr_ind(aggr_label)
        # TODO check what happens if aggr_label not in config

        if self.config.aggregation[ind].equity is None:
            self.logger.warning(
                f"Cannot calculate equity weighted risk for aggregation label: {aggr_label}, because equity inputs are not available."
            )
            return

        self.logger.info(
            f"Calculating equity weighted risk for aggregation label: {aggr_label} "
        )
        metrics = pd.read_csv(metrics_path)
        # Create Equity object
        equity = Equity(
            census_table=self.config_base_path.joinpath(
                self.config.aggregation[ind].equity.census_data
            ),
            damages_table=metrics,
            aggregation_label=self.config.aggregation[ind].field_name,
            percapitaincome_label=self.config.aggregation[
                ind
            ].equity.percapitaincome_label,
            totalpopulation_label=self.config.aggregation[
                ind
            ].equity.totalpopulation_label,
            damage_column_pattern=damage_column_pattern,
        )
        # Calculate equity
        df_equity = equity.equity_calculation(gamma)
        # Merge with metrics tables and resave
        metrics_new = metrics.merge(
            df_equity,
            left_on=metrics.columns[0],
            right_on=self.config.aggregation[ind].field_name,
            how="left",
        )
        del metrics_new[self.config.aggregation[ind].field_name]
        metrics_new = metrics_new.set_index(metrics_new.columns[0])
        metrics_new.loc["Description", ["EW", "EWEAD", "EWCEAD"]] = [
            "Equity weight",
            "Equity weighted  expected annual damage",
            "Equity weighted certainty equivalent  annual damage",
        ]
        metrics_new.loc["Show In Metrics Table", ["EW", "EWEAD", "EWCEAD"]] = [
            True,
            True,
            True,
        ]
        metrics_new.loc["Long Name", ["EW", "EWEAD", "EWCEAD"]] = [
            "Equity weight",
            "Equity weighted  expected annual damage",
            "Equity weighted certainty equivalent  annual damage",
        ]
        metrics_new.index.name = None
        metrics_new.to_csv(metrics_path)

    def save_aggregation_spatial(
        self, aggr_label: str, metrics_path: os.PathLike, output_path: os.PathLike
    ):
        """
        Save aggregated metrics to a spatial file.

        Parameters
        ----------
        aggr_label : str
            The label of the aggregation area.
        metrics_path : os.PathLike
            The path to the metrics file.
        output_path : os.PathLike
            The path where the output spatial file will be saved.
        """
        self.logger.info(f"Saving impacts for aggregation areas type: '{aggr_label}'")

        metrics = pd.read_csv(metrics_path)

        # Load aggregation areas
        ind = self._get_aggr_ind(aggr_label)

        aggr_areas_path = self.config_base_path.joinpath(
            self.config.aggregation[ind].file
        )

        aggr_areas = gpd.read_file(aggr_areas_path, engine="pyogrio")

        # Save file
        AggregationAreas.write_spatial_file(
            metrics,
            aggr_areas,
            output_path,
            id_name=self.config.aggregation[ind].field_name,
            file_format="geopackage",
        )

    def save_building_footprints(self, output_path: os.PathLike):
        """
        Aggregate impacts at a building footprint level and then saves to an output file.

        Parameters
        ----------
        output_path : os.PathLike
            The path where the output spatial file will be saved.

        Raises
        ------
        ValueError
            If no building footprints are provided in the configuration.
        """
        self.logger.info("Calculating impacts at a building footprint scale")

        # Read the existing building points
        buildings = self._model.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self.config.non_building_names,
            return_gdf=True,
        )

        # Change names
        buildings = buildings[[self.fiat_columns.object_id, "geometry"]]
        buildings = buildings.rename(
            columns={self.fiat_columns.object_id: self.impact_columns.object_id}
        )

        # Get all results per building
        fiat_results_df = gpd.GeoDataFrame(
            self.outputs["table"].merge(
                buildings,
                on=self.impact_columns.object_id,
                how="inner",
            )
        )

        # Check which footprint case we have
        # If FIAT has points and external footprints are provided
        if self.config.building_footprints:
            method = "external_footprints"
            # Get footprints file
            footprints_path = self.config_base_path.joinpath(
                self.config.building_footprints
            )
            # Read building footprints
            footprints_gdf = gpd.read_file(footprints_path, engine="pyogrio")
            field_name = "BF_FID"
        # If FIAT has footprints already
        elif all(buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])):
            method = "internal_footprints"
            footprints_gdf = buildings[[self.impact_columns.object_id, "geometry"]]
            field_name = self.impact_columns.object_id
        # If FIAT has points and no external footprints are available
        else:
            method = "no_footprints"

        # Based on case follow different workflow
        if method in ["external_footprints", "internal_footprints"]:
            footprints = Footprints(
                footprints=footprints_gdf,
                fiat_columns=self.impact_columns,
                field_name=field_name,
            )
            footprints.aggregate(fiat_results_df)
        elif method == "no_footprints":
            footprints = Footprints(fiat_columns=self.impact_columns)
            footprints.set_point_data(fiat_results_df)

        # Normalize damages
        footprints.calc_normalized_damages()

        # Save footprint
        footprints.write(output_path)

    def save_roads(self, output_path: os.PathLike):
        """
        Save the impacts on roads to a spatial file.

        Parameters
        ----------
        output_path : os.PathLike
            The path where the output spatial file will be saved.
        """
        self.logger.info("Calculating road impacts")
        # Read roads spatial file
        roads = gpd.read_file(
            self.outputs["path"].joinpath(self.config.roads_file_name)
        )
        roads = roads.rename(columns=self.name_mapping)
        # Get columns to use
        aggr_cols = [
            name
            for name in self.outputs["table"].columns
            if self.impact_columns.aggregation_label in name
        ]
        inun_cols = [
            name
            for name in roads.columns
            if self.impact_columns.inundation_depth in name
        ]
        # Merge data
        roads = roads[[self.impact_columns.object_id, "geometry"] + inun_cols].merge(
            self.outputs["table"][
                [self.impact_columns.object_id, self.impact_columns.primary_object_type]
                + aggr_cols
            ],
            on=self.impact_columns.object_id,
        )
        # Save as geopackage
        roads.to_file(output_path, driver="GPKG")

    @staticmethod
    def _ensure_correct_hash_spacing_in_csv(
        model_root: Path, hash_spacing: int = 1
    ) -> None:
        """
        Ensure that the CSV file has the correct number of spaces between hashes.

        When writing csv files, FIAT does not add spaces between the hashes and the line, which leads to errors on linux.


        Parameters
        ----------
        file_path : Path
            The path to the model root.
        hash_spacing : int, optional
            The number of spaces between hashes, by default 1.
        """
        for dirpath, _, filenames in os.walk(model_root):
            for filename in filenames:
                if not filename.lower().endswith(".csv"):
                    continue
                file_path = os.path.join(dirpath, filename)

                with open(file_path, "r") as file:
                    lines = file.readlines()

                with open(file_path, "w") as file:
                    for line in lines:
                        if line.startswith("#"):
                            line = "#" + " " * hash_spacing + line.lstrip("#")
                        file.write(line)
