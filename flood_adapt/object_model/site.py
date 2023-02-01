from flood_adapt.object_model.io.config_io import read_config
import flood_adapt.object_model.validate.config as val

class SiteConfig():
    def __init__(self, config_path):
        self.config_path = config_path
        self.build()

    def build(self):
        #Reading of toml file is done by read_config()
        if val.validate_existence_config_file(self.config_path):
            config = read_config(self.config_path)

        #Keys of dictionaries
        mandatory_attributes = ["name","long_name","lat","lon","sfincs","slr","risk","gui","dem","fiat"]
        non_mandatory_attributes = ["river","obs_station"]
        mandatory_sfincs = ["csname","cstype","version","offshore_model","overland_model","datum_offshore_model","datum_overland_model","diff_datum_offshore_overland","tidal_components","ambient_air_pressure","floodmap_no_data_value","floodmap_units"]
        mandatory_slr = ["vertical_offset","relative_to_year"]
        mandatory_risk = ["return_periods","flooding_threshold"]
        mandatory_gui = ["tide_harmonic_amplitude"]
        mandatory_dem = ["filename","units","indexfilename"]
        mandatory_fiat = ["exposure_crs","aggregation_shapefiles","aggregation_field_names","floodmap_type"]
        if val.validate_content_config_file(config,self.config_path,mandatory_attributes):
            for attr in mandatory_attributes:
                #Check if attributes have correct dictionary keys (if applicable)
                if attr == "sfincs":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_sfincs)
                elif attr == "slr":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_slr)
                elif attr == "risk":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_risk)
                elif attr == "gui":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_gui)
                elif attr == "dem":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_dem)
                elif attr == "fiat":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_fiat)
                #Add the attributes
                setattr(self,attr,config[attr])

            for attr in non_mandatory_attributes:
                for key in config:
                    if attr == key:
                        setattr(self,attr,config[attr])