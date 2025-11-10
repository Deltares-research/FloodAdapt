import shutil
from os import listdir
from pathlib import Path

import pytest

from flood_adapt.config import SETTINGS
from flood_adapt.config.site import Site
from flood_adapt.dbs_classes.database import Database
from flood_adapt.misc.exceptions import IsStandardObjectError
from flood_adapt.workflows.benefit_runner import Benefit, BenefitRunner


def test_database_controller(test_db):
    assert isinstance(test_db.site, Site)


def test_create_benefit_scenarios(test_db):
    benefit_toml = (
        test_db.input_path
        / "benefits"
        / "benefit_raise_properties_2050"
        / "benefit_raise_properties_2050.toml"
    )

    assert benefit_toml.is_file()

    benefit = Benefit.load_file(benefit_toml)
    runner = BenefitRunner(test_db, benefit)
    runner.create_benefit_scenarios()

    # Check if scenarios were created and then delete them
    scenarios_path = test_db.input_path / "scenarios"

    path1 = scenarios_path / "all_projections_test_set_elevate_comb_correct"
    path2 = scenarios_path / "all_projections_test_set_no_measures"
    path3 = scenarios_path / "current_test_set_elevate_comb_correct"

    assert path1.is_dir()
    assert path2.is_dir()
    assert path3.is_dir()

    # Delete scenarios created
    shutil.rmtree(path1)
    shutil.rmtree(path2)
    shutil.rmtree(path3)


def test_projection_interp_slr(test_fa):
    slr = test_fa.interp_slr("ssp245", 2075)
    assert slr > 1.0
    assert slr < 1.1


def test_projection_plot_slr(test_fa):
    html_file_loc = test_fa.plot_slr_scenarios()
    assert Path(html_file_loc).is_file()


def test_cleanup_NoInput_RemoveOutput():
    # Arrange
    input_path = SETTINGS.database_path / "input" / "scenarios" / "test123"
    if input_path.exists():
        shutil.rmtree(input_path)

    output_path = SETTINGS.database_path / "output" / "scenarios" / "test123"
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / "test123.txt", "w") as f:
        f.write("run finished")

    # Act
    dbs = Database(SETTINGS.database_root, SETTINGS.database_name)

    # Assert
    assert not output_path.exists()

    # Cleanup singleton
    dbs.shutdown()


def test_cleanup_InputExists_RunNotFinished_OutputRemoved():
    # Arrange
    input_path = SETTINGS.database_path / "input" / "scenarios"
    output_path = SETTINGS.database_path / "output" / "scenarios"

    scenario_name = listdir(input_path)[0]
    input_dir = input_path / scenario_name
    output_dir = output_path / scenario_name

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    with open(output_dir / "test123.txt", "w") as f:
        f.write("run not finished")

    # Act
    dbs = Database(SETTINGS.database_root, SETTINGS.database_name)

    # Assert
    assert input_dir.exists()
    assert not output_dir.exists()

    # Cleanup singleton
    dbs.shutdown()


def test_shutdown_AfterShutdown_VarsAreNone():
    # Arrange
    dbs = Database(SETTINGS.database_root, SETTINGS.database_name)

    # Act
    dbs.shutdown()

    # Assert
    assert dbs.__class__._instance is None
    assert dbs._instance is None
    assert dbs._init_done is False
    assert dbs.__dict__ == {}


def test_shutdown_AfterShutdown_CanReadNewDatabase():
    # Arrange
    dbs = Database(SETTINGS.database_root, SETTINGS.database_name)

    # Act
    dbs.shutdown()
    dbs = Database(SETTINGS.database_root, SETTINGS.database_name)

    # Assert
    assert dbs.__class__._instance is not None
    assert dbs._instance is not None
    assert dbs._init_done
    assert dbs.database_path is not None
    assert dbs.database_name is not None
    assert dbs.base_path is not None
    assert dbs.input_path is not None
    assert dbs.static_path is not None
    assert dbs.output_path is not None
    assert dbs._site is not None
    assert dbs._static is not None
    assert dbs._events is not None
    assert dbs._scenarios is not None
    assert dbs._strategies is not None
    assert dbs._measures is not None
    assert dbs._projections is not None
    assert dbs._benefits is not None


def test_cannot_delete_standard_objects(test_db: Database):
    # Arrange

    # Act
    for event in test_db.site.standard_objects.events:
        with pytest.raises(IsStandardObjectError):
            test_db.events.delete(event)

    for projection in test_db.site.standard_objects.projections:
        with pytest.raises(IsStandardObjectError):
            test_db.projections.delete(projection)

    for strategy in test_db.site.standard_objects.strategies:
        with pytest.raises(IsStandardObjectError):
            test_db.strategies.delete(strategy)
