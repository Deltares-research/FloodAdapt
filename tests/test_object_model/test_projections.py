from pathlib import Path

import pytest
import tomli

from flood_adapt import unit_system as us
from flood_adapt.object_model.interface.projections import (
    PhysicalProjectionModel,
    Projection,
    SocioEconomicChangeModel,
)


@pytest.fixture()
def test_projections(test_db) -> dict[str, Projection]:
    test_tomls = [
        test_db.input_path / "projections" / "all_projections" / "all_projections.toml",
        test_db.input_path / "projections" / "SLR_2ft" / "SLR_2ft.toml",
    ]
    test_projections = {
        toml_file.name: Projection.load_file(toml_file) for toml_file in test_tomls
    }
    yield test_projections


@pytest.fixture()
def test_dict(test_data_dir):
    config_values = {
        "name": "new_projection",
        "description": "new_unsaved_projection",
        "physical_projection": {
            "sea_level_rise": {"value": 2, "units": "feet"},
            "subsidence": {"value": 0, "units": "feet"},
            "rainfall_multiplier": 20,
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
            "new_development_shapefile": str(Path(test_data_dir, "new_areas.geojson")),
        },
    }
    yield config_values


@pytest.fixture
def test_projection(test_data_dir):
    return Projection(
        name="test_projection",
        description="test description",
        physical_projection=PhysicalProjectionModel(),
        socio_economic_change=SocioEconomicChangeModel(
            new_development_shapefile=str(
                test_data_dir / "shapefiles" / "pop_growth_new_20.shp"
            )
        ),
    )


def test_projection_load_dict(test_dict):
    projection = Projection(**test_dict)
    for key, value in test_dict.items():
        if not isinstance(value, dict):
            assert getattr(projection, key) == value


def test_projection_save_createsFile(test_db, test_dict):
    test_projection = Projection(**test_dict)
    file_path = (
        test_db.input_path / "projections" / "new_projection" / "new_projection.toml"
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    test_projection.save(file_path)
    assert file_path.is_file()


def test_projection_loadFile_checkAllAttrs(test_db, test_dict):
    test_projection = Projection(**test_dict)
    file_path = (
        test_db.input_path / "projections" / "new_projection" / "new_projection.toml"
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    test_projection.save(file_path)

    test_projection = Projection.load_file(file_path)
    for key, value in test_dict.items():
        if not isinstance(value, dict):
            assert getattr(test_projection, key) == value


def test_projection_loadFile_validFiles(test_projections: dict[str, Projection]):
    test_projection = test_projections["all_projections.toml"]
    # Assert that the configured risk drivers are set to the values from the toml file
    assert isinstance(test_projection.physical_projection, PhysicalProjectionModel)
    assert isinstance(test_projection.socio_economic_change, SocioEconomicChangeModel)


def test_projection_loadFile_invalidFile_raiseFileNotFoundError():
    with pytest.raises(FileNotFoundError):
        Projection.load_file(Path("invalid_file.toml"))


def test_projection_getPhysicalProjection_readValidAttrs(
    test_projections: dict[str, Projection],
):
    test_projection = test_projections["all_projections.toml"]

    assert test_projection.name == "all_projections"
    physical_attrs = test_projection.physical_projection

    assert physical_attrs.sea_level_rise.value == 2
    assert physical_attrs.sea_level_rise.units == us.UnitTypesLength.feet

    assert physical_attrs.subsidence.value == 0
    assert physical_attrs.subsidence.units == us.UnitTypesLength.meters

    assert physical_attrs.rainfall_multiplier == 2
    assert physical_attrs.storm_frequency_increase == 2


def test_projection_getSocioEconomicChange_readValidAttrs(
    test_projections: dict[str, Projection],
):
    test_projection = test_projections["all_projections.toml"]

    assert test_projection.name == "all_projections"

    socio_economic_attrs = test_projection.socio_economic_change

    assert socio_economic_attrs.economic_growth == 20
    assert socio_economic_attrs.population_growth_new == 20
    assert socio_economic_attrs.population_growth_existing == 20
    assert socio_economic_attrs.new_development_elevation.value == 1
    assert socio_economic_attrs.new_development_elevation.units == "feet"
    assert socio_economic_attrs.new_development_elevation.type == "floodmap"
    assert socio_economic_attrs.new_development_shapefile == "new_areas.geojson"


def test_projection_getSocioEconomicChange_readInvalidAttrs_raiseAttributeError(
    test_projections: dict[str, Projection],
):
    test_projection = test_projections["all_projections.toml"]
    with pytest.raises(AttributeError):
        test_projection.socio_economic_change.sea_level_rise.value


def test_projection_getPhysicalProjection_readInvalidAttrs_raiseAttributeError(
    test_projections,
):
    test_projection = test_projections["all_projections.toml"]
    with pytest.raises(AttributeError):
        test_projection.physical_projection.economic_growth


def test_projection_only_slr(test_projections: dict[str, Projection]):
    test_projection = test_projections["SLR_2ft.toml"]

    # Assert that all unconfigured risk drivers are set to the default values
    assert test_projection.physical_projection.storm_frequency_increase == 0

    # Assert that the configured risk drivers are set to the values from the toml file
    assert test_projection.name == "SLR_2ft"
    assert test_projection.physical_projection.sea_level_rise.value == 2
    assert test_projection.physical_projection.sea_level_rise.units == "feet"


def test_save_with_new_development_areas_also_saves_shapefile(
    test_projection, tmp_path
):
    # Arrange
    toml_path = tmp_path / "test_file.toml"
    expected_new_path = (
        toml_path.parent
        / Path(test_projection.socio_economic_change.new_development_shapefile).name
    )

    # Act
    test_projection.save(toml_path)

    # Assert
    assert toml_path.exists()
    assert expected_new_path.exists()

    with open(toml_path, "rb") as f:
        data = tomli.load(f)
    assert (
        data["socio_economic_change"]["new_development_shapefile"]
        == expected_new_path.name
    )


def test_save_with_new_development_areas_shapefile_already_exists(
    test_projection, test_db
):
    # Arrange
    toml_path = (
        test_db.input_path
        / "projections"
        / test_projection.name
        / f"{test_projection.name}.toml"
    )
    expected_new_path = (
        toml_path.parent
        / Path(
            test_projection.socio_economic_change.new_development_shapefile  # "pop_growth_new_20.shp"
        ).name
    )

    # Act
    test_projection.save(toml_path)
    test_projection.save(toml_path)

    # Assert
    assert toml_path.exists()
    assert expected_new_path.exists()
    assert (
        test_projection.socio_economic_change.new_development_shapefile
        == expected_new_path.name
    )
