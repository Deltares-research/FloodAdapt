from pathlib import Path

import pytest

import flood_adapt.api.projections as api_projections
import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "charleston"


def test_projection():
    test_dict = {
        "name": "SLR_2ft",
        "long_name": "SLR_2ft",
        "physical_projection": {
            "sea_level_rise": {"value": "two", "units": "feet"},
            "subsidence": {"value": 1, "units": "feet"},
        },
        "socio_economic_change": {},
    }
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)

    # When user presses add projection and chooses the projections
    # the dictionary is returned and an Projection object is created
    with pytest.raises(ValueError):
        # Assert error if a value is incorrect
        projection = api_projections.create_projection(test_dict)

    # correct projection
    test_dict["physical_projection"]["sea_level_rise"]["value"] = 2
    projection = api_projections.create_projection(test_dict)

    with pytest.raises(ValueError):
        # Assert error if name already exists
        api_projections.save_projection(projection, database)

    # Change name to something new
    test_dict["name"] = "test_proj_1"
    projection = api_projections.create_projection(test_dict)
    # If the name is not used before the measure is save in the database
    api_projections.save_projection(projection, database)
    database.get_projections()

    # Try to delete a measure which is already used in a scenario
    # with pytest.raises(ValueError):
    #    api_projections.delete_measure("", database)

    # If user presses delete projection the measure is deleted
    api_projections.delete_projection("test_proj_1", database)
    database.get_projections()
