# has to be here at the start to avoid circular imports
__version__ = "0.2.0"

from flood_adapt import adapter, dbs_classes, object_model
from flood_adapt import api as API
from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.io import unit_system

__all__ = [
    "Settings",
    "FloodAdaptLogging",
    "unit_system",
    "API",
    "object_model",
    "dbs_classes",
    "adapter",
]

FloodAdaptLogging()  # Initialize logging once for the entire package
