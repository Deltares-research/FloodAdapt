from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'


def test_all_projections():
    from flood_adapt.object_model.projection import Projection

    test_toml = test_database / "charleston" / "input" / "projections" / "all_projections" / "all_projections.toml"
    assert test_toml.is_file()

    test_projections = Projection(test_toml)
    test_projections.load()

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

    assert test_projections.slr.slr["value"] == 2
    assert test_projections.slr.slr["units"] == "feet"
    assert test_projections.slr.subsidence["value"] == 0
    assert test_projections.slr.subsidence["units"] == "feet"

    assert test_projections.population_growth_existing.value == 0

    assert test_projections.population_growth_new.value == 0

    assert test_projections.economic_growth.value == 0

    assert test_projections.storminess.value == 0

    assert test_projections.precipitation_intensity.value == 0
