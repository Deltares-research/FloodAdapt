import filecmp
import logging
import os
import platform
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

from flood_adapt import __path__
from flood_adapt.adapter.docker import (
    FIAT_CONTAINER,
    HAS_DOCKER,
    SFINCS_CONTAINER,
    DockerContainer,
)
from flood_adapt.config.config import Settings
from flood_adapt.flood_adapt import FloodAdapt
from flood_adapt.misc.log import FloodAdaptLogging
from tests.data.create_test_input import update_database_input
from tests.data.create_test_static import update_database_static
from tests.fixtures import dummy_1d_timeseries_df as dummy_1d_timeseries_df  # noqa
from tests.fixtures import dummy_2d_timeseries_df as dummy_2d_timeseries_df
from tests.fixtures import dummy_buyout_measure as dummy_buyout_measure
from tests.fixtures import dummy_projection as dummy_projection
from tests.fixtures import dummy_pump_measure as dummy_pump_measure
from tests.fixtures import dummy_strategy as dummy_strategy
from tests.fixtures import dummy_time_model as dummy_time_model

session_tmp_dir = Path(tempfile.mkdtemp())
snapshot_dir = session_tmp_dir / "database_snapshot"
logs_dir = Path(__file__).resolve().parent / "logs"
src_dir = Path(
    *__path__
).resolve()  # __path__ is a list of paths to the package, but has only one element
IS_WINDOWS = platform.system() == "Windows"

#### DEBUGGING ####
# To disable resetting the database after tests: set CLEAN = False
# Only for debugging purposes, should always be set to true when pushing to github
clean = True

load_dotenv()
IS_WINDOWS = platform.system() == "Windows"
SETTINGS = Settings(
    DATABASE_ROOT=src_dir.parents[1] / "Database",
    DATABASE_NAME="charleston_test",
    DELETE_CRASHED_RUNS=clean,
    VALIDATE_ALLOWED_FORCINGS=True,
    MANUAL_DOCKER_CONTAINERS=True,
    USE_DOCKER=not IS_WINDOWS,
    USE_BINARIES=IS_WINDOWS,
)
SETTINGS.export_to_env()
execution_method = SETTINGS.get_scenario_execution_method(strict=False)
CAN_EXECUTE_SCENARIOS = execution_method is not None
if IS_WINDOWS and not CAN_EXECUTE_SCENARIOS:
    raise RuntimeError(
        "FloodAdapt must always be able to execute scenarios on Windows in the test environment"
    )


## AUTO USE FIXTURES ##
@pytest.fixture(scope="session", autouse=True)
def setup_settings():
    return SETTINGS


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Session-wide setup and teardown for creating the initial snapshot."""
    log_path = logs_dir / f"test_run_{datetime.now().strftime('%m-%d_%Hh-%Mm')}.log"
    logger = FloodAdaptLogging.getLogger()
    logger.info(f"Logging test run to {log_path}")
    start = datetime.now()

    with FloodAdaptLogging.to_file(file_path=log_path, level=logging.DEBUG):
        yield

    end = datetime.now()
    duration = end - start
    logger.info("Finished test run.")
    logger.info(f"Test run duration: {duration} (hh:mm:ss.ms)")


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(setup_settings: Settings):
    update_database_static(setup_settings)
    update_database_input(setup_settings)
    _create_snapshot()

    yield

    if clean:
        _restore_db_from_snapshot()
    shutil.rmtree(snapshot_dir, ignore_errors=True)


@pytest.fixture(scope="session", autouse=HAS_DOCKER)
def setup_docker_containers(setup_settings: Settings):
    logger = FloodAdaptLogging.getLogger()
    logger.info("Setting up Docker containers for testing.")

    SFINCS_CONTAINER.start(setup_settings.database_path)
    FIAT_CONTAINER.start(setup_settings.database_path)

    yield

    SFINCS_CONTAINER.stop()
    FIAT_CONTAINER.stop()
    logger.info(
        f"Docker containers initialized: {DockerContainer.CONTAINERS_INITIALIZED}"
    )
    logger.info("Finished tearing down Docker containers.")


## GENERAL FIXTURES ##
@pytest.fixture
def test_data_dir():
    return Path(__file__).parent / "data"


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    test_name = item.name
    logger = FloodAdaptLogging.getLogger()
    logger.info(f"\nStarting test: {test_name}\n")


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
        fa = FloodAdapt(SETTINGS.database_path)

        # Perform tests
        yield fa.database

        # Teardown
        fa.database.shutdown()
        if clean:
            _restore_db_from_snapshot()

    return _db_fixture


def make_fa_fixture(scope):
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
        fa = FloodAdapt(SETTINGS.database_path)

        # Perform tests
        yield fa

        # Teardown
        fa.database.shutdown()
        if clean:
            _restore_db_from_snapshot()

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

test_fa = make_fa_fixture("function")
test_fa_class = make_fa_fixture("class")
test_fa_module = make_fa_fixture("module")
test_fa_package = make_fa_fixture("package")
test_fa_session = make_fa_fixture("session")


## HELPER FUNCTIONS ##
def _create_snapshot():
    """Create a snapshot of the database directory."""
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(SETTINGS.database_path, snapshot_dir)


def _restore_db_from_snapshot():
    """Restore the database directory from the snapshot."""
    if not snapshot_dir.exists():
        raise FileNotFoundError(
            "Snapshot path does not exist. Create a snapshot first."
        )
    seen_files = set()
    db_path = SETTINGS.database_path

    for root, _, files in os.walk(snapshot_dir):
        # Copy deleted/changed files from snapshot to database
        for file in files:
            snapshot_file = Path(root) / file
            relative_path = snapshot_file.relative_to(snapshot_dir)
            database_file = db_path / relative_path
            seen_files.add(database_file)

            if not database_file.exists():
                os.makedirs(os.path.dirname(database_file), exist_ok=True)
                shutil.copy2(snapshot_file, database_file)
            elif not filecmp.cmp(snapshot_file, database_file):
                shutil.copy2(snapshot_file, database_file)

    for root, dirs, files in os.walk(db_path, topdown=False):
        # Remove created files from database
        for file in files:
            database_file = Path(root) / file
            if database_file not in seen_files:
                os.remove(database_file)

        # Remove empty directories from the database
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
