import os
import shutil
import subprocess
from pathlib import Path

import pytest

from flood_adapt.api.startup import read_database
from flood_adapt.config import parse_config, set_site_name


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


@pytest.fixture(
    autouse=True, scope="session"
)  # This fixture is only run once per session
def updatedSVN():
    config_path = Path(__file__).parent.parent / "config.toml"
    parse_config(
        config_path
    )  # Set the database root, system folder, based on the config file
    set_site_name("charleston_test")  # set the site name to the test database
    updateSVN_file_path = Path(__file__).parent / "updateSVN.py"
    subprocess.run(
        [str(updateSVN_file_path), os.environ["DATABASE_ROOT"]],
        shell=True,
        capture_output=True,
    )


def make_db_fixture(scope):
    """
    This fixture is used for testing in general.
    It functions as follows:
        1) Setup database controller
        2) Perform all tests in scope
        3) Clean the database
    Scope can be one of the following: "function", "class", "module", "package", "session"
    """
    if scope not in ["function", "class", "module", "package", "session"]:
        raise ValueError(f"Invalid fixture scope: {scope}")

    @pytest.fixture(scope=scope)
    def _db_fixture():
        database_path = os.environ["DATABASE_ROOT"]
        site_name = os.environ["SITE_NAME"]
        file_structure = get_file_structure(database_path)
        dbs = read_database(database_path, site_name)
        yield dbs
        remove_files_and_folders(database_path, file_structure)

    return _db_fixture


# NOTE: to access the contents the fixtures in the test functions,
# the fixture name needs to be passed as an argument to the test function.
# the first line of your test needs to initialize the yielded variables:
# 'dbs = _db_fixture'
test_db = make_db_fixture("function")
test_db_class = make_db_fixture("class")
test_db_module = make_db_fixture("module")
test_db_package = make_db_fixture("package")
test_db_session = make_db_fixture("session")
