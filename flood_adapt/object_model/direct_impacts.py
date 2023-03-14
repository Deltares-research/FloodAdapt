from pathlib import Path

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.hazard import Hazard, ScenarioModel
from flood_adapt.object_model.projection import Projection

# from flood_adapt.object_model.scenario import ScenarioModel
from flood_adapt.object_model.strategy import Strategy


class DirectImpacts:
    """class holding all information related to the direct impacts of the scenario.
    Includes functions to run the impact model or check if it has already been run.
    """

    database_input_path: Path
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy
    hazard: Hazard

    def __init__(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.database_input_path = database_input_path
        self.set_socio_economic_change(scenario.projection)
        self.set_impact_strategy(scenario.strategy)
        self.set_hazard(scenario, database_input_path)

    def set_socio_economic_change(self, projection: str) -> None:
        """Sets the SocioEconomicChange object of the actual scenario

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
        strategy_path = (
            self.database_input_path / "Strategies" / strategy / f"{strategy}.toml"
        )
        self.impact_strategy = Strategy.load_file(strategy_path).get_impact_strategy()

    def set_hazard(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.hazard = Hazard(scenario, database_input_path)
