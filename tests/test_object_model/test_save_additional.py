import pytest
import tomli

from flood_adapt.object_model.interface.projections import (
    PhysicalProjectionModel,
    ProjectionModel,
    SocioEconomicChangeModel,
)
from flood_adapt.object_model.projection import Projection

# to_test = [
#     events: historical hurricane / synthetic / offshore / nearshore
# ]
# def save(self, filepath: Union[str, os.PathLike], additional_files: bool = False):
#     """Save Projection to a toml file."""
#     if additional_files:
#         if self.attrs.socio_economic_change.new_development_shapefile is None:
#             raise ValueError("The shapefile for the new development is not set.")
#         new_path = import_external_file(
#             self.attrs.socio_economic_change.new_development_shapefile,
#             Path(filepath).parent,
#         )
#         # Update the shapefile path in the object so it is saved in the toml file as well
#         self.attrs.socio_economic_change.new_development_shapefile = str(new_path)

#     with open(filepath, "wb") as f:
#         tomli_w.dump(self.attrs.dict(exclude_none=True), f)


@pytest.fixture
def dummy_projection():
    attrs = ProjectionModel(
        name="test_projection",
        description="test description",
        physical_projection=PhysicalProjectionModel(),
        socio_economic_change=SocioEconomicChangeModel(),
    )
    return Projection.load_dict(attrs)


@pytest.fixture
def dummy_shapefile(tmp_path, test_data_dir):
    shpfile = test_data_dir / "shapefiles" / "pop_growth_new_20.shp"
    assert shpfile.exists()
    return shpfile


def test_save_with_additional_files(dummy_projection, dummy_shapefile, tmp_path):
    # Arrange
    dummy_projection.attrs.socio_economic_change.new_development_shapefile = str(
        dummy_shapefile
    )
    toml_path = tmp_path / "test_file.toml"

    # Act
    dummy_projection.save(toml_path, additional_files=True)

    # Assert
    expected_new_path = toml_path.parent / dummy_shapefile.name
    assert toml_path.exists()
    assert expected_new_path.exists()

    with open(toml_path, "rb") as f:
        data = tomli.load(f)
    assert data["socio_economic_change"]["new_development_shapefile"] == str(
        expected_new_path
    )


# def test_save_without_additional_files(object_model, object_model_data, tmp_path):
#     # Arrange
#     filepath = tmp_path / "test_file.toml"

#     # Act
#     object_model.save(filepath, additional_files=False)

#     # Assert
#     assert filepath.exists()
#     with open(filepath, "rb") as f:
#         data = tomli_w.load(f)
#     assert "new_development_shapefile" not in data["socio_economic_change"]

# def test_save_raises_value_error_when_shapefile_not_set(object_model, object_model_data, tmp_path):
#     # Arrange
#     filepath = tmp_path / "test_file.toml"

#     # Act & Assert
#     with pytest.raises(ValueError, match="The shapefile for the new development is not set."):
#         object_model.save(filepath, additional_files=True)


# def test_save_additional(object_model, object_model_data, ):
#     # Arrange
#     hazard_measure = HazardMeasureModel(
#         name="test_hazard_measure",
#         description="test description",
#         type=HazardType.floodwall,
#         selection_type=SelectionType.polyline,
#     )

#     # Assert
#     assert hazard_measure.name == "test_hazard_measure"
#     assert hazard_measure.description == "test description"
#     assert hazard_measure.type == "floodwall"
#     assert hazard_measure.polygon_file is None
#     assert hazard_measure.selection_type == "aggregation_area"
