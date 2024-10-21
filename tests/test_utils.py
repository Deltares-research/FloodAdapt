from unittest import mock

import pytest

from flood_adapt.object_model.utils import save_file_to_database


@pytest.fixture
def mock_settings(tmp_path):
    with mock.patch("flood_adapt.dbs_classes.path_builder.Settings") as MockSettings:
        instance = MockSettings.return_value
        instance.database_path = tmp_path / "Database" / "test"
        yield instance


class TestSaveFileToDatabase:
    def test_save_absfile_success(self, mock_settings, tmp_path):
        # Arrange
        src_file = tmp_path / "source.txt"
        src_file.write_text("test content")

        dst_file = mock_settings.database_path / "subdir" / "source.txt"

        # Act
        result = save_file_to_database(src_file, dst_file.parent)

        # Assert
        assert dst_file.exists()
        assert result == dst_file

    def test_overwrite_existing_dst_file_with_file(self, mock_settings, tmp_path):
        # Arrange
        src_file = tmp_path / "source.txt"
        src_file.write_text("new content")

        dst_file = mock_settings.database_path / "subdir" / "source.txt"
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        dst_file.write_text("old content")

        # Act
        result = save_file_to_database(src_file, dst_file.parent)

        # Assert
        assert result == dst_file
        assert dst_file.read_text() == "new content"

    def test_non_existent_file_raise_file_not_found(self, mock_settings, tmp_path):
        # Arrange
        not_exists_src_file = tmp_path / "source.txt"
        dst_file = mock_settings.database_path / "subdir" / "source.txt"

        # Act & Assert
        with pytest.raises(FileNotFoundError) as excinfo:
            save_file_to_database(not_exists_src_file, dst_file.parent)
            assert (
                f"Failed to save external file to the database {not_exists_src_file} as it does not exist."
                in str(excinfo.value)
            )
