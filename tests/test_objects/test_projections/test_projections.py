from pathlib import Path

import geopandas as gpd

from flood_adapt.objects import Projection


def test_projection_save_and_load_file(projection_full: Projection, tmp_path: Path):
    test_projection = projection_full
    file_path = tmp_path / "new_projection.toml"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    test_projection.save(file_path)
    assert file_path.is_file()

    assert (file_path.parent / "new_developments.geojson").is_file()
    assert test_projection.socio_economic_change.new_development_shapefile is None

    loaded_projection = Projection.load_file(file_path)
    assert loaded_projection == test_projection


def test_save_with_new_development_areas_shapefile_already_exists(
    projection_full: Projection, tmp_path: Path
):
    # Arrange
    test_projection = projection_full
    toml_path = tmp_path / f"{test_projection.name}.toml"
    expected_new_path = toml_path.parent / "new_developments.geojson"

    # Act
    test_projection.save(toml_path)
    test_projection.save(toml_path)

    # Assert
    assert toml_path.exists()
    assert expected_new_path.exists()
    assert test_projection.socio_economic_change.new_development_shapefile is None
    assert isinstance(test_projection.socio_economic_change.gdf, gpd.GeoDataFrame)
