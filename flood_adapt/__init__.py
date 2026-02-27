# has to be here at the start to avoid circular imports
__version__ = "2.0.3"

from flood_adapt import adapter, database_builder, dbs_classes, objects
from flood_adapt.config.settings import Settings
from flood_adapt.config.site import Site
from flood_adapt.flood_adapt import FloodAdapt
from flood_adapt.misc.exceptions import DatabaseError, FloodAdaptError
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.objects.forcing import unit_system

__all__ = [
    "FloodAdapt",
    "Site",
    "Settings",
    "FloodAdaptLogging",
    "unit_system",
    "objects",
    "dbs_classes",
    "adapter",
    "database_builder",
    "FloodAdaptError",
    "DatabaseError",
]

FloodAdaptLogging()  # Initialize logging once for the entire package
