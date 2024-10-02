import shutil
import subprocess
import time
from os import environ
from pathlib import Path

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
from fiat_toolbox.spatial_output.points_to_footprint import PointsToFootprints

from flood_adapt.integrator.fiat_adapter import FiatAdapter
from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.hazard.interface.models import Mode
from flood_adapt.object_model.interface.database_user import IDatabaseUser
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.utils import cd


# TODO move code that is related to fiat to the Fiat Adapter
# TODO move other code to the Controller class
class DirectImpacts(IDatabaseUser):
    """All information related to the direct impacts of the scenario.

    Includes methods to run the impact model or check if it has already been run.
    """

    name: str
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy
    hazard: FloodMap

    def __init__(self, scenario: ScenarioModel, results_path: Path = None) -> None:
        self._logger = FloodAdaptLogging.getLogger(__name__)
        self.name = scenario.name
        self.scenario = scenario

        if results_path is not None:
            FloodAdaptLogging.deprecation_warning(
                version="0.2.0",
                reason="`results_path` parameter is deprecated. Use the `results_path` property instead.",
            )

        self.set_socio_economic_change(scenario.projection)
        self.set_impact_strategy(scenario.strategy)

        # self.hazard = FloodMap(scenario.name)

    @property
    def hazard(self) -> FloodMap:
        return FloodMap(self.name)

    @property
    def results_path(self) -> Path:
        return (
            self.database.scenarios.get_database_path(get_input_path=False) / self.name
        )

    @property
    def impacts_path(self) -> Path:
        return self.results_path / "Impacts"

    @property
    def fiat_path(self) -> Path:
        return self.impacts_path / "fiat_model"

    @property
    def has_run(self) -> bool:
        return self.has_run_check()

    @property
    def site_info(self):
        return self.database.site

    def run(self):
        """Run the direct impact model."""
        if self.has_run:
            self._logger.info("Direct impacts have already been run.")
            return
        self.preprocess_models()
        self.run_models()
        self.postprocess_models()

    def has_run_check(self) -> bool:
        """Check if the direct impact has been run.

        Returns
        -------
        bool
            _description_
        """
        return self.impacts_path.joinpath(f"Impacts_detailed_{self.name}.csv").exists()

    def fiat_has_run_check(self) -> bool:
        """Check if fiat has run as expected.

        Returns
        -------
        boolean
            True if fiat has run, False if something went wrong
        """
        log_file = self.fiat_path.joinpath("fiat.log")
        if not log_file.exists():
            return False
        try:
            with open(log_file, "r", encoding="cp1252") as f:
                return "Geom calculation are done!" in f.read()
        except Exception as e:
            self._logger.error(f"Error while checking if FIAT has run: {e}")
            return False

    def set_socio_economic_change(self, projection: str) -> None:
        """Set the SocioEconomicChange object of the scenario.

        Parameters
        ----------
        projection : str
            Name of the projection used in the scenario
        """
        self.socio_economic_change = self.database.projections.get(
            projection
        ).get_socio_economic_change()

    def set_impact_strategy(self, strategy: str) -> None:
        """Set the ImpactStrategy object of the scenario.

        Parameters
        ----------
        strategy : str
            Name of the strategy used in the scenario
        """
        self.impact_strategy = self.database.strategies.get(
            strategy
        ).get_impact_strategy()

    def preprocess_models(self):
        self._logger.info("Preparing impact models...")
        # Preprocess all impact model input
        start_time = time.time()
        self.preprocess_fiat()
        end_time = time.time()
        print(f"FIAT preprocessing took {str(round(end_time - start_time, 2))} seconds")

    def run_models(self):
        self._logger.info("Running impact models...")
        start_time = time.time()
        return_code = self.run_fiat()
        end_time = time.time()

        success_str = "SUCCESS" if return_code == 0 else "FAILURE"
        self._logger.info(
            f"FIAT run finished with return code {return_code} ({success_str}). Running FIAT took {str(round(end_time - start_time, 2))} seconds"
        )

    def postprocess_models(self):
        self._logger.info("Post-processing impact models...")
        # Preprocess all impact model input
        self.postprocess_fiat()
        self._logger.info("Impact models post-processing complete!")

    def preprocess_fiat(self):
        """Update FIAT model based on scenario information and then runs the FIAT model."""
        # Check if hazard is already run
        if not self.hazard.has_run:
            raise ValueError(
                "Hazard for this scenario has not been run yet! FIAT cannot be initiated."
            )

        # Get the location of the FIAT template model
        template_path = self.database.static_path / "templates" / "fiat"

        # Read FIAT template with FIAT adapter
        fa = FiatAdapter(
            model_root=template_path, database_path=self.database.base_path
        )

        # If path for results does not yet exist, make it
        if not self.fiat_path.is_dir():
            self.fiat_path.mkdir(parents=True)
        else:
            shutil.rmtree(self.fiat_path)

        # Get ids of existing objects
        ids_existing = fa.fiat_model.exposure.exposure_db["Object ID"].to_list()

        # Implement socioeconomic changes if needed
        # First apply economic growth to existing objects
        if self.socio_economic_change.attrs.economic_growth != 0:
            fa.apply_economic_growth(
                economic_growth=self.socio_economic_change.attrs.economic_growth,
                ids=ids_existing,
            )

        # Then we create the new population growth area if provided
        # In that area only the economic growth is taken into account
        # Order matters since for the pop growth new, we only want the economic growth!
        if self.socio_economic_change.attrs.population_growth_new != 0:
            # Get path of new development area geometry
            area_path = (
                self.database.projections.get_database_path()
                / self.scenario.projection
                / self.socio_economic_change.attrs.new_development_shapefile
            )
            dem = self.database.static_path / "dem" / self.site_info.attrs.dem.filename
            aggregation_areas = [
                self.database.static_path / aggr.file
                for aggr in self.site_info.attrs.fiat.aggregation
            ]
            attribute_names = [
                aggr.field_name for aggr in self.site_info.attrs.fiat.aggregation
            ]
            label_names = [
                f"Aggregation Label: {aggr.name}"
                for aggr in self.site_info.attrs.fiat.aggregation
            ]

            fa.apply_population_growth_new(
                population_growth=self.socio_economic_change.attrs.population_growth_new,
                ground_floor_height=self.socio_economic_change.attrs.new_development_elevation.value,
                elevation_type=self.socio_economic_change.attrs.new_development_elevation.type,
                area_path=area_path,
                ground_elevation=dem,
                aggregation_areas=aggregation_areas,
                attribute_names=attribute_names,
                label_names=label_names,
            )

        # Last apply population growth to existing objects
        if self.socio_economic_change.attrs.population_growth_existing != 0:
            fa.apply_population_growth_existing(
                population_growth=self.socio_economic_change.attrs.population_growth_existing,
                ids=ids_existing,
            )

        # Then apply Impact Strategy by iterating trough the impact measures
        for measure in self.impact_strategy.measures:
            if measure.attrs.type == "elevate_properties":
                fa.elevate_properties(
                    elevate=measure,
                    ids=ids_existing,
                )
            elif measure.attrs.type == "buyout_properties":
                fa.buyout_properties(
                    buyout=measure,
                    ids=ids_existing,
                )
            elif measure.attrs.type == "floodproof_properties":
                fa.floodproof_properties(
                    floodproof=measure,
                    ids=ids_existing,
                )
            else:
                self._logger.warning(
                    f"Impact measure type not recognized: {measure.attrs.type}"
                )

        # setup hazard for fiat
        fa.set_hazard(self.hazard)

        # Save the updated FIAT model
        fa.fiat_model.set_root(self.fiat_path)
        fa.fiat_model.write()

        # Delete instance of Adapter (together with all logging references)
        del fa

    def run_fiat(self):
        with cd(self.fiat_path):
            with open(self.fiat_path.joinpath("fiat.log"), "a") as log_handler:
                process = subprocess.run(
                    f'"{Settings().fiat_path.as_posix()}" run settings.toml',
                    stdout=log_handler,
                    stderr=log_handler,
                    env=environ.copy(),  # need environment variables from runtime hooks
                    check=True,
                    shell=True,
                )

        return process.returncode

    def postprocess_fiat(self):
        # Postprocess the FIAT results
        if not self.fiat_has_run_check():
            raise RuntimeError("Delft-FIAT did not run successfully!")

        # First move and rename fiat output csv
        fiat_results_path = self.impacts_path.joinpath(
            f"Impacts_detailed_{self.name}.csv"
        )
        shutil.copy(self.fiat_path.joinpath("output", "output.csv"), fiat_results_path)

        # Add exceedance probability if needed (only for risk)
        if self.hazard.mode == Mode.risk:
            fiat_results_df = self._add_exeedance_probability(fiat_results_path)

        # Get the results dataframe
        fiat_results_df = pd.read_csv(fiat_results_path)

        # Create the infometrics files
        metrics_path = self._create_infometrics(fiat_results_df)

        # Create the infographic files
        if self.site_info.attrs.fiat.infographics:
            self._create_infographics(self.hazard.mode, metrics_path)

        if self.hazard.mode == Mode.risk:
            # Calculate equity based damages
            self._create_equity(metrics_path)

        # Aggregate results to regions
        self._create_aggregation(metrics_path)

        # Merge points data to building footprints
        self._create_footprints(fiat_results_df)

        # Create a roads spatial file
        if self.site_info.attrs.fiat.roads_file_name:
            self._create_roads(fiat_results_df)

        self._logger.info("Post-processing complete!")

        # If site config is set to not keep FIAT simulation, then delete folder
        if not self.site_info.attrs.fiat.save_simulation:
            try:
                shutil.rmtree(self.fiat_path)
            except OSError as e_info:
                self._logger.warning(f"{e_info}\nCould not delete {self.fiat_path}.")

    def _create_roads(self, fiat_results_df):
        self._logger.info("Saving road impacts...")
        # Read roads spatial file
        roads = gpd.read_file(
            self.fiat_path.joinpath("output", self.site_info.attrs.fiat.roads_file_name)
        )
        # Get columns to use
        aggr_cols = [
            name for name in fiat_results_df.columns if "Aggregation Label:" in name
        ]
        inun_cols = [name for name in roads.columns if "Inundation Depth" in name]
        # Merge data
        roads = roads[["Object ID", "geometry"] + inun_cols].merge(
            fiat_results_df[["Object ID", "Primary Object Type"] + aggr_cols],
            on="Object ID",
        )
        # Save as geopackage
        outpath = self.impacts_path.joinpath(f"Impacts_roads_{self.name}.gpkg")
        roads.to_file(outpath, driver="GPKG")

    def _create_equity(self, metrics_path):
        self._logger.info("Calculating equity weighted risk...")
        # Get metrics tables
        metrics_fold = metrics_path.parent
        # loop through metrics aggregated files
        for file in metrics_fold.glob(f"Infometrics_{self.name}_*.csv"):
            # Load metrics
            aggr_label = file.stem.split(f"_{self.name}_")[-1]
            ind = [
                i
                for i, aggr in enumerate(self.site_info.attrs.fiat.aggregation)
                if aggr.name == aggr_label
            ][0]
            if not self.site_info.attrs.fiat.aggregation[ind].equity:
                continue

            fiat_data = pd.read_csv(file)

            # Create Equity object
            equity = Equity(
                census_table=self.database.static_path.joinpath(
                    self.site_info.attrs.fiat.aggregation[ind].equity.census_data
                ),
                damages_table=fiat_data,
                aggregation_label=self.site_info.attrs.fiat.aggregation[ind].field_name,
                percapitaincome_label=self.site_info.attrs.fiat.aggregation[
                    ind
                ].equity.percapitaincome_label,
                totalpopulation_label=self.site_info.attrs.fiat.aggregation[
                    ind
                ].equity.totalpopulation_label,
                damage_column_pattern="TotalDamageRP{rp}",
            )
            # Calculate equity
            # TODO gamma in configuration file?
            gamma = 1.2  # elasticity
            df_equity = equity.equity_calculation(gamma)
            # Merge with metrics tables and resave
            metrics_new = fiat_data.merge(
                df_equity,
                left_on=fiat_data.columns[0],
                right_on=self.site_info.attrs.fiat.aggregation[ind].field_name,
                how="left",
            )
            del metrics_new[self.site_info.attrs.fiat.aggregation[ind].field_name]
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
            metrics_new.to_csv(file)

    def _create_aggregation(self, metrics_path):
        self._logger.info("Saving impacts on aggregation areas...")

        # Define where aggregated results are saved
        output_fold = self.impacts_path
        # Get metrics tables
        metrics_fold = metrics_path.parent

        # loop through metrics aggregated files
        for file in metrics_fold.glob(f"Infometrics_{self.name}_*.csv"):
            # Load metrics
            metrics = pd.read_csv(file)
            # Load aggregation areas
            aggr_label = file.stem.split(f"_{self.name}_")[-1]
            ind = [
                i
                for i, n in enumerate(self.site_info.attrs.fiat.aggregation)
                if n.name == aggr_label
            ][0]
            aggr_areas_path = self.database.static_path.joinpath(
                self.site_info.attrs.fiat.aggregation[ind].file
            )

            aggr_areas = gpd.read_file(aggr_areas_path, engine="pyogrio")
            # Define output path
            outpath = output_fold.joinpath(
                f"Impacts_aggregated_{self.name}_{aggr_label}.gpkg"
            )
            # Save file
            AggregationAreas.write_spatial_file(
                metrics,
                aggr_areas,
                outpath,
                id_name=self.site_info.attrs.fiat.aggregation[ind].field_name,
                file_format="geopackage",
            )

    def _create_footprints(self, fiat_results_df):
        self._logger.info("Saving impacts on building footprints...")

        # Get footprints file paths from site.toml
        # TODO ensure that if this does not happen we get same file name output from FIAT?
        # Check if there is a footprint file given
        if not self.site_info.attrs.fiat.building_footprints:
            raise ValueError("No building footprints are provided.")
        # Get footprints file
        footprints_path = self.database.static_path.joinpath(
            self.site_info.attrs.fiat.building_footprints
        )
        # Define where footprint results are saved
        outpath = self.impacts_path.joinpath(
            f"Impacts_building_footprints_{self.name}.gpkg"
        )

        # Read files
        # TODO Will it save time if we load this footprints once when the database is initialized?
        footprints = gpd.read_file(footprints_path, engine="pyogrio")
        # Step to ensure that results is not a Geodataframe
        if "geometry" in fiat_results_df.columns:
            del fiat_results_df["geometry"]
        # Check if there is new development area
        new_development_area = None
        file_path = self.fiat_path.joinpath(
            "output", self.site_info.attrs.fiat.new_development_file_name
        )
        if file_path.exists():
            new_development_area = gpd.read_file(file_path)
        # Save file
        PointsToFootprints.write_footprint_file(
            footprints, fiat_results_df, outpath, extra_footprints=new_development_area
        )

    def _add_exeedance_probability(self, fiat_results_path):
        """Add exceedance probability to the fiat results dataframe.

        Parameters
        ----------
        fiat_results_path : str
            Path to the fiat results csv file

        Returns
        -------
        pandas.DataFrame
        FIAT results dataframe with exceedance probability added
        """
        # Get config path
        config_path = self.database.static_path.joinpath(
            "templates", "infometrics", "metrics_additional_risk_configs.toml"
        )
        with open(config_path, mode="rb") as fp:
            config = tomli.load(fp)["flood_exceedance"]

        # Check whether all configs are present
        if not all(key in config for key in ["column", "threshold", "period"]):
            raise ValueError("Not all required keys are present in the config file.")

        # Get the exceedance probability
        fiat_results_df = ExceedanceProbabilityCalculator(
            config["column"]
        ).append_to_file(
            fiat_results_path, fiat_results_path, config["threshold"], config["period"]
        )

        return fiat_results_df

    def _create_infometrics(self, fiat_results_df) -> Path:
        # Get the metrics configuration
        self._logger.info("Calculating infometrics...")

        if self.hazard.mode == Mode.risk:
            ext = "_risk"
        else:
            ext = ""

        # Get options for metric configurations
        metric_types = ["mandatory", "additional"]  # these are checked always

        if self.site_info.attrs.fiat.infographics:  # if infographics are created
            metric_types += ["infographic"]

        metric_config_paths = [
            self.database.static_path.joinpath(
                "templates", "infometrics", f"{name}_metrics_config{ext}.toml"
            )
            for name in metric_types
        ]

        # Specify the metrics output path
        metrics_outputs_path = self.database.scenarios.get_database_path(
            get_input_path=False
        ).joinpath(
            self.name,
            f"Infometrics_{self.name}.csv",
        )

        # Write the metrics to file
        # Check if type of metric configuration is available
        for metric_file in metric_config_paths:
            if metric_file.exists():
                metrics_writer = MetricsFileWriter(metric_file)

                metrics_writer.parse_metrics_to_file(
                    df_results=fiat_results_df,
                    metrics_path=metrics_outputs_path,
                    write_aggregate=None,
                )

                metrics_writer.parse_metrics_to_file(
                    df_results=fiat_results_df,
                    metrics_path=metrics_outputs_path,
                    write_aggregate="all",
                )
            else:
                if "mandatory" in metric_file.name.lower():
                    raise FileNotFoundError(
                        f"Mandatory metric configuration file {metric_file} does not exist!"
                    )

        return metrics_outputs_path

    def _create_infographics(self, mode, metrics_path):
        self._logger.info("Creating infographics...")

        # Check if infographics config file exists
        if mode == "risk":
            config_path = self.database.static_path.joinpath(
                "templates", "Infographics", "config_risk_charts.toml"
            )
            if not config_path.exists():
                self._logger.warning(
                    "Risk infographic cannot be created, since 'config_risk_charts.toml' is not available"
                )
                return

        # Get the infographic
        InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=mode,
            scenario_name=self.name,
            metrics_full_path=metrics_path,
            config_base_path=self.database.static_path.joinpath(
                "templates", "Infographics"
            ),
            output_base_path=self.database.scenarios.get_database_path(
                get_input_path=False
            ).joinpath(self.name),
        ).write_infographics_to_file()
