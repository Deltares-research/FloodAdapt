import filecmp
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

import flood_adapt.config as fa_config
from flood_adapt.api.static import read_database
from flood_adapt.log import FloodAdaptLogging

PROJECT_ROOT = Path(__file__).absolute().parent.parent.parent
DATABASE_ROOT = PROJECT_ROOT / "Database"
SITE_NAME = "charleston_test"
SYSTEM_FOLDER = DATABASE_ROOT / "system"
DATABASE_PATH = DATABASE_ROOT / SITE_NAME

SESSION_TMP_DIR = Path(tempfile.mkdtemp())
SNAPSHOT_DIR = SESSION_TMP_DIR / "database_snapshot"
LOGS_DIR = Path(__file__).absolute().parent / "logs"

fa_config.parse_user_input(
    database_root=DATABASE_ROOT,
    database_name=SITE_NAME,
    system_folder=SYSTEM_FOLDER,
)

#### DEBUGGING ####
# To disable resetting the database after tests: set CLEAN = False
# Only for debugging purposes, should always be set to true when pushing to github
CLEAN = True


def create_snapshot():
    """Create a snapshot of the database directory."""
    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)
    shutil.copytree(DATABASE_PATH, SNAPSHOT_DIR)


def restore_db_from_snapshot():
    """Restore the database directory from the snapshot."""
    if not SNAPSHOT_DIR.exists():
        raise FileNotFoundError(
            "Snapshot path does not exist. Create a snapshot first."
        )

    # Copy deleted/changed files from snapshot to database
    for root, _, files in os.walk(SNAPSHOT_DIR):
        for file in files:
            snapshot_file = Path(root) / file
            relative_path = snapshot_file.relative_to(SNAPSHOT_DIR)
            database_file = DATABASE_PATH / relative_path
            if not database_file.exists():
                os.makedirs(os.path.dirname(database_file), exist_ok=True)
                shutil.copy2(snapshot_file, database_file)
            elif not filecmp.cmp(snapshot_file, database_file):
                shutil.copy2(snapshot_file, database_file)

    # Remove created files from database
    for root, _, files in os.walk(DATABASE_PATH):
        for file in files:
            database_file = Path(root) / file
            relative_path = database_file.relative_to(DATABASE_PATH)
            snapshot_file = SNAPSHOT_DIR / relative_path

            if not snapshot_file.exists():
                os.remove(database_file)

    # Remove empty directories from the database
    for root, dirs, _ in os.walk(DATABASE_PATH, topdown=False):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown():
    """Session-wide setup and teardown for creating the initial snapshot."""
    log_path = LOGS_DIR / f"test_run_{datetime.now().strftime('%m-%d_%Hh-%Mm')}.log"
    FloodAdaptLogging(
        file_path=log_path,
        loglevel_console=logging.DEBUG,
        loglevel_root=logging.DEBUG,
        loglevel_files=logging.DEBUG,
    )
    create_snapshot()

    yield

    if CLEAN:
        restore_db_from_snapshot()
    shutil.rmtree(SNAPSHOT_DIR)


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
        dbs = read_database(DATABASE_ROOT, SITE_NAME)

        # Perform tests
        yield dbs

        # Teardown
        dbs.reset()
        if CLEAN:
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
