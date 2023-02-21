from flood_adapt.object_model.strategy import Strategy
from flood_adapt.object_model.measures.elevate import Elevate



# strat_file = r'd:\GitHub\FloodAdapt\tests\test_database\charleston\input\strategies\elevate\elevate.toml'
# elevate = Strategy()
# elevate.load()

measure_files = [r'd:\GitHub\FloodAdapt\tests\test_database\charleston\input\measures\raise_property_aggregation_area\raise_property_aggregation_area.toml',
                 r'd:\GitHub\FloodAdapt\tests\test_database\charleston\input\measures\raise_property_all_properties\raise_property_all_properties.toml',
                 r'd:\GitHub\FloodAdapt\tests\test_database\charleston\input\measures\raise_property_draw_polygon\raise_property_draw_polygon.toml',
                 r'd:\GitHub\FloodAdapt\tests\test_database\charleston\input\measures\raise_property_import_polygon\raise_property_import_polygon.toml'
                ]

elevate_objects = []

for meas_file in measure_files:
    elevate = Elevate(meas_file)
    elevate.load()
    elevate_objects.append(elevate)

test = 'test'
