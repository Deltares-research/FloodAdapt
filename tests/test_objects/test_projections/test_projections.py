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


def test_save_additional_with_path(
    projection_full: Projection, tmp_path: Path, gdf_polygon: gpd.GeoDataFrame
):
    path = tmp_path / "projection.geojson"
    gdf_polygon.to_file(path)

    projection_full.socio_economic_change.gdf = path

    output_dir = tmp_path / "output"
    projection_full.save_additional(output_dir)

    expected_path = output_dir / path.name
    assert expected_path.exists()


def test_save_additional_with_gdf(
    projection_full: Projection, tmp_path: Path, gdf_polygon: gpd.GeoDataFrame
):
    projection_full.socio_economic_change.gdf = gdf_polygon

    output_dir = tmp_path / "output"
    projection_full.save_additional(output_dir)

    expected_path = output_dir / "new_developments.geojson"
    assert expected_path.exists()


def test_save_additional_with_shapefile(
    projection_full: Projection, tmp_path: Path, shapefile: Path
):
    projection_full.socio_economic_change.gdf = shapefile

    output_dir = tmp_path / "output"
    projection_full.save_additional(output_dir)

    expected_path = output_dir / shapefile.with_suffix(".geojson").name
    assert expected_path.exists()


def test_save_additional_with_str(
    projection_full: Projection, tmp_path: Path, gdf_polygon: gpd.GeoDataFrame
):
    path = tmp_path / "projection.geojson"
    gdf_polygon.to_file(path)

    projection_full.socio_economic_change.gdf = path.as_posix()

    output_dir = tmp_path / "output"
    projection_full.save_additional(output_dir)

    expected_path = output_dir / path.name
    assert expected_path.exists()
