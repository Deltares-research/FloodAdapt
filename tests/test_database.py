import shutil
from os import listdir
from pathlib import Path

from flood_adapt.api.static import read_database
from flood_adapt.misc.config import Settings
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.site import Site


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
    test_db.create_benefit_scenarios(benefit)

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


def test_projection_interp_slr(test_db):
    slr = test_db.interp_slr("ssp245", 2075)
    assert slr > 1.0
    assert slr < 1.1


def test_projection_plot_slr(test_db):
    html_file_loc = test_db.plot_slr_scenarios()
    print(html_file_loc)
    assert Path(html_file_loc).is_file()


def test_cleanup_NoInput_RemoveOutput():
    # Arrange
    input_path = Settings().database_path / "input" / "scenarios" / "test123"
    if input_path.exists():
        shutil.rmtree(input_path)

    output_path = Settings().database_path / "output" / "scenarios" / "test123"
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / "test123.txt", "w") as f:
        f.write("run finished")

    # Act
    dbs = read_database(Settings().database_root, Settings().database_name)

    # Assert
    assert not output_path.exists()

    # Cleanup singleton
    dbs.shutdown()


def test_cleanup_InputExists_RunNotFinished_OutputRemoved():
    # Arrange
    input_path = Settings().database_path / "input" / "scenarios"
    output_path = Settings().database_path / "output" / "scenarios"

    scenario_name = listdir(input_path)[0]
    input_dir = input_path / scenario_name
    output_dir = output_path / scenario_name

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    with open(output_dir / "test123.txt", "w") as f:
        f.write("run not finished")

    # Act
    dbs = read_database(Settings().database_root, Settings().database_name)

    # Assert
    assert input_dir.exists()
    assert not output_dir.exists()

    # Cleanup singleton
    dbs.shutdown()


def test_shutdown_AfterShutdown_VarsAreNone():
    # Arrange
    dbs = read_database(Settings().database_root, Settings().database_name)

    # Act
    dbs.shutdown()

    # Assert
    assert dbs.__class__._instance is None
    assert dbs._instance is None
    assert dbs._init_done is False
    assert dbs.database_path is None
    assert dbs.database_name is None
    assert dbs.base_path is None
    assert dbs.input_path is None
    assert dbs.static_path is None
    assert dbs.output_path is None
    assert dbs._site is None
    assert dbs.static_sfincs_model is None
    assert dbs.logger is None
    assert dbs._static is None
    assert dbs._events is None
    assert dbs._scenarios is None
    assert dbs._strategies is None
    assert dbs._measures is None
    assert dbs._projections is None
    assert dbs._benefits is None


def test_shutdown_AfterShutdown_CanReadNewDatabase():
    # Arrange
    dbs = read_database(Settings().database_root, Settings().database_name)

    # Act
    dbs.shutdown()
    dbs = read_database(Settings().database_root, Settings().database_name)

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
    assert dbs.static_sfincs_model is not None
    assert dbs.logger is not None
    assert dbs._static is not None
    assert dbs._events is not None
    assert dbs._scenarios is not None
    assert dbs._strategies is not None
    assert dbs._measures is not None
    assert dbs._projections is not None
    assert dbs._benefits is not None
