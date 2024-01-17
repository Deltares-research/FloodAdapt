import os
import shutil
import subprocess
from pathlib import Path

import pytest
import tomli

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


@pytest.fixture(scope="session")  # This fixture is only run once per session
def updatedSVN():
    database_root = tomli.load("database.toml")["database_root"]
    batch_file_path = Path().absolute() / "tests" / "updateSVN.bat"
    subprocess.run([str(batch_file_path), database_root], shell=True)
    print("Updated SVN\n\n\n")
    return database_root


@pytest.fixture
def test_db(updatedSVN):
    """This fixture is used for testing in general to setup the test database,
    perform the test, and clean the database after each test.
    It is used by other fixtures to set up and clean the test_database"""

    # Get the database file structure before the test
    database_root = updatedSVN
    site_name = "charleston_test"  # the name of the test site

    database_path = database_root / site_name
    file_structure = get_file_structure(database_path)
    dbs = read_database(database_path, site_name)

    # NOTE: to access the contents of this function in the test,
    #  the first line of your test needs to initialize the yielded variables:
    #   'dbs = test_db'

    # Run the test
    yield dbs
    # Remove all files and folders that were not present before the test
    remove_files_and_folders(database_path, file_structure)
