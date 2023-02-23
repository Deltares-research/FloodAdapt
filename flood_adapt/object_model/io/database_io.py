from pathlib import Path

site_name_ = "charleston"  # This should be retrieved from somewhere else
database_path_ = str(Path().absolute() / 'tests' / 'test_database' / site_name_)  # This should be retrieved from somewhere else


class DatabaseIO:
    def __init__(self, database_path: str = database_path_, site_name: str = site_name_):
        self.site_name = site_name
        self.database_path = str(Path(database_path).joinpath(self.site_name))
        self.validate_path()
        self.set_paths()

    def validate_path(self):
        if not Path(self.database_path).is_dir():
            raise FileNotFoundError("Database not found at {}".format(self.database_path))

    def set_paths(self):
        # The input folders
        self.events_path = str(Path(self.database_path) / "input" / "events")
        self.measures_path = str(Path(self.database_path) / "input" / "measures")
        self.projections_path = str(Path(self.database_path) / "input" / "projections")
        self.scenarios_path = str(Path(self.database_path) / "input" / "scenarios")
        self.strategies_path = str(Path(self.database_path) / "input" / "strategies")

        # The output folders
        self.output_path = str(Path(self.database_path) / "output")
        self.simulations_path = str(Path(self.database_path) / "output" / "simulations")

        # The static folders
        self.static_path = str(Path(self.database_path) / "static")
        self.site_path = str(Path(self.database_path) / "static" / "site")
