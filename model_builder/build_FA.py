import shutil
from pathlib import Path
from shutil import rmtree
from typing import Optional

import click
import tomli
from hydromt_fiat.fiat import FiatModel
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, Field


class configModel(BaseModel):
    """BaseModel describing the configuration parameters."""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: str = ""
    database_path: Optional[str] = "."
    sfincs: str
    sfincs_offshore: Optional[str] = None
    fiat: str


def read_config(config: str) -> dict:
    """_summary_

    Parameters
    ----------
    config : str
        _description_

    Returns
    -------
    dict
        _description_
    """
    with open(config, mode="rb") as fp:
        toml = tomli.load(fp)
    dict = configModel.model_validate(toml)
    return dict


def read_sfincs(path: str) -> SfincsModel:
    """_summary_

    Parameters
    ----------
    path : str
        _description_

    Returns
    -------
    SfincsModel
        _description_
    """
    pass


def make_input_dirs():
    pass


class Database:
    def __init__(self, config: configModel, overwrite=True):
        self.site_name = config.name
        root = Path(config.database_path).joinpath("Database", config.name)
        if root.exists() and not overwrite:
            raise ValueError(f"There is already a Database folder in '{root}'")
        else:
            rmtree(root)
            root.mkdir(parents=True)
            print(f"Initializing a FloodAdapt database in '{root}'")
        self.root = root
        self.site_attrs = {"name": config.name, "description": config.description}

    def make_folder_structure(self):
        # Prepare input folder structure
        input_path = self.root.joinpath("input")
        input_path.mkdir()
        inputs = [
            "events",
            "projections",
            "measures",
            "strategies",
            "scenarios",
            "benefits",
        ]
        for name in inputs:
            input_path.joinpath(name).mkdir()

        # Prepare static folder structure
        static_path = self.root.joinpath("static")
        static_path.mkdir()
        folders = ["templates"]
        for name in folders:
            static_path.joinpath(name).mkdir()

    def read_fiat(self, path: str) -> FiatModel:
        # First copy FIAT model to database
        fiat_path = self.root.joinpath("static", "templates", "fiat")
        shutil.copytree(path, fiat_path)

        # Then read the model with hydromt-FIAT
        self.fiat_model = FiatModel(root=fiat_path, mode="r")


@click.command()
@click.option(
    "--config_path", default="config.toml", help="Full path to the config toml file."
)
def main(config_path):
    print(f"Read FloodAdapt building configuration from {config_path}")
    config = read_config(config_path)
    dbs = Database(config)
    dbs.make_folder_structure()
    dbs.read_fiat(config.fiat)


if __name__ == "__main__":
    main(["--config_path", r"c:\Users\athanasi\Github\Database\FA_builder\config.toml"])
