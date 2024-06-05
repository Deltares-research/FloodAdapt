import filecmp
import gc
import logging
import os
import shutil
import tempfile
from pathlib import Path

import pytest

import flood_adapt.config as fa_config
from flood_adapt.api.static import read_database

logging.basicConfig(level=logging.ERROR)
database_root = Path().absolute().parent / "Database"
site_name = "charleston_test"
system_folder = database_root / "system"
database_path = database_root / site_name
snapshot_dir = Path(tempfile.mkdtemp()) / "database_snapshot"
fa_config.parse_user_input(
    database_root=database_root,
    database_name=site_name,
    system_folder=system_folder,
)


def create_snapshot():
    """Create a snapshot of the database directory."""
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(database_path, snapshot_dir)


def restore_db_from_snapshot():
    """Restore the database directory from the snapshot."""
    if not snapshot_dir.exists():
        raise FileNotFoundError(
            "Snapshot path does not exist. Create a snapshot first."
        )

    # Copy deleted/changed files from snapshot to database
    for root, _, files in os.walk(snapshot_dir):
        for file in files:
            snapshot_file = Path(root) / file
            relative_path = snapshot_file.relative_to(snapshot_dir)
            database_file = database_path / relative_path
            if not database_file.exists():
                os.makedirs(os.path.dirname(database_file), exist_ok=True)
                shutil.copy2(snapshot_file, database_file)
            elif not filecmp.cmp(snapshot_file, database_file):
                shutil.copy2(snapshot_file, database_file)

    # Remove created files from database
    for root, _, files in os.walk(database_path):
        for file in files:
            database_file = Path(root) / file
            relative_path = database_file.relative_to(database_path)
            snapshot_file = snapshot_dir / relative_path

            if not snapshot_file.exists():
                os.remove(database_file)

    # Remove empty directories from the database
    for root, dirs, _ in os.walk(database_path, topdown=False):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown():
    """Session-wide setup and teardown for creating the initial snapshot."""
    create_snapshot()

    yield

    restore_db_from_snapshot()
    shutil.rmtree(snapshot_dir)


def make_db_fixture(scope, clean=True):
    """
    Generate a fixture that is used for testing in general.

    All fixtures function as follows:
    At the start of the test session:
        1) Create a snapshot of the database

    At the start of each test:
        2) Restore the database from the snapshot
        3) Initialize database controller
        4) Perform all tests in scope
        5) Restore the database from the snapshot

    Usage
    ----------
    To access the fixture in a test , you need to:
        1) pass the fixture name as an argument to the test function
        2) directly use as a the database object:
            def test_some_test(test_db):
                something = test_db.get_something()
                some_event_toml_path = test_db.input_path / "events" / "some_event" / "some_event.toml"
                assert ...

    Parameters
    ----------
    scope : str
        The scope of the fixture (e.g., "function", "class", "module", "package", "session")
    clean : bool, optional (default is True)
        Whether to clean the database after all tests in the scope have run.
        Clean means cleaning the contents of versioned files, and deleting unversioned files and folders after the tests

    Returns
    -------
    _db_fixture : pytest.fixture
        The database fixture used for testing
    """
    if scope not in ["function", "class", "module", "package", "session"]:
        raise ValueError(f"Invalid fixture scope: {scope}")

    @pytest.fixture(scope=scope)
    def _db_fixture(clean=clean):
        """Fixture for setting up and tearing down the database for each test."""
        if clean:
            restore_db_from_snapshot()

        dbs = read_database(database_root, site_name)

        # Yield the database controller for the test
        yield dbs

        # Close dangling connections
        gc.collect()

        if clean:
            restore_db_from_snapshot()

    return _db_fixture


# NOTE: to access the contents the fixtures in the test functions,
# the fixture name needs to be passed as an argument to the test function.
# the first line of your test needs to initialize the yielded variables:
# 'dbs = test_db_...'


test_db = make_db_fixture("function")
test_db_class = make_db_fixture("class")
test_db_module = make_db_fixture("module")
test_db_package = make_db_fixture("package")
test_db_session = make_db_fixture("session")

# NOTE: while developing, it is useful to have a fixture that does not clean the database to debug
# Should not be used in tests that are completed and pushed to the repository
test_db_no_clean = make_db_fixture("function", clean=False)
test_db_class_no_clean = make_db_fixture("class", clean=False)
test_db_module_no_clean = make_db_fixture("module", clean=False)
test_db_package_no_clean = make_db_fixture("package", clean=False)
test_db_session_no_clean = make_db_fixture("session", clean=False)
