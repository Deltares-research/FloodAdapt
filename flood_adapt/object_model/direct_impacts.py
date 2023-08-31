import shutil
import subprocess
from pathlib import Path

from flood_adapt.integrator.fiat_adapter import FiatAdapter
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.hazard import Hazard, ScenarioModel
from flood_adapt.object_model.projection import Projection

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

    def run_models(self):
        self.preprocess_fiat()

        return_code = self.run_fiat()

        # Indicator that direct impacts have run
        if return_code == 0:
            self.__setattr__("has_run", True)

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

        with cd(self.results_path):
            process = subprocess.run(
                f'"{fiat_exec}" run settings.toml',
                stdout=subprocess.PIPE,
                check=True,
                shell=True,
            )

            return process.returncode
