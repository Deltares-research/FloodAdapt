from pathlib import Path

from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.strategy import Strategy


class DirectImpacts:
    """The DirectImpacts class containing all information on a single direct impact scenario."""

    def __init__(self, data: dict):
        # TODO: How to get the paths of the database?
        projection_path = Path(
            DatabaseIO().projections_path, data.projection, f"{data.projection}.toml"
        )

        strategy_path = Path(
            DatabaseIO().strategies_path, data.strategy, f"{data.strategy}.toml"
        )

        Path(DatabaseIO().scenarios_path, data.event, f"{data.event}.toml")

        # Create objects
        self.socio_economic_change = Projection.load_file(
            projection_path
        ).get_socio_economic_change()
        self.impact_strategy = Strategy.load_file(strategy_path).get_impact_strategy()
