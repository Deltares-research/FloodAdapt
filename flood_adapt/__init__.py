from pathlib import Path

# has to be here at the start to avoid circular imports
__version__ = "0.1.3"
SRC_DIR: Path = Path(__file__).parent

from flood_adapt.log import FloodAdaptLogging  # noqa: E402

FloodAdaptLogging()  # Initialize logging once for the entire package
