import os
from enum import Enum
from pathlib import Path

from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.interface.models import Mode
from flood_adapt.object_model.interface.database_user import IDatabaseUser


class FloodMapType(str, Enum):
    """Enum class for the type of flood map."""

    WATER_LEVEL = "water_level"  # TODO make caps, but hydromt_fiat expects lowercase


class FloodMap(IDatabaseUser):
    _type: FloodMapType = FloodMapType.WATER_LEVEL

    name: str
    path: Path | os.PathLike | list[Path | os.PathLike]
    event_set: EventSet
    # mode: Mode
    # physical_projection: PhysicalProjection
    # hazard_strategy: HazardStrategy

    def __init__(self, scenario_name: str) -> None:
        self.name = scenario_name
        base_dir = self.database.scenarios.output_path / scenario_name / "Flooding"

        if self.mode == Mode.single_event:
            self.path = base_dir / "max_water_level_map.nc"
        elif self.mode == Mode.risk:
            self.path = list(
                base_dir.glob("RP_*_maps.nc")
            )  # TODO: check if this is correct

    @property
    def has_run(self) -> bool:
        if self.mode == Mode.single_event:
            return self.path.exists()
        elif self.mode == Mode.risk:
            check_files = [RP_map.exists() for RP_map in self.path]
            check_rps = len(self.path) == len(
                self.database.site.attrs.risk.return_periods
            )
            return all(check_files) & check_rps

    @property
    def scenario(self):
        if hasattr(self, "_scenario"):
            return self._scenario
        self._scenario = self.database.scenarios.get(self.name)
        return self._scenario

    @property
    def mode(self):
        if hasattr(self, "_mode"):
            return self._mode
        self._mode = self.database.events.get(self.scenario.attrs.event).attrs.mode
        return self._mode

    @property
    def crs(self):
        if hasattr(self, "_crs"):
            return self._crs
        self._crs = self.database.site.attrs.crs
        return self._crs

    @property
    def hazard_strategy(self):
        if hasattr(self, "_hazard_strategy"):
            return self._hazard_strategy
        self._hazard_strategy = self.database.strategies.get(
            self.scenario.attrs.strategy
        ).get_hazard_strategy()
        return self._hazard_strategy

    @property
    def physical_projection(self):
        if hasattr(self, "_physical_projection"):
            return self._physical_projection
        self._physical_projection = self.database.projections.get(
            self.scenario.attrs.projection
        ).get_physical_projection()
        return self._physical_projection