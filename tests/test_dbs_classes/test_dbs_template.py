import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from flood_adapt.dbs_classes.dbs_measure import DbsMeasure


# Fixture that makes a copy of the measure file to avoid modifying the original
@pytest.fixture
def copy_measure_file(test_db):

    # Make a copy of the file and rename to avoid modifying the original
    measures_path = test_db.input_path.joinpath("measures")
    shutil.copytree(measures_path.joinpath("raise_property_polygon"), measures_path.joinpath("raise_property_polygon_copy"))
    os.rename(measures_path.joinpath("raise_property_polygon_copy").joinpath("raise_property_polygon.toml"), measures_path.joinpath("raise_property_polygon_copy").joinpath("raise_property_polygon_copy.toml"))
    if measures_path.joinpath("raise_property_polygon").joinpath("raise_property_polygon.geojson").exists():
        os.rename(measures_path.joinpath("raise_property_polygon_copy").joinpath("raise_property_polygon.geojson"), measures_path.joinpath("raise_property_polygon_copy").joinpath("raise_property_polygon_copy.geojson"))
    
    # Change the name in the copy
    measure_file = measures_path.joinpath("raise_property_polygon_copy").joinpath("raise_property_polygon_copy.toml")
    with open(measure_file, "r") as file:
        data = file.read()
    data = data.replace("raise_property_polygon", "raise_property_polygon_copy")
    with open(measure_file, "w") as file:
        file.write(data)

    # Yield the test_db
    yield test_db

    # Remove the copy
    shutil.rmtree(measures_path.joinpath("raise_property_polygon_copy"))


class TestDbsMeasure:
    def test_getObject_fileFound(self, copy_measure_file):
        # Arrange
        # Act
        measure = copy_measure_file.measures.get("raise_property_polygon")

        # Assert
        assert measure.attrs.name == "raise_property_polygon"
        assert measure.attrs.description == "raise_property_polygon"
        assert measure.attrs.type == "elevate_properties"
        assert measure.attrs.polygon_file == "raise_property_polygon.geojson"
        assert measure.attrs.selection_type == "polygon"

    def test_getObject_fileNotFound(self, test_db):
        # Arrange
        # Act / Assert
        with pytest.raises(FileNotFoundError):
            test_db.measures.get("not_found")
    
    def test_listObjects(self, test_db):
        # Arrange
        # Act
        measures = test_db.measures.list_objects()

        # Assert
        # Not going to test the actual values, just that the keys are present
        # Otherwise, we would be testing the content of the database
        assert 'path'in measures
        assert 'name' in measures
        assert 'last_modification_date' in measures
        assert 'description' in measures
        assert 'objects' in measures
        assert 'geometry' in measures

    def test_setLock(self, copy_measure_file):
        # Arrange
        # Make a copy of the file to avoid modifying the original
        measures_path = copy_measure_file.input_path.joinpath("measures")

        # Act
        copy_measure_file.measures.set_lock(name = "raise_property_polygon_copy")

        # Assert
        assert measures_path.joinpath("raise_property_polygon_copy").joinpath("lock").exists()
    

