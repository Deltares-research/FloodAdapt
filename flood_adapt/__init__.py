from pathlib import Path

from flood_adapt.log import FloodAdaptLogging

FloodAdaptLogging()  # Initialize logging once for the entire package

__version__ = "0.1.2"
SRC_DIR: Path = Path(__file__).parent
