import filecmp
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from flood_adapt import SRC_DIR
from flood_adapt.api.static import read_database
from flood_adapt.config import Settings
from flood_adapt.log import FloodAdaptLogging

settings = Settings(
    database_root=SRC_DIR.parents[1] / "Database",
    database_name="charleston_test",
    # leave system_folder empty to use the envvar or default system folder
)

session_tmp_dir = Path(tempfile.mkdtemp())
snapshot_dir = session_tmp_dir / "database_snapshot"
logs_dir = Path(__file__).absolute().parent / "logs"

#### DEBUGGING ####
# To disable resetting the database after tests: set clean=false
# Only for debugging purposes, should always be set to true when pushing to github
clean = True


def create_snapshot():
    """Create a snapshot of the database directory."""
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(settings.database_path, snapshot_dir)


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
            database_file = settings.database_path / relative_path
            if not database_file.exists():
                os.makedirs(os.path.dirname(database_file), exist_ok=True)
                shutil.copy2(snapshot_file, database_file)
            elif not filecmp.cmp(snapshot_file, database_file):
                shutil.copy2(snapshot_file, database_file)

    # Remove created files from database
    for root, _, files in os.walk(settings.database_path):
        for file in files:
            database_file = Path(root) / file
            relative_path = database_file.relative_to(settings.database_path)
            snapshot_file = snapshot_dir / relative_path

            if not snapshot_file.exists():
                os.remove(database_file)

    # Remove empty directories from the database
    for root, dirs, _ in os.walk(settings.database_path, topdown=False):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown():
    """Session-wide setup and teardown for creating the initial snapshot."""
    log_path = logs_dir / f"test_run_{datetime.now().strftime('%m-%d_%Hh-%Mm')}.log"
    FloodAdaptLogging(
        file_path=log_path,
        loglevel_console=logging.DEBUG,
        loglevel_root=logging.DEBUG,
        loglevel_files=logging.DEBUG,
    )
    create_snapshot()

    yield

    if clean:
        restore_db_from_snapshot()
    shutil.rmtree(snapshot_dir, ignore_errors=True)


def make_db_fixture(scope):
    """
    Generate a fixture that is used for testing in general.

    Parameters
    ----------
    scope : str
        The scope of the fixture (e.g., "function", "class", "module", "package", "session")

    Returns
    -------
    _db_fixture : pytest.fixture
        The database fixture used for testing
    """
    if scope not in ["function", "class", "module", "package", "session"]:
        raise ValueError(f"Invalid fixture scope: {scope}")

    @pytest.fixture(scope=scope)
    def _db_fixture():
        """
        Fixture for setting up and tearing down the database once per scope.

        Every test session:
            1) Create a snapshot of the database
            2) Run all tests
            3) Restore the database from the snapshot

        Every scope:
            1) Initialize database controller
            2) Perform all tests in scope
            3) Restore the database from the snapshot

        Usage
        ----------
        To access the fixture in a test , you need to:
            1) pass the fixture name as an argument to the test function
            2) directly use as a the database object:
                def test_some_test(test_db):
                    something = test_db.get_something()
                    some_event_toml_path = test_db.input_path / "events" / "some_event" / "some_event.toml"
                    assert ...
        """
        # Setup
        dbs = read_database(settings.database_root, settings.database_name)

        # Perform tests
        yield dbs

        # Teardown
        dbs.shutdown()
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


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    test_name = item.name
    logger = FloodAdaptLogging.getLogger()
    logger.info(f"\nStarting test: {test_name}\n")
