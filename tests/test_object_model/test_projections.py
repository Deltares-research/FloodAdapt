from pathlib import Path

import pytest

from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
)
from flood_adapt.object_model.projection import Projection


@pytest.fixture()
def test_projections(test_db):
    test_tomls = [
        test_db.input_path / "projections" / "all_projections" / "all_projections.toml",
        test_db.input_path / "projections" / "SLR_2ft" / "SLR_2ft.toml",
    ]
    test_projections = {
        toml_file.name: Projection.load_file(toml_file) for toml_file in test_tomls
    }
    yield test_projections


@pytest.fixture()
def test_dict():
    config_values = {
        "name": "new_projection",
        "description": "new_unsaved_projection",
        "physical_projection": {
            "sea_level_rise": {"value": 2, "units": "feet"},
            "subsidence": {"value": 0, "units": "feet"},
            "rainfall_increase": 20,
            "storm_frequency_increase": 20,
        },
        "socio_economic_change": {
            "economic_growth": 20,
            "population_growth_new": 20,
            "population_growth_existing": 20,
            "new_development_elevation": {
                "value": 1,
                "units": "feet",
                "type": "floodmap",
            },
            "new_development_shapefile": "new_areas.geojson",
        },
    }
    yield config_values


def test_projection_load_dict(test_dict):
    projection = Projection.load_dict(test_dict)
    for key, value in test_dict.items():
        if not isinstance(value, dict):
            assert getattr(projection.attrs, key) == value


def test_projection_save_createsFile(test_db, test_dict):
    test_projection = Projection.load_dict(test_dict)
    file_path = (
        test_db.input_path / "projections" / "new_projection" / "new_projection.toml"
    )
    test_projection.save(file_path)
    assert file_path.is_file()


def test_projection_loadFile_checkAllAttrs(test_db, test_dict):
    test_projection = Projection.load_dict(test_dict)
    file_path = (
        test_db.input_path / "projections" / "new_projection" / "new_projection.toml"
    )
    test_projection.save(file_path)

    test_projection = Projection.load_file(file_path)
    for key, value in test_dict.items():
        if not isinstance(value, dict):
            assert getattr(test_projection.attrs, key) == value


def test_projection_loadFile_validFiles(test_projections):
    test_projection = test_projections["all_projections.toml"]
    # Assert that the configured risk drivers are set to the values from the toml file
    assert isinstance(test_projection.get_physical_projection(), PhysicalProjection)
    assert isinstance(test_projection.get_socio_economic_change(), SocioEconomicChange)


def test_projection_loadFile_invalidFile_raiseFileNotFoundError():
    with pytest.raises(FileNotFoundError):
        Projection.load_file(Path("invalid_file.toml"))


def test_projection_getPhysicalProjection_readValidAttrs(test_projections):
    test_projection = test_projections["all_projections.toml"]

    assert test_projection.attrs.name == "all_projections"
    assert test_projection.attrs.description == "all_projections"
    physical_attrs = test_projection.get_physical_projection()

    assert physical_attrs.attrs.sea_level_rise.value == 2
    assert physical_attrs.attrs.sea_level_rise.units == "feet"

    assert physical_attrs.attrs.subsidence.value == 0
    assert physical_attrs.attrs.subsidence.units == "feet"

    assert physical_attrs.attrs.rainfall_increase == 20
    assert physical_attrs.attrs.storm_frequency_increase == 20


def test_projection_getSocioEconomicChange_readValidAttrs(test_projections):
    test_projection = test_projections["all_projections.toml"]

    assert test_projection.attrs.name == "all_projections"
    assert test_projection.attrs.description == "all_projections"

    socio_economic_attrs = test_projection.get_socio_economic_change()

    assert socio_economic_attrs.attrs.economic_growth == 20
    assert socio_economic_attrs.attrs.population_growth_new == 20
    assert socio_economic_attrs.attrs.population_growth_existing == 20
    assert socio_economic_attrs.attrs.new_development_elevation.value == 1
    assert socio_economic_attrs.attrs.new_development_elevation.units == "feet"
    assert socio_economic_attrs.attrs.new_development_elevation.type == "floodmap"
    assert socio_economic_attrs.attrs.new_development_shapefile == "new_areas.geojson"


def test_projection_getSocioEconomicChange_readInvalidAttrs_raiseAttributeError(
    test_projections,
):
    test_projection = test_projections["all_projections.toml"]
    with pytest.raises(AttributeError):
        test_projection.get_socio_economic_change().attrs.sea_level_rise.value


def test_projection_getPhysicalProjection_readInvalidAttrs_raiseAttributeError(
    test_projections,
):
    test_projection = test_projections["all_projections.toml"]
    with pytest.raises(AttributeError):
        test_projection.get_physical_projection().attrs.economic_growth


def test_projection_only_slr(test_projections):
    test_projection = test_projections["SLR_2ft.toml"]

    # Assert that all unconfigured risk drivers are set to the default values
    assert test_projection.get_physical_projection().attrs.storm_frequency_increase == 0

    # Assert that the configured risk drivers are set to the values from the toml file
    assert test_projection.attrs.name == "SLR_2ft"
    assert test_projection.attrs.description == "SLR_2ft"
    assert test_projection.get_physical_projection().attrs.sea_level_rise.value == 2
    assert (
        test_projection.get_physical_projection().attrs.sea_level_rise.units == "feet"
    )
