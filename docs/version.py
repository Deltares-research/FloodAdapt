from pathlib import Path
from flood_adapt import __version__

with open(Path(__file__).parent / "_version.yml", "w") as f:
    f.write(f"version: {__version__}")
