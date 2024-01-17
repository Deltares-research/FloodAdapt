import pathlib as Path

import tomli

# Get the directory that contains the currently executing script
current_dir = Path.Path(__file__).parent

# Get the path to the config.toml file
config_path = current_dir / "config.toml"

# Load the TOML file
config = tomli.load(config_path)

# Set the variables based on the values in the TOML file
__version__ = config["version"]
__database_root__ = Path.Path(config["database_root"])
__system_folder__ = Path.Path(config["system_folder"])
