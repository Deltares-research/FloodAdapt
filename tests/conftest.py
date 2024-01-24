import os
import shutil
from pathlib import Path

import pytest

from flood_adapt.api.startup import read_database


def get_file_structure(path: str) -> list:
    """Get the file structure of a directory and store it in a list"""
    file_structure = []

    # Walk through the directory
    for root, dirs, files in os.walk(path):
        relative_path = os.path.relpath(root, path)
        file_structure.append(relative_path)
    return file_structure


def remove_files_and_folders(path, file_structure):
    """Remove all files and folders that are not present in the file structure"""

    # Walk through the directory
    for root, dirs, files in os.walk(path):
        relative_path = os.path.relpath(root, path)
        # If the relative path is not in the file structure, remove it
        if relative_path not in file_structure:
            try:
                shutil.rmtree(root)
            except PermissionError:
                print(f"PermissionError: {root}")


@pytest.fixture
def test_db():
    """This fixture is used for testing in general to setup the test database,
    perform the test, and clean the database after each test.
    It is used by other fixtures to set up and clean the test_database"""

    # Get the database file structure before the test
    rootPath = Path().absolute() / "tests" / "test_database"  # the path to the database
    site_name = "Charleston"  # the name of the test site

    database_path = str(rootPath.joinpath(site_name))
    file_structure = get_file_structure(database_path)
    dbs = read_database(rootPath, site_name)

    # NOTE: to access the contents of this function in the test,
    #  the first line of your test needs to initialize the yielded variables:
    #   'dbs, folders = test_db'

    # Run the test
    yield dbs
    # Remove all files and folders that were not present before the test
    remove_files_and_folders(database_path, file_structure)
