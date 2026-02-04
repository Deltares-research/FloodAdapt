from pathlib import Path

from pydantic import BaseModel

from flood_adapt.config.impacts import FloodmapType
from flood_adapt.objects.events.events import Mode


class FloodMap(BaseModel):
    name: str
    map_type: FloodmapType
    mode: Mode
    paths: list[Path]
