import logging
import shutil
import subprocess
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_write_metrics_file import MetricsFileWriter
from fiat_toolbox.spatial_output.aggregation_areas import AggregationAreas
from fiat_toolbox.spatial_output.points_to_footprint import PointsToFootprints

from flood_adapt.integrator.fiat_adapter import FiatAdapter
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.hazard import Hazard, ScenarioModel
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.site import Site

# from flood_adapt.object_model.scenario import ScenarioModel
from flood_adapt.object_model.strategy import Strategy
from flood_adapt.object_model.utils import cd


class DirectImpacts:
    """Class holding all information related to the direct impacts of the scenario.
    Includes methods to run the impact model or check if it has already been run.
    """

    name: str
    database_input_path: Path
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy
    hazard: Hazard
    has_run: bool = False

    def __init__(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.name = scenario.name
        self.database_input_path = database_input_path
        self.scenario = scenario
        self.set_socio_economic_change(scenario.projection)
        self.set_impact_strategy(scenario.strategy)
        self.set_hazard(scenario, database_input_path)
        # Define results path
        self.results_path = (
            self.database_input_path.parent
            / "output"
            / "results"
            / self.scenario.name
            / "fiat_model"
        )
        self.has_run = self.fiat_has_run_check()

    def fiat_has_run_check(self):
        """Checks if fiat has run as expected

        Returns
        -------
        boolean
            True if fiat has run, False if something went wrong
        """
        fiat_path = self.results_path
        log_file = fiat_path.joinpath("output", "fiat.log")
        if log_file.exists():
            with open(log_file) as f:
                if "All done!" in f.read():
                    return True
                else:
                    return False
        else:
            return False

    def set_socio_economic_change(self, projection: str) -> None:
        """Sets the SocioEconomicChange object of the scenario.

        Parameters
        ----------
        projection : str
            Name of the projection used in the scenario
        """
        projection_path = (
            self.database_input_path / "Projections" / projection / f"{projection}.toml"
        )
        self.socio_economic_change = Projection.load_file(
            projection_path
        ).get_socio_economic_change()

    def set_impact_strategy(self, strategy: str) -> None:
        """Sets the ImpactStrategy object of the scenario.

        Parameters
        ----------
        strategy : str
            Name of the strategy used in the scenario
        """
        strategy_path = (
            self.database_input_path / "Strategies" / strategy / f"{strategy}.toml"
        )
        self.impact_strategy = Strategy.load_file(strategy_path).get_impact_strategy()

    def set_hazard(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        """Sets the Hazard object of the scenario.

        Parameters
        ----------
        scenario : str
            Name of the scenario
        """
        self.hazard = Hazard(scenario, database_input_path)

    def preprocess_models(self):
        logging.info("Preparing impact models...")
        # Preprocess all impact model input
        start_time = time.time()
        self.preprocess_fiat()
        end_time = time.time()
        print(f"FIAT preprocessing took {str(round(end_time - start_time, 2))} seconds")

    def run_models(self):
        logging.info("Running impact models...")
        start_time = time.time()
        return_code = self.run_fiat()
        end_time = time.time()
        print(f"Running FIAT took {str(round(end_time - start_time, 2))} seconds")

        self.postprocess_fiat()

        # Indicator that direct impacts have run
        if return_code == 0:
            self.__setattr__("has_run", True)

    def postprocess_models(self):
        logging.info("Post-processing impact models...")
        # Preprocess all impact model input
        self.postprocess_fiat()

    def preprocess_fiat(self):
        """Updates FIAT model based on scenario information and then runs the FIAT model"""

        # Check if hazard is already run
        if not self.hazard.has_run:
            raise ValueError(
                "Hazard for this scenario has not been run yet! FIAT cannot be initiated."
            )

        # Get the location of the FIAT template model
        template_path = (
            self.database_input_path.parent / "static" / "templates" / "fiat"
        )

        # Read FIAT template with FIAT adapter
        fa = FiatAdapter(
            model_root=template_path, database_path=self.database_input_path.parent
        )

        # If path for results does not yet exist, make it
        if not self.results_path.is_dir():
            self.results_path.mkdir(parents=True)
        else:
            shutil.rmtree(self.results_path)

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
                self.database_input_path
                / "projections"
                / self.scenario.projection
                / self.socio_economic_change.attrs.new_development_shapefile
            )

            fa.apply_population_growth_new(
                population_growth=self.socio_economic_change.attrs.population_growth_new,
                ground_floor_height=self.socio_economic_change.attrs.new_development_elevation.value,
                elevation_type=self.socio_economic_change.attrs.new_development_elevation.type,
                area_path=area_path,
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
                print("Impact measure type not recognized!")

        # setup hazard for fiat
        fa.set_hazard(self.hazard)

        # Save the updated FIAT model
        fa.fiat_model.set_root(self.results_path)
        fa.fiat_model.write()

    def run_fiat(self):
        fiat_exec = str(
            self.database_input_path.parents[2] / "system" / "fiat" / "fiat.exe"
        )
        results_dir = self.database_input_path.parent.joinpath(
            "output", "results", self.name
        )
        with cd(self.results_path):
            with open(results_dir.joinpath("fiat.log"), "a") as log_handler:
                process = subprocess.run(
                    f'"{fiat_exec}" run settings.toml',
                    stdout=log_handler,
                    check=True,
                    shell=True,
                )

            return process.returncode

    def postprocess_fiat(self):
        # Get the metrics
        fiat_results_path = self.database_input_path.parent.joinpath(
            "output",
            "results",
            f"{self.name}",
            "fiat_model",
            "output",
            "output.csv",
        )
        # Create the infometrics files
        self._create_infometrics(fiat_results_path)

        # Create the infographic files
        self._create_infographics(self.hazard.event_mode)

        # Aggregate results to regions
        self._create_aggregation()

        # Create equity
        self._create_equity()

        # Merge points data to building footprints
        self._create_footprints(fiat_results_path)

    def _create_equity(self):
        pass

    def _create_aggregation(self):
        # Define where aggregated results are saved
        output_fold = self.database_input_path.parent.joinpath(
            "output", "results", f"{self.name}"
        )
        # Get metrics tables
        metrics_fold = self.database_input_path.parent.joinpath("output", "infometrics")
        # Get aggregation area file paths from site.toml
        site_toml = (
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        site_info = Site.load_file(site_toml)
        # loop through metrics aggregated files
        for file in metrics_fold.glob(f"{self.name}_metrics_*.*"):
            # Load metrics
            metrics = pd.read_csv(file)
            # Load aggregation areas
            aggr_label = file.stem.split("_metrics_")[-1]
            ind = [
                i
                for i, n in enumerate(site_info.attrs.fiat.aggregation)
                if n.name == aggr_label
            ][0]
            aggr_areas_path = Path(
                self.database_input_path.parent
                / "static"
                / "site"
                / site_info.attrs.fiat.aggregation[ind].file
            )

            aggr_areas = gpd.read_file(aggr_areas_path, engine="pyogrio")
            # Define output path
            outpath = output_fold.joinpath(f"aggregated_damages_{aggr_label}.gpkg")
            # Save file
            AggregationAreas.write_spatial_file(
                metrics,
                aggr_areas,
                outpath,
                id_name=site_info.attrs.fiat.aggregation[ind].field_name,
                file_format="geopackage",
            )

    def _create_footprints(self, fiat_results_path):
        # Get footprints file paths from site.toml
        site_toml = (
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        site_info = Site.load_file(site_toml)
        # TODO ensure that if this does not happen we get same file name output from FIAT?
        # Check if there is a footprint file given
        if not site_info.attrs.fiat.building_footprints:
            return
        # Get footprints file
        footprints_path = (
            self.database_input_path.parent
            / "static"
            / "site"
            / site_info.attrs.fiat.building_footprints
        )
        # Define where footprint results are saved
        outpath = self.database_input_path.parent.joinpath(
            "output", "results", f"{self.name}", "building_footprints.gpkg"
        )

        # Read files
        # TODO Will it save time if we load this footprints once when the database is initialized?
        footprints = gpd.read_file(footprints_path, engine="pyogrio")
        results = pd.read_csv(fiat_results_path)
        # Step to ensure that results is not a Geodataframe
        if "geometry" in results.columns:
            del results["geometry"]
        # Save file
        PointsToFootprints.write_footprint_file(footprints, results, outpath)

    def _create_infometrics(self, fiat_results_path):
        # Get the metrics configuration
        if self.hazard.event_mode == "risk":
            ext = "_risk"
        else:
            ext = ""

        metrics_config_path = self.database_input_path.parent.joinpath(
            "static",
            "templates",
            "infometrics",
            f"metrics_config{ext}.toml",
        )

        # Specify the metrics output path
        metrics_outputs_path = self.database_input_path.parent.joinpath(
            "output",
            "infometrics",
            f"{self.name}_metrics.csv",
        )

        # Get the results dataframe
        df = pd.read_csv(fiat_results_path)

        # Write the metrics to file
        metrics_writer = MetricsFileWriter(metrics_config_path)

        metrics_writer.parse_metrics_to_file(
            df_results=df, metrics_path=metrics_outputs_path, write_aggregate=None
        )

        if self.hazard.event_mode != "risk":
            metrics_writer.parse_metrics_to_file(
                df_results=df, metrics_path=metrics_outputs_path, write_aggregate="all"
            )

    def _create_infographics(self, mode):
        # Get the infographic
        database_path = Path(self.database_input_path).parent
        metrics_path = database_path.joinpath(
            "output", "infometrics", f"{self.name}_metrics.csv"
        )
        config_path = database_path.joinpath("static", "templates", "infographics")
        output_path = database_path.joinpath("output", "infographics")
        InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=mode,
            scenario_name=self.name,
            metrics_full_path=metrics_path,
            config_base_path=config_path,
            output_base_path=output_path,
        ).write_infographics_to_file()
