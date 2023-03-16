from pathlib import Path

import pytest

import flood_adapt.api.measures as api_measures
import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database_GUI"
test_site_name = "charleston"


def test_elevate_measure():
    test_dict = {
        "name": "raise_property_aggregation_area",
        "long_name": "test1",
        "type": "elevate_properties",
        "elevation": {"value": 1, "units": "feet", "type": "floodmap"},
        "selection_type": "aggregation_area",
        "aggregation_area_name": "test_area",
        "property_type": "RES",
    }
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)

    # When user presses add measure and fills in the Elevate object attributes
    # the dictionary is returned and an Elevate object is created
    elevate = api_measures.create_elevate_measure(test_dict, database)

    with pytest.raises(ValueError):
        # Assert error if name already exists
        api_measures.save_measure(elevate, database)

    # Change name to something new
    test_dict["name"] = "test1"
    elevate = api_measures.create_elevate_measure(test_dict, database)
    # If the name is not used before the measure is save in the database
    api_measures.save_measure(elevate, database)
    database.get_measures()

    # When user presses edit measure the dictionary is returned
    elevate_old = api_measures.get_measure("test1", database)
    elevate_edit_dict = elevate_old.attrs.dict()

    # User can make changes
    elevate_edit_dict["elevation"]["value"] = 2

    # If user presses ok the object is updated and the measure is overwritten
    elevate_edit = api_measures.create_elevate_measure(elevate_edit_dict, database)
    api_measures.edit_measure(elevate_edit, database)
    database.get_measures()

    # Try to delete a measure which is already used in a strategy
    with pytest.raises(ValueError):
        api_measures.delete_measure("raise_property_aggregation_area", database)

    # If user presses delete measure the measure is deleted
    api_measures.delete_measure("test1", database)
    database.get_measures()
