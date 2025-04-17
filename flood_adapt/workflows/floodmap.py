import os
from pathlib import Path

from flood_adapt.config.sfincs import FloodmapType
from flood_adapt.misc.database_user import DatabaseUser
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.events.events import Mode
from flood_adapt.objects.strategies.strategies import Strategy


class FloodMap(DatabaseUser):
    logger = FloodAdaptLogging.getLogger("FloodMap")

    type: FloodmapType

    name: str
    path: Path | os.PathLike | list[Path | os.PathLike]
    event_set: EventSet

    def __init__(self, scenario_name: str) -> None:
        self.name = scenario_name
        self.type = self.database.site.fiat.config.floodmap_type
        self._get_flood_map_paths()

    def _get_flood_map_paths(self):
        base_dir = self.database.scenarios.output_path / self.name / "Flooding"
        # TODO check naming of files
        if self.mode == Mode.single_event:
            if self.type == FloodmapType.water_level:
                self.path = base_dir / "max_water_level_map.nc"
            elif self.type == FloodmapType.water_depth:
                self.path = base_dir / f"FloodMap_{self.name}.tif"
        elif self.mode == Mode.risk:
            if self.type == FloodmapType.water_level:
                self.path = list(base_dir.glob("RP_*_maps.nc"))
            elif self.type == FloodmapType.water_depth:
                self.path = list(base_dir.glob("RP_*_maps.tif"))

    @property
    def has_run(self) -> bool:
        if self.mode == Mode.single_event:
            return self.path.exists()
        elif self.mode == Mode.risk:
            check_files = [RP_map.exists() for RP_map in self.path]
            check_rps = len(self.path) == len(
                self.database.site.fiat.risk.return_periods
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
        self._mode = self.database.events.get(self.scenario.event).mode
        return self._mode

    @property
    def crs(self):
        if hasattr(self, "_crs"):
            return self._crs
        self._crs = self.database.site.crs
        return self._crs

    @property
    def hazard_strategy(self) -> Strategy:
        return self.database.strategies.get(
            self.scenario.strategy
        ).get_hazard_strategy()

    @property
    def physical_projection(self):
        if hasattr(self, "_physical_projection"):
            return self._physical_projection
        self._physical_projection = self.database.projections.get(
            self.scenario.projection
        ).physical_projection
        return self._physical_projection
