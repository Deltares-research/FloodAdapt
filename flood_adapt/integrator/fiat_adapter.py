from pathlib import Path

from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.site import Site


class FiatAdapter:
    def __init__(self, database_path: Path, scenario: ScenarioModel) -> None:
        self.scenario = scenario
        self.fiat_template_path = database_path / "static" / "templates" / "fiat"
        self.bfe_path = list((database_path / "static" / "bfe").glob("*.shp"))[0]
        self.results_path = database_path / "output" / "results" / scenario.name
        self.site = Site.load_file(database_path / "static" / "site" / "site.toml")

        # # If path for results does not yet exist, make it
        # if not self.results_path.is_dir():
        #     self.results_path.mkdir()

        # Create a temp folder for all temporary files.
        temp_folder = self.results_path / "temp"
        if not temp_folder.is_dir():
            temp_folder.mkdir(parents=True, exist_ok=True)

        # Make a copy of the base configuration file.
        self.config_path = self.results_path / "configuration_file.xlsx"
        base_config_path = self.fiat_template_path / "base_configuration_file.xlsx"
        copyfile(base_config_path, self.config_path)

        config_file = load_workbook(self.config_path)
        # Change Site Name and Scenario Name in configuration.xlsx.
        # This does nothing for the FIAT calculation but you can
        # check it later.
        sheet = config_file["Settings"]
        sheet["A2"] = self.site.attrs.long_name
        sheet["B2"] = self.scenario.name

        # Copy the coordinate reference system to the output CRS cell.
        sheet["C2"] = self.site.attrs.fiat.exposure_crs

        # Copy the unit to the vertical unit field in the configuration file.
        sheet["D2"] = self.site.attrs.sfincs.floodmap_units._value_

        # Change the relative paths to full paths for the exposure data
        sheet = config_file["Exposure"]
        sheet["A2"] = str(self.fiat_template_path / sheet["A2"].value)
        sheet["B2"] = self.site.attrs.fiat.exposure_crs

        # Change the relative paths to full paths for the damage function data
        sheet = config_file["Damage Functions"]
        for i in range(1, sheet.max_row):
            sheet["B" + str(i + 1)] = str(
                self.fiat_template_path / sheet["B" + str(i + 1)].value
            )

        config_file.save(self.config_path)

        # Read the updated config file
        read_config_file(self.config_path, check=False)

    def set_hazard(self, hazard: Hazard) -> None:
        # TODO add option for probabilistic event
        pass
        # Check type of event
        if hasattr(hazard, "ensemble"):
            raise NotImplementedError
        elif hasattr(hazard, "event"):
            event_or_RP = ["event"] * len(hazard.hazard_map_paths)

        # Check what type of hazard maps are given
        if self.site.attrs.fiat.floodmap_type == "water_level":
            wd_swe = "Datum"
        elif self.site.attrs.fiat.floodmap_type == "water_depth":
            wd_swe = "DEM"

        # Get the crs of the hazard map.
        if str(hazard.hazard_map_paths[0]).endswith(".tif"):
            # TODO do we need this since this is created based on the site config?
            raise NotImplementedError
            src = gdal.Open(str(hazard.hazard_map_paths[0]))
            proj = osr.SpatialReference(wkt=src.GetProjection())
            epsg = proj.GetAttrValue("AUTHORITY", 1)
        else:
            epsg = CRS.from_user_input(self.site.attrs.sfincs.csname).to_authority()[-1]

        # Fill the Hazard sheet in the configuration file.
        config_file = load_workbook(self.config_path)
        sheet = config_file["Hazard"]
        for i, flood_map in enumerate(hazard.hazard_map_paths):
            sheet["A" + str(i + 2)] = str(flood_map)
            # If this is defined as 'event', only damage is calculated.
            sheet["B" + str(i + 2)] = event_or_RP[i]
            sheet["C" + str(i + 2)] = "EPSG:" + epsg
            sheet["D" + str(i + 2)] = wd_swe

        config_file.save(self.config_path)
