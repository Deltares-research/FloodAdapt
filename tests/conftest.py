import filecmp
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from cht_cyclones.tropical_cyclone import TropicalCyclone
from dotenv import load_dotenv

from flood_adapt import FloodAdapt, FloodAdaptLogging, __path__
from flood_adapt.config import RiverModel, Settings
from flood_adapt.objects import (
    Buyout,
    MeasureType,
    PhysicalProjection,
    Projection,
    Pump,
    Scenario,
    SelectionType,
    SocioEconomicChange,
    Strategy,
    SyntheticEvent,
)
from flood_adapt.objects.forcing import (
    DischargeConstant,
    ForcingType,
    RainfallConstant,
    ShapeType,
    SurgeModel,
    TideModel,
    TimeFrame,
    TimeseriesFactory,
    WaterlevelSynthetic,
    WindConstant,
)
from flood_adapt.objects.forcing import unit_system as us
from tests.data.create_test_input import update_database_input
from tests.data.create_test_static import update_database_static

session_tmp_dir = Path(tempfile.mkdtemp())
snapshot_dir = session_tmp_dir / "database_snapshot"
logs_dir = Path(__file__).absolute().parent / "logs"
src_dir = Path(
    *__path__
).resolve()  # __path__ is a list of paths to the package, but has only one element

#### DEBUGGING ####
# To disable resetting the database after tests: set CLEAN = False
# Only for debugging purposes, should always be set to true when pushing to github
clean = True


def create_snapshot():
    """Create a snapshot of the database directory."""
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(Settings().database_path, snapshot_dir)


def restore_db_from_snapshot():
    """Restore the database directory from the snapshot."""
    if not snapshot_dir.exists():
        raise FileNotFoundError(
            "Snapshot path does not exist. Create a snapshot first."
        )
    seen_files = set()
    db_path = Settings().database_path

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


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown():
    """Session-wide setup and teardown for creating the initial snapshot."""
    load_dotenv()

    settings = Settings(
        DATABASE_ROOT=src_dir.parents[1] / "Database",
        DATABASE_NAME="charleston_test",
        DELETE_CRASHED_RUNS=clean,
        VALIDATE_ALLOWED_FORCINGS=True,
        VALIDATE_BINARIES=True,
    )

    log_path = logs_dir / f"test_run_{datetime.now().strftime('%m-%d_%Hh-%Mm')}.log"
    FloodAdaptLogging(
        file_path=log_path,
        level=logging.DEBUG,
        ignore_warnings=[DeprecationWarning],
    )

    update_database_static(settings.database_path)
    update_database_input(settings.database_path)
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
        fa = FloodAdapt(Settings().database_path)

        # Perform tests
        yield fa.database

        # Teardown
        fa.database.shutdown()
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
        fa = FloodAdapt(Settings().database_path)

        # Perform tests
        yield fa

        # Teardown
        fa.database.shutdown()
        if clean:
            restore_db_from_snapshot()

    return _db_fixture


test_fa = make_fa_fixture("function")
test_fa_class = make_fa_fixture("class")
test_fa_module = make_fa_fixture("module")
test_fa_package = make_fa_fixture("package")
test_fa_session = make_fa_fixture("session")


@pytest.fixture
def test_data_dir():
    return Path(__file__).parent / "data"


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    test_name = item.name
    logger = FloodAdaptLogging.getLogger()
    logger.info(f"\nStarting test: {test_name}\n")


@pytest.fixture()
def dummy_time_model() -> TimeFrame:
    return TimeFrame()


@pytest.fixture()
def dummy_1d_timeseries_df(dummy_time_model) -> pd.DataFrame:
    return _n_dim_dummy_timeseries_df(1, dummy_time_model)


@pytest.fixture()
def dummy_2d_timeseries_df(dummy_time_model) -> pd.DataFrame:
    return _n_dim_dummy_timeseries_df(2, dummy_time_model)


def _n_dim_dummy_timeseries_df(n_dims: int, time_model: TimeFrame) -> pd.DataFrame:
    time = pd.date_range(
        start=time_model.start_time - 10 * time_model.time_step,
        end=time_model.end_time + 10 * time_model.time_step,
        freq=time_model.time_step,
        name="time",
    )
    gen = np.random.default_rng()
    data = {f"data_{i}": gen.random(len(time)) for i in range(n_dims)}
    df = pd.DataFrame(index=time, data=data, dtype=float)
    return df


@pytest.fixture(scope="session")
def spw_file(test_data_dir) -> Path:
    cyc_file = test_data_dir / "IAN.cyc"
    spw_file = test_data_dir / "IAN.spw"
    if spw_file.exists():
        return spw_file
    tc = TropicalCyclone()
    tc.include_rainfall = True
    tc.read_track(cyc_file, fmt="ddb_cyc")
    tc.to_spiderweb(spw_file)
    return spw_file


@pytest.fixture
def shapefile(test_data_dir: Path):
    return test_data_dir / "shapefiles" / "pop_growth_new_20.shp"


## Dummy fixtures


@pytest.fixture()
def dummy_buyout_measure():
    return Buyout(
        name="dummy_buyout_measure",
        type=MeasureType.buyout_properties,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_type="aggr_lvl_2",
        aggregation_area_name="name1",
        property_type="residential",
    )


@pytest.fixture()
def dummy_pump_measure(test_data_dir):
    return Pump(
        name="dummy_pump_measure",
        type=MeasureType.pump,
        selection_type=SelectionType.polyline,
        gdf=gpd.read_file(test_data_dir / "pump.geojson").to_crs(epsg=4326),
        discharge=us.UnitfulDischarge(value=100, units=us.UnitTypesDischarge.cfs),
    )


@pytest.fixture()
def dummy_strategy(dummy_buyout_measure, dummy_pump_measure):
    pump = dummy_pump_measure
    buyout = dummy_buyout_measure
    strategy = Strategy(
        name="dummy_strategy",
        description="",
        measures=[buyout.name, pump.name],
    )
    strategy.initialize_measure_objects([buyout, pump])
    return strategy


@pytest.fixture()
def dummy_projection():
    return Projection(
        name="dummy_projection",
        physical_projection=PhysicalProjection(),
        socio_economic_change=SocioEconomicChange(),
    )


@pytest.fixture()
def dummy_event():
    return SyntheticEvent(
        name="test_synthetic_nearshore",
        time=TimeFrame(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        forcings={
            ForcingType.WIND: [
                WindConstant(
                    speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                )
            ],
            ForcingType.RAINFALL: [
                RainfallConstant(
                    intensity=us.UnitfulIntensity(
                        value=20, units=us.UnitTypesIntensity.mm_hr
                    )
                )
            ],
            ForcingType.DISCHARGE: [
                DischargeConstant(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=5000, units=us.UnitTypesDischarge.cfs
                    ),
                )
            ],
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    surge=SurgeModel(
                        timeseries=TimeseriesFactory.from_args(
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=1, units=us.UnitTypesLength.meters
                            ),
                        )
                    ),
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.meters
                        ),
                        harmonic_period=us.UnitfulTime(
                            value=12.4, units=us.UnitTypesTime.hours
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                )
            ],
        },
    )


@pytest.fixture()
def dummy_scenario(
    dummy_event,
    dummy_projection,
    dummy_strategy,
):
    scn = Scenario(
        name="dummy_scenario",
        event=dummy_event.name,
        projection=dummy_projection.name,
        strategy=dummy_strategy.name,
    )
    return scn
