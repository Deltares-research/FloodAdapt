from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_projection_slr():
    from flood_adapt.object_model.projection import Projection

    test_toml = test_database / "charleston" / "input" / "projections" / "all_projections" / "all_projections.toml"
    assert test_toml.is_file()

    test_projections = Projection(test_toml)
    test_projections.load()

    assert test_projections.slr.slr_value == 2
    assert test_projections.slr.slr_unit == "feet"
    assert test_projections.slr.subsidence_value == 0
    assert test_projections.slr.subsidence_unit == "feet"
