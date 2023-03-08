from pathlib import Path

import pytest

test_database = Path().absolute() / "tests" / "test_database"


def test_all_socio_economic_projections():
    from flood_adapt.object_model.direct_impact.socio_economic_change.socio_economic_change import (
        SocioEconomicChange,
    )

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "projections"
        / "all_projections"
        / "all_projections.toml"
    )
    assert test_toml.is_file()

    test_projections = SocioEconomicChange()
    test_projections.load(test_toml)

    # Assert that the configured risk drivers are set to the values from the toml file
    assert test_projections.population_growth_existing.population_growth_existing == 20
    assert test_projections.population_growth_new.population_growth_new == 20
    assert test_projections.economic_growth.economic_growth == 20


def test_all_physical_projections():
    from flood_adapt.object_model.hazard.physical_projection.physical_projection import (
        PhysicalProjection,
    )

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "projections"
        / "all_projections"
        / "all_projections.toml"
    )
    assert test_toml.is_file()

    test_projections = PhysicalProjection()
    test_projections.load(test_toml)

    assert test_projections.slr.slr["value"] == 2
    assert test_projections.slr.slr["units"] == "feet"
    assert test_projections.slr.subsidence["value"] == 0
    assert test_projections.slr.subsidence["units"] == "feet"
    assert test_projections.storminess.storm_frequency_increase == 20
    assert test_projections.precipitation_intensity.rainfall_increase == 20


def test_phsyical_projection_only_slr():
    from flood_adapt.object_model.hazard.physical_projection.physical_projection import (
        PhysicalProjection,
    )

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "projections"
        / "all_projections"
        / "SLR_2ft.toml"
    )
    assert test_toml.is_file()

    test_projections = PhysicalProjection()
    test_projections.load(test_toml)

    # Assert that all unconfigured risk drivers are set to the default values
    assert test_projections.storminess.storm_frequency_increase == 0
    assert test_projections.precipitation_intensity.rainfall_increase == 0

    # Assert that the configured risk drivers are set to the values from the toml file
    assert test_projections.slr.slr["value"] == 2
    assert test_projections.slr.slr["units"] == "feet"
    assert test_projections.slr.subsidence["value"] == 1
    assert test_projections.slr.subsidence["units"] == "feet"


def test_socio_economic_projection_only_population_growth_new():
    from flood_adapt.object_model.direct_impact.socio_economic_change.socio_economic_change import (
        SocioEconomicChange,
    )

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "projections"
        / "all_projections"
        / "pop_growth_new_20.toml"
    )
    assert test_toml.is_file()

    test_projections = SocioEconomicChange()
    test_projections.load(test_toml)

    # Assert that all unconfigured risk drivers are set to the default values
    assert test_projections.population_growth_existing.population_growth_existing == 0
    assert test_projections.economic_growth.economic_growth == 0

    # Assert that the configured risk drivers are set to the values from the toml file
    assert test_projections.population_growth_new.population_growth_new == 20
    assert (
        test_projections.population_growth_new.new_development_elevation["value"] == 1
    )
    assert (
        test_projections.population_growth_new.new_development_elevation["units"]
        == "feet"
    )
    assert (
        test_projections.population_growth_new.new_development_elevation["reference"]
        == "floodmap"
    )
    assert (
        test_projections.population_growth_new.new_development_shapefile
        == "pop_growth_new_20.shp"
    )


def test_projection_missing_key_population_growth_new():
    from flood_adapt.object_model.direct_impact.socio_economic_change.socio_economic_change import (
        SocioEconomicChange,
    )

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "projections"
        / "all_projections"
        / "pop_growth_new_20_missingKey.toml"
    )
    assert test_toml.is_file()

    test_projections = SocioEconomicChange()

    # Assert that the ValueError is thrown because of a missing key in the configuration
    with pytest.raises(ValueError):
        test_projections.load(test_toml)
