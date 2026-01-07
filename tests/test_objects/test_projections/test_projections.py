from pathlib import Path

from flood_adapt.objects import Projection
from flood_adapt.objects.data_container import GeoDataFrameContainer


def test_projection_save_and_load_file(projection_full: Projection, tmp_path: Path):
    test_projection = projection_full
    file_path = tmp_path / "new_projection.toml"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    test_projection.save(file_path)
    assert file_path.is_file()
    assert test_projection.socio_economic_change.gdf is not None
    assert (
        file_path.parent / f"{test_projection.socio_economic_change.gdf.name}.geojson"
    ).is_file()
    assert test_projection.socio_economic_change.new_development_shapefile is None

    loaded_projection = Projection.load_file(file_path, load_all=True)
    assert loaded_projection == test_projection


def test_save_with_new_development_areas_shapefile_already_exists(
    projection_full: Projection, tmp_path: Path
):
    # Arrange
    test_projection = projection_full
    toml_path = tmp_path / f"{test_projection.name}.toml"
    expected_new_path = (
        toml_path.parent / f"{test_projection.socio_economic_change.gdf.name}.geojson"
    )

    # Act
    test_projection.save(toml_path)
    test_projection.save(toml_path)

    # Assert
    assert toml_path.exists()
    assert expected_new_path.exists()
    assert test_projection.socio_economic_change.new_development_shapefile is None
    assert test_projection.socio_economic_change.gdf is not None


def test_save_additional(
    projection_full: Projection,
    tmp_path: Path,
    gdf_container_polygon: GeoDataFrameContainer,
):
    projection_full.socio_economic_change.gdf = gdf_container_polygon

    output_dir = tmp_path / "output"
    projection_full.save_additional(output_dir)

    expected_path = output_dir / f"{gdf_container_polygon.name}.geojson"
    assert expected_path.exists()


def test_save_additional_with_shapefile(
    projection_full: Projection, tmp_path: Path, shapefile: Path
):
    projection_full.socio_economic_change.gdf = GeoDataFrameContainer(path=shapefile)

    output_dir = tmp_path / "output"
    projection_full.save_additional(output_dir)

    expected_path = output_dir / shapefile.name
    assert expected_path.exists()
