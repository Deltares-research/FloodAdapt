from pathlib import Path
import pytest

test_database = Path().absolute() / 'tests' / 'test_database'


def test_all_projections():
    from flood_adapt.object_model.projection import Projection

    test_toml = test_database / "charleston" / "input" / "projections" / "all_projections" / "all_projections.toml"
    assert test_toml.is_file()

    test_projections = Projection(test_toml)
    test_projections.load()

    # Assert that the configured risk drivers are set to the values from the toml file  
    assert test_projections.slr.slr["value"] == 2
    assert test_projections.slr.slr["units"] == "feet"
    assert test_projections.slr.subsidence["value"] == 0
    assert test_projections.slr.subsidence["units"] == "feet"
    assert test_projections.population_growth_existing.value == 20
    assert test_projections.population_growth_new.value == 20
    assert test_projections.economic_growth.value == 20
    assert test_projections.storminess.value == 20
    assert test_projections.precipitation_intensity.value == 20


def test_projection_only_slr():
    from flood_adapt.object_model.projection import Projection

    test_toml = test_database / "charleston" / "input" / "projections" / "all_projections" / "SLR_2ft.toml"
    assert test_toml.is_file()

    test_projections = Projection(test_toml)
    test_projections.load()

    # Assert that all unconfigured risk drivers are set to the default values
    assert test_projections.population_growth_existing.value == 0
    assert test_projections.population_growth_new.value == 0
    assert test_projections.economic_growth.value == 0
    assert test_projections.storminess.value == 0
    assert test_projections.precipitation_intensity.value == 0

    # Assert that the configured risk drivers are set to the values from the toml file
    assert test_projections.slr.slr["value"] == 2
    assert test_projections.slr.slr["units"] == "feet"
    assert test_projections.slr.subsidence["value"] == 0
    assert test_projections.slr.subsidence["units"] == "feet"


def test_projection_only_population_growth_new():
    from flood_adapt.object_model.projection import Projection

    test_toml = test_database / "charleston" / "input" / "projections" / "all_projections" / "pop_growth_new_20.toml"
    assert test_toml.is_file()

    test_projections = Projection(test_toml)
    test_projections.load()

    # Assert that all unconfigured risk drivers are set to the default values
    assert test_projections.slr.slr["value"] == 0
    assert test_projections.slr.slr["units"] == "m"
    assert test_projections.slr.subsidence["value"] == 0
    assert test_projections.slr.subsidence["units"] == "m"
    assert test_projections.population_growth_existing.value == 0
    assert test_projections.economic_growth.value == 0
    assert test_projections.storminess.value == 0
    assert test_projections.precipitation_intensity.value == 0

    # Assert that the configured risk drivers are set to the values from the toml file
    assert test_projections.population_growth_new.value == 20
    assert test_projections.population_growth_new.new_development_elevation["value"] == 1
    assert test_projections.population_growth_new.new_development_elevation["units"] == "feet"
    assert test_projections.population_growth_new.new_development_elevation["reference"] == "floodmap"
    assert test_projections.population_growth_new.new_development_shapefile == "pop_growth_new_20.shp"


def test_projection_missing_key_population_growth_new():
    from flood_adapt.object_model.projection import Projection

    test_toml = test_database / "charleston" / "input" / "projections" / "all_projections" / "pop_growth_new_20_missingKey.toml"
    assert test_toml.is_file()

    test_projections = Projection(test_toml)

    # Assert that the ValueError is thrown because of a missing key in the configuration
    with pytest.raises(ValueError):
        test_projections.load()
