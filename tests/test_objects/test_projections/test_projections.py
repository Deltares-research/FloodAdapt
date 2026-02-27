from pathlib import Path

import pytest

from flood_adapt.objects.projections.projections import (
    PhysicalProjection,
    Projection,
    SocioEconomicChange,
)


@pytest.fixture
def test_projection(test_data_dir):
    return Projection(
        name="test_projection",
        description="test description",
        physical_projection=PhysicalProjection(),
        socio_economic_change=SocioEconomicChange(
            new_development_shapefile=str(
                test_data_dir / "shapefiles" / "pop_growth_new_20.shp"
            )
        ),
    )


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

    loaded = Projection.load_file(toml_path)
    assert loaded == test_projection
    assert (
        loaded.socio_economic_change.new_development_shapefile
        == expected_new_path.as_posix()
    )
