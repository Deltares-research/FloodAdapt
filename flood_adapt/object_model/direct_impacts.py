import logging
import shutil
import subprocess
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from fiat_toolbox.equity.equity import Equity
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

    def __init__(
        self, scenario: ScenarioModel, database_input_path: Path, results_path: Path
    ) -> None:
        self.name = scenario.name
        self.database_input_path = database_input_path
        self.scenario = scenario
        self.results_path = results_path
        self.set_socio_economic_change(scenario.projection)
        self.set_impact_strategy(scenario.strategy)
        self.set_hazard(
            scenario, database_input_path, self.results_path.joinpath("Flooding")
        )
        # Get site config
        self.site_toml_path = (
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        self.site_info = Site.load_file(self.site_toml_path)
        # Define results path
        self.impacts_path = self.results_path.joinpath("Impacts")
        self.fiat_path = self.impacts_path.joinpath("fiat_model")
        self.has_run = self.fiat_has_run_check()

    def fiat_has_run_check(self):
        """Checks if fiat has run as expected

        Returns
        -------
        boolean
            True if fiat has run, False if something went wrong
        """
        log_file = self.fiat_path.joinpath("fiat.log")
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

    def set_hazard(
        self, scenario: ScenarioModel, database_input_path: Path, results_dir: Path
    ) -> None:
        """Sets the Hazard object of the scenario.

        Parameters
        ----------
        scenario : str
            Name of the scenario
        """
        self.hazard = Hazard(scenario, database_input_path, results_dir)

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
        fa.fiat_model.set_root(self.fiat_path)
        fa.fiat_model.write()

    def run_fiat(self):
        fiat_exec = str(
            self.database_input_path.parents[2] / "system" / "fiat" / "fiat.exe"
        )
        with cd(self.fiat_path):
            with open(self.fiat_path.joinpath("fiat.log"), "a") as log_handler:
                process = subprocess.run(
                    f'"{fiat_exec}" run settings.toml',
                    stdout=log_handler,
                    check=True,
                    shell=True,
                )

            return process.returncode

    def postprocess_fiat(self):
        # Postprocess the FIAT results
        # First move and rename fiat output csv
        fiat_results_path = self.impacts_path.joinpath(
            f"Impacts_detailed_{self.name}.csv"
        )
        shutil.copy(self.fiat_path.joinpath("output", "output.csv"), fiat_results_path)

        # Get the results dataframe
        df = pd.read_csv(fiat_results_path)

        # Create the infometrics files
        metrics_path = self._create_infometrics(df)

        # Create the infographic files
        self._create_infographics(self.hazard.event_mode, metrics_path)

        if self.hazard.event_mode == "risk":
            # Calculate equity based damages
            self._create_equity(metrics_path)

        # Aggregate results to regions
        self._create_aggregation(metrics_path)

        # Merge points data to building footprints
        self._create_footprints(df)

        # Create a roads spatial file
        if self.site_info.attrs.fiat.roads_file_name:
            self._create_roads(df)

        # TODO add this when hydromt logger issue solution has been merged
        # If site config is set to not keep FIAT simulation, then delete folder
        # if not self.site_info.attrs.fiat.save_simulation:
        # shutil.rmtree(self.fiat_path)
    
    def _create_roads(self, fiat_results):
        logging.info("Saving road impacts...")
        # Read roads spatial file
        roads = gpd.read_file(self.fiat_path.joinpath("output", self.site_info.attrs.fiat.roads_file_name))
        # Get columns to use
        aggr_cols = [name for name in fiat_results.columns if "Aggregation Label:" in name]
        inun_cols = [name for name in roads.columns if "Inundation Depth" in name]
        # Merge data
        roads = pd.merge(roads[["Object ID", "geometry"] + inun_cols], fiat_results[["Object ID", "Primary Object Type"] + aggr_cols], on="Object ID")
        # Save as geopackage
        outpath = self.impacts_path.joinpath(f"Impacts_roads_{self.name}.gpkg")
        roads.to_file(outpath, format="geopackage")

    def _create_equity(self, metrics_path):
        logging.info("Calculating equity weighted risk...")
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
                census_table=self.site_toml_path.parent.joinpath(
                    self.site_info.attrs.fiat.aggregation[ind].equity.census_data
                ),
                damages_table=fiat_data,
                aggregation_label=self.site_info.attrs.fiat.aggregation[ind].field_name,
                percapitalincome_label=self.site_info.attrs.fiat.aggregation[
                    ind
                ].equity.percapitalincome_label,
                totalpopulation_label=self.site_info.attrs.fiat.aggregation[
                    ind
                ].equity.totalpopulation_label,
                damage_column_pattern="TotalDamageRP{rp}",
            )
            # Calculate equity
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
            metrics_new.loc["Description", ["EW", "EWCEAD"]] = [
                "Equity weight",
                "Equity weighted certainty equivalent expected annual damage",
            ]
            metrics_new.loc["Show In Metrics Table", ["EW", "EWCEAD"]] = [True, True]
            metrics_new.loc["Long Name", ["EW", "EWCEAD"]] = [
                "Equity weight",
                "Equity weighted certainty equivalent expected annual damage",
            ]
            metrics_new.index.name = None
            metrics_new.to_csv(file)

    def _create_aggregation(self, metrics_path):
        logging.info("Saving impacts on aggregation areas...")

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
            aggr_areas_path = self.site_toml_path.parent.joinpath(
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

    def _create_footprints(self, results):
        logging.info("Saving impacts on building footprints...")

        # Get footprints file paths from site.toml
        # TODO ensure that if this does not happen we get same file name output from FIAT?
        # Check if there is a footprint file given
        if not self.site_info.attrs.fiat.building_footprints:
            raise ValueError("No building footprints are provided.")
        # Get footprints file
        footprints_path = self.site_toml_path.parent.joinpath(
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
        if "geometry" in results.columns:
            del results["geometry"]
        # Check if there is new development area
        new_development_area = None
        file_path = self.fiat_path.joinpath("output", self.site_info.attrs.fiat.new_development_file_name)
        if file_path.exists():
            new_development_area = gpd.read_file(file_path)
        # Save file
        PointsToFootprints.write_footprint_file(footprints, results, outpath, extra_footprints=new_development_area)

    def _create_infometrics(self, df) -> Path:
        # Get the metrics configuration
        logging.info("Calculating infometrics...")

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
            "Scenarios",
            self.name,
            f"Infometrics_{self.name}.csv",
        )

        # Write the metrics to file
        metrics_writer = MetricsFileWriter(metrics_config_path)

        metrics_writer.parse_metrics_to_file(
            df_results=df, metrics_path=metrics_outputs_path, write_aggregate=None
        )

        metrics_writer.parse_metrics_to_file(
            df_results=df, metrics_path=metrics_outputs_path, write_aggregate="all"
        )

        return metrics_outputs_path

    def _create_infographics(self, mode, metrics_path):
        logging.info("Creating infographics...")

        # Get the infographic
        database_path = Path(self.database_input_path).parent
        config_path = database_path.joinpath("static", "templates", "infographics")
        output_path = database_path.joinpath("output", "Scenarios", self.name)
        InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=mode,
            scenario_name=self.name,
            metrics_full_path=metrics_path,
            config_base_path=config_path,
            output_base_path=output_path,
        ).write_infographics_to_file()
