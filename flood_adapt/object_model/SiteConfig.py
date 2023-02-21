from flood_adapt.object_model.io.config_io import read_config
import flood_adapt.object_model.validate.config as val

class SiteConfig():
    def __init__(self, config_path):
        self.config_path = config_path
        self.build()

    def build(self):
        #Reading is done by read_config()
        if val.validate_existence_config_file(self.config_path):
            config = read_config(self.config_path)

        #Add variables as attributes of the class
        mandatory_attributes = ["name","long_name","lat","lon","csname","cstype","sfincs","slr","gui","return_periods","dem","fiat","aggregation","floodmap"]
        non_mandatory_attributes = ["river","obs_station","tim"]
        mandatory_sfincs = ["version","offshore_model","overland_model","datum_offshore_model","datum_overland_model","diff_datum_offshore_overland","tidal_components","ambient_air_pressure"]
        mandatory_slr = ["vertical_offset","relative_to_year"]
        # mandatory_gui = ["tide_harmonic_amplitude","flooding_threshold","return_periods"]
        # mandatory_dem = ["filename","units"]
        # mandatory_fiat = ["indexfilename","exposure_crs"]
        # mandatory_aggregation = ["shapefiles","field_names"]
        # mandatory_floodmap = ["type","no_data_value","units"]
        if val.validate_content_config_file(config,self.config_path,mandatory_attributes):
            for attr in mandatory_attributes:
                if attr == "sfincs":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_sfincs)
                elif attr == "slr":
                    val.validate_content_config_file(config[attr],self.config_path,mandatory_slr)
                #Is this a good way to check attributes of a dict?
                setattr(self,attr,config[attr])

            for attr in non_mandatory_attributes:
                for key in config:
                    if attr == key:
                        setattr(self,attr,config[attr])


#Test if class works
path = r'c:\Github\flood_adapt\tests\test_database\charleston\static\site\charleston_vs2.toml'
data = SiteConfig(config_path=path)

print('finished')
