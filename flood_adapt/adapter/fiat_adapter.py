import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, List, Optional, Union

import geopandas as gpd
import pandas as pd
import tomli
from fiat_toolbox.equity.equity import Equity
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_write_metrics_file import MetricsFileWriter
from fiat_toolbox.metrics_writer.fiat_write_return_period_threshold import (
    ExceedanceProbabilityCalculator,
)
from fiat_toolbox.spatial_output.aggregation_areas import AggregationAreas
from fiat_toolbox.spatial_output.footprints import Footprints
from hydromt_fiat.fiat import FiatModel

from flood_adapt import unit_system as us
from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.floodmap import FloodMap, FloodMapType
from flood_adapt.object_model.hazard.interface.events import Mode
from flood_adapt.object_model.impact.measure.buyout import Buyout
from flood_adapt.object_model.impact.measure.elevate import Elevate
from flood_adapt.object_model.impact.measure.floodproof import FloodProof
from flood_adapt.object_model.impact.measure.measure_helpers import (
    get_object_ids,
)
from flood_adapt.object_model.interface.config.fiat import FiatConfigModel
from flood_adapt.object_model.interface.measures import (
    IMeasure,
    MeasureType,
)
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.utils import cd, resolve_filepath


class FiatAdapter(IImpactAdapter):
    """
    ImpactAdapter for Delft-FIAT.

    It includes:
    - preprocessing methods for adding measures, projections and hazards
    - executing methods for running a Delft-FIAT simulations
    - postprocessing methods for saving impact results
    """

    _model: FiatModel  # hydroMT-FIAT model
    config: Optional[FiatConfigModel] = None  # Site model
    exe_path: Optional[os.PathLike] = None

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
        self.logger = FloodAdaptLogging.getLogger(
            "FiatAdapter", level=logging.INFO
        )  # TODO check name and level for logging
        self.config = config
        self.config_base_path = config_base_path
        self.exe_path = exe_path
        self.delete_crashed_runs = delete_crashed_runs
        self._model = FiatModel(root=str(model_root.resolve()), mode="r")
        self._model.read()

    @property
    def model_root(self):
        return Path(self._model.root)

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

    def has_run(self, scenario: IScenario) -> bool:
        scenario_output_path = scenario.database.scenarios.output_path.joinpath(
            scenario.attrs.name
        )
        impacts_output_path = scenario_output_path.joinpath("Impacts")
        fiat_results_path = impacts_output_path.joinpath(
            f"Impacts_detailed_{scenario.attrs.name}.csv"
        )
        return fiat_results_path.exists()

    def delete_model(self):
        self.logger.info("Deleting Delft-FIAT simulation folder...")
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

    def preprocess(self, scenario: IScenario):
        # Measures
        for measure in scenario.strategy.get_impact_strategy().measures:
            self.add_measure(measure)

        # Projection
        self.add_projection(scenario.projection)

        # Hazard
        floodmap = FloodMap(scenario.attrs.name)
        var = "zsmax" if floodmap.mode == Mode.risk else "risk_maps"
        is_risk = floodmap.mode == Mode.risk
        self.add_hazard(
            map_fn=floodmap.path,
            map_type=floodmap.type,
            var=var,
            is_risk=is_risk,
            units=us.UnitTypesLength.meters,
        )

        # Save any changes made to disk as well
        output_path = scenario.impacts.fiat_path
        self.write(path_out=output_path)

    def run(self, scenario):
        self.preprocess(scenario)
        self.execute(
            scenario.impacts.fiat_path
        )  # TODO which should not use FloodAdapt classes
        self.postprocess(scenario)

    def execute(
        self,
        path: Optional[os.PathLike] = None,
        exe_path: Optional[os.PathLike] = None,
        delete_crashed_runs: Optional[bool] = None,
        strict=True,
    ):
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
                self.logger.info(f"Running FIAT in {path}...")
                process = subprocess.run(
                    f'"{exe_path.as_posix()}" run settings.toml',
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

    def read_outputs(self):
        # Get output csv
        outputs_path = self.model_root.joinpath(self._model.config["output"]["path"])
        output_csv_path = outputs_path.joinpath(
            self._model.config["output"]["csv"]["name"]
        )
        self.outputs = {}
        self.outputs["path"] = outputs_path
        self.outputs["table"] = pd.read_csv(output_csv_path)

    def _get_aggr_ind(self, aggr_label: str):
        ind = [
            i
            for i, aggr in enumerate(self.config.aggregation)
            if aggr.name == aggr_label
        ][0]

        return ind

    def postprocess(self, scenario):
        if not self.fiat_completed():
            raise RuntimeError("Delft-FIAT did not run successfully!")

        self.logger.info("Post-processing Delft-FIAT results...")

        self.read_outputs()

        mode = scenario.event.attrs.mode

        # Define scenario output path
        scenario_output_path = scenario.database.scenarios.output_path.joinpath(
            scenario.attrs.name
        )
        impacts_output_path = scenario_output_path.joinpath("Impacts")

        # Add exceedance probabilities if needed (only for risk)
        if mode == Mode.risk:
            # Get config path
            # TODO check where this configs should be read from
            config_path = scenario.database.static_path.joinpath(
                "templates", "infometrics", "metrics_additional_risk_configs.toml"
            )
            with open(config_path, mode="rb") as fp:
                config = tomli.load(fp)["flood_exceedance"]
            self.add_exceedance_probability(
                column=config["column"],
                threshold=config["threshold"],
                period=config["period"],
            )

        # Save impacts per object
        fiat_results_path = impacts_output_path.joinpath(
            f"Impacts_detailed_{scenario.attrs.name}.csv"
        )
        self.outputs["table"].to_csv(fiat_results_path)

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
            scenario.database.static_path.joinpath(
                "templates", "infometrics", f"{name}_metrics_config{ext}.toml"
            )
            for name in metric_types
        ]

        # Specify the metrics output path
        metrics_outputs_path = scenario_output_path.joinpath(
            f"Infometrics_{scenario.attrs.name}.csv"
        )
        self.create_infometrics(metric_config_paths, metrics_outputs_path)

        # Get paths of created aggregated infometrics
        aggr_metrics_paths = list(
            metrics_outputs_path.parent.glob(f"{metrics_outputs_path.stem}_*.csv")
        )

        # Create the infographic files
        if self.config.infographics:
            config_base_path = scenario.database.static_path.joinpath(
                "templates", "Infographics"
            )
            self.create_infographics(
                name=scenario.attrs.name,
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
                f"Impacts_aggregated_{scenario.attrs.name}_{aggr_label}.gpkg"
            )
            self.save_aggregation_spatial(
                aggr_label=aggr_label, metrics_path=file, output_path=output_path
            )

        # Merge points data to building footprints
        self.save_building_footprints(
            output_path=impacts_output_path.joinpath(
                f"Impacts_building_footprints_{scenario.attrs.name}.gpkg"
            )
        )

        # Create a roads spatial file
        if self.config.roads_file_name:
            self.save_roads(
                output_path=impacts_output_path.joinpath(
                    f"Impacts_roads_{scenario.attrs.name}.gpkg"
                )
            )

        self.logger.info("Delft-FIAT post-processing complete!")

        # If site config is set to not keep FIAT simulation, delete folder
        if not self.config.save_simulation:
            self.delete_model()

    def add_measure(self, measure: IMeasure):
        self.logger.info(
            f"Adding {measure.__class__.__name__.capitalize()} to the Delft-FIAT model..."
        )

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

    def add_projection(self, projection):
        return super().add_projection(projection)

    def add_hazard(
        self,
        map_fn: str,
        map_type: FloodMapType,
        var: str,
        is_risk: bool = False,
        units: str = us.UnitTypesLength.meters,
    ) -> None:
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

    def apply_economic_growth(
        self, economic_growth: float, ids: Optional[list[str]] = []
    ):
        """Implement economic growth in the exposure of FIAT.

        This is only done for buildings. This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        economic_growth : float
            Percentage value of economic growth.
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the economic growth on,
            by default None
        """
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self._model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.fiat_model.exposure.exposure_db[
            "Primary Object Type"
        ].isin(self.site.attrs.fiat.config.non_building_names)

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self._model.exposure.exposure_db[
                "Object ID"
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
        self, population_growth: float, ids: Optional[list[str]] = []
    ):
        """Implement population growth in the exposure of FIAT.

        This is only done for buildings. This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        population_growth : float
            Percentage value of population growth.
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on,
            by default None
        """
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self._model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.fiat_model.exposure.exposure_db[
            "Primary Object Type"
        ].isin(self.site.attrs.fiat.config.non_building_names)

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self._model.exposure.exposure_db[
                "Object ID"
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
        aggregation_areas: Union[List[str], List[Path], str, Path] = None,
        attribute_names: Union[List[str], str] = None,
        label_names: Union[List[str], str] = None,
    ):
        """Implement population growth in new development area.

        Parameters
        ----------
        population_growth : float
            percentage of the existing population (value of assets) to use for the new area
        ground_floor_height : float
            height of the ground floor to be used for the objects in the new area
        elevation_type : str
            "floodmap" or "datum"
        area_path : str
            path to geometry file with new development areas
        """
        # Get reference type to align with hydromt
        if elevation_type == "floodmap":
            if not self.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            # Use hydromt function
            self._model.exposure.setup_new_composite_areas(
                percent_growth=population_growth,
                geom_file=Path(area_path),
                ground_floor_height=ground_floor_height,
                damage_types=["Structure", "Content"],
                vulnerability=self._model.vulnerability,
                elevation_reference="geom",
                path_ref=self.bfe["geom"],
                attr_ref=self.bfe["name"],
                ground_elevation=ground_elevation,
                aggregation_area_fn=aggregation_areas,
                attribute_names=attribute_names,
                label_names=label_names,
            )
        elif elevation_type == "datum":
            # Use hydromt function
            self._model.exposure.setup_new_composite_areas(
                percent_growth=population_growth,
                geom_file=Path(area_path),
                ground_floor_height=ground_floor_height,
                damage_types=["Structure", "Content"],
                vulnerability=self._model.vulnerability,
                elevation_reference="datum",
                ground_elevation=ground_elevation,
                aggregation_area_fn=aggregation_areas,
                attribute_names=attribute_names,
                label_names=label_names,
            )
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")

    def elevate_properties(self, elevate: Elevate):
        # If ids are given use that as an additional filter
        objectids = self.get_object_ids(elevate)

        # Get reference type to align with hydromt
        if elevate.attrs.elevation.type == "floodmap":
            if not self.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            elev_ref = self.bfe["mode"]
            path_ref = self.bfe[elev_ref]
            # Use hydromt function
            self._model.exposure.raise_ground_floor_height(
                raise_by=elevate.attrs.elevation.value,
                objectids=objectids,
                height_reference=elev_ref,
                path_ref=path_ref,
                attr_ref=self.bfe["name"],
            )

        elif elevate.attrs.elevation.type == "datum":
            # Use hydromt function
            self._model.exposure.raise_ground_floor_height(
                raise_by=elevate.attrs.elevation.value,
                objectids=objectids,
                height_reference="datum",
            )
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")

    def buyout_properties(self, buyout: Buyout):
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self._model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.fiat_model.exposure.exposure_db[
            "Primary Object Type"
        ].isin(self.site.attrs.fiat.config.non_building_names)

        # Get rows that are affected
        objectids = self.get_object_ids(buyout)
        rows = (
            self._model.exposure.exposure_db["Object ID"].isin(objectids)
            & buildings_rows
        )

        # Update columns using economic growth value
        updated_max_pot_damage = self._model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[rows, damage_cols] *= 0

        # update fiat model
        self._model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def floodproof_properties(self, floodproof: FloodProof):
        """Floodproof properties by creating new depth-damage functions and adding them in "Damage Function: {}" column in the FIAT exposure file.

        Parameters
        ----------
        floodproof : FloodProof
            this is an "floodproof" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on,
            by default None
        """
        # If ids are given use that as an additional filter
        objectids = get_object_ids(floodproof, self._model)

        # Use hydromt function
        self._model.exposure.truncate_damage_function(
            objectids=objectids,
            floodproof_to=floodproof.attrs.elevation.value,
            damage_function_types=["Structure", "Content"],
            vulnerability=self._model.vulnerability,
        )

    def get_buildings(self) -> gpd.GeoDataFrame:
        if self._model.exposure is None:
            raise ValueError(
                "FIAT model does not have exposure, make sure your model has been initialized."
            )
        return self._model.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self.site.attrs.fiat.config.non_building_names,
            return_gdf=True,
        )

    def get_property_types(self) -> list:
        if self._model.exposure is None:
            raise ValueError(
                "FIAT model does not have exposure, make sure your model has been initialized."
            )

        types = self._model.exposure.get_primary_object_type()
        if types is None:
            raise ValueError("No property types found in the FIAT model.")
        types.append("all")  # Add "all" type for using as identifier

        names = self.site.attrs.fiat.config.non_building_names
        if names:
            for name in names:
                if name in types:
                    types.remove(name)

        return types

    def get_object_ids(self, measure: IMeasure) -> list[Any]:
        """Get ids of objects that are affected by the measure."""
        if not MeasureType.is_impact(measure.attrs.type):
            raise ValueError(
                f"Measure type {measure.attrs.type} is not an impact measure. "
                "Can only retrieve object ids for impact measures."
            )

        # check if polygon file is used, then get the absolute path
        if measure.attrs.polygon_file:
            polygon_file = resolve_filepath(
                object_dir=ObjectDir.measure,
                obj_name=measure.attrs.name,
                path=measure.attrs.polygon_file,
            )
        else:
            polygon_file = None

        # use the hydromt-fiat method to the ids
        ids = self._model.exposure.get_object_ids(
            selection_type=measure.attrs.selection_type,
            property_type=measure.attrs.property_type,
            non_building_names=self.site.attrs.fiat.config.non_building_names,
            aggregation=measure.attrs.aggregation_area_type,
            aggregation_area_name=measure.attrs.aggregation_area_name,
            polygon_file=str(polygon_file),
        )

        return ids

    def add_exceedance_probability(
        self, column: str, threshold: float, period: int
    ) -> pd.DataFrame:
        self.logger.info("Calculating exceedance probabilities...")
        fiat_results_df = ExceedanceProbabilityCalculator(column).append_probability(
            self.outputs["table"], threshold, period
        )
        self.outputs["table"] = fiat_results_df
        return self.outputs["table"]

    def create_infometrics(
        self, metric_config_paths: list[os.PathLike], metrics_output_path: os.PathLike
    ) -> None:
        # Get the metrics configuration
        self.logger.info("Calculating infometrics...")

        # Write the metrics to file
        # Check if type of metric configuration is available
        for metric_file in metric_config_paths:
            if metric_file.exists():
                metrics_writer = MetricsFileWriter(metric_file)

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
        self.logger.info("Creating infographics...")

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
        # TODO gamma in configuration file?

        ind = self._get_aggr_ind(aggr_label)
        # TODO check what happens if aggr_label not in config

        if self.config.aggregation[ind].equity is None:
            self.logger.warning(
                f"Cannot calculate equity weighted risk for aggregation label: {aggr_label}, because equity inputs are not available."
            )
            return

        self.logger.info(
            f"Calculating equity weighted risk for aggregation label: {aggr_label} ..."
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
        self.logger.info("Saving impacts on aggregation areas...")

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
        self.logger.info("Saving impacts on building footprints...")

        # Get footprints file paths from site.toml
        # TODO ensure that if this does not happen we get same file name output from FIAT?
        # Check if there is a footprint file given
        if not self.config.building_footprints:
            raise ValueError("No building footprints are provided.")

        # Get footprints file
        footprints_path = self.config_base_path.joinpath(
            self.config.building_footprints
        )
        # Read building footprints
        footprints_gdf = gpd.read_file(footprints_path, engine="pyogrio")
        footprints = Footprints(footprints_gdf)

        # Read files
        # TODO Will it save time if we load this footprints once when the database is initialized?

        # Read the existing building points
        buildings = self._model.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self.config.non_building_names,
            return_gdf=True,
        )

        fiat_results_df = gpd.GeoDataFrame(
            self.outputs["table"].merge(
                buildings[["Object ID", "geometry"]], on="Object ID", how="left"
            )
        )

        footprints.aggregate(fiat_results_df)
        footprints.calc_normalized_damages()

        # Save footprint
        footprints.write(output_path)

    def save_roads(self, output_path: os.PathLike):
        self.logger.info("Saving road impacts...")
        # Read roads spatial file
        roads = gpd.read_file(
            self.outputs["path"].joinpath(self.config.roads_file_name)
        )
        # Get columns to use
        aggr_cols = [
            name
            for name in self.outputs["table"].columns
            if "Aggregation Label:" in name
        ]
        inun_cols = [name for name in roads.columns if "Inundation Depth" in name]
        # Merge data
        roads = roads[["Object ID", "geometry"] + inun_cols].merge(
            self.outputs["table"][["Object ID", "Primary Object Type"] + aggr_cols],
            on="Object ID",
        )
        # Save as geopackage
        roads.to_file(output_path, driver="GPKG")
