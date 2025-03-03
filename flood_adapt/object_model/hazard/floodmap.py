from pathlib import Path

from pydantic import BaseModel

from flood_adapt.object_model.hazard.interface.events import Mode
from flood_adapt.object_model.interface.config.sfincs import FloodmapType


class FloodMap(BaseModel):
    type: FloodmapType
    name: str
    path: list[Path]
    mode: Mode


# class FloodMap2:
#     logger = FloodAdaptLogging.getLogger("FloodMap")

#     type: FloodmapType = FloodmapType.water_level

#     name: str
#     path: Path | os.PathLike | list[Path | os.PathLike]

#     @model_validator(mode="after")
#     def check_path(self):
#         if isinstance(self.path, list):
#             for p in self.path:
#                 if not Path(p).exists():
#                     raise ValueError(f"Path {p} does not exist")
#         else:
#             if not Path(self.path).exists():
#                 raise ValueError(f"Path {self.path} does not exist")
#         return self

#     def __init__(self, path: Path, event_mode: Mode, type: FloodmapType) -> None:
#         # self.name = scenario_name
#         # self.type = self.database.site.attrs.fiat.config.floodmap_type
#         self.type = type
#         self.name = path.stem
#         self.path = path
#         self.mode = event_mode

#         self._get_flood_map_paths()

#     def _get_flood_map_paths(self):
#         base_dir = self.database.scenarios.output_path / self.name / "Flooding"
#         # TODO check naming of files
#         if self.mode == Mode.single_event:
#             if self.type == FloodmapType.water_level:
#                 self.path = base_dir / "max_water_level_map.nc"
#             elif self.type == FloodmapType.water_depth:
#                 self.path = base_dir / f"FloodMap_{self.name}.tif"
#         elif self.mode == Mode.risk:
#             if self.type == FloodmapType.water_level:
#                 self.path = list(base_dir.glob("RP_*_maps.nc"))
#             elif self.type == FloodmapType.water_depth:
#                 self.path = list(base_dir.glob("RP_*_maps.tif"))

#     @property
#     def has_run(self) -> bool:
#         if self.mode == Mode.single_event:
#             return self.path.exists()
#         elif self.mode == Mode.risk:
#             check_files = [RP_map.exists() for RP_map in self.path]
#             check_rps = len(self.path) == len(
#                 self.database.site.attrs.fiat.risk.return_periods
#             )
#             return all(check_files) & check_rps
#         else:
#             return False

#     @property
#     def scenario(self):
#         if hasattr(self, "_scenario"):
#             return self._scenario
#         self._scenario = self.database.scenarios.get(self.name)
#         return self._scenario

# @property
# def mode(self):
#     if hasattr(self, "_mode"):
#         return self._mode
#     self._mode = self.database.events.get(self.scenario.attrs.event).attrs.mode
#     return self._mode

# @property
# def crs(self):
#     if hasattr(self, "_crs"):
#         return self._crs
#     self._crs = self.database.site.attrs.sfincs.config.cstype
#     return self._crs

# @property
# def hazard_strategy(self):
#     if hasattr(self, "_hazard_strategy"):
#         return self._hazard_strategy
#     self._hazard_strategy = self.database.strategies.get(
#         self.scenario.attrs.strategy
#     ).get_hazard_strategy()
#     return self._hazard_strategy

# @property
# def physical_projection(self):
#     if hasattr(self, "_physical_projection"):
#         return self._physical_projection
#     self._physical_projection = self.database.projections.get(
#         self.scenario.attrs.projection
#     ).get_physical_projection()
#     return self._physical_projection
