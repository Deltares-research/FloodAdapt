import shutil
from os import listdir
from pathlib import Path

from flood_adapt.api.static import read_database
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.site import Site

from .conftest import DATABASE_PATH, DATABASE_ROOT, SITE_NAME


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
    input_path = DATABASE_PATH / "input" / "scenarios" / "test123"
    if input_path.exists():
        shutil.rmtree(input_path)

    output_path = DATABASE_PATH / "output" / "scenarios" / "test123"
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / "test123.txt", "w") as f:
        f.write("run finished")

    # Act
    dbs = read_database(DATABASE_ROOT, SITE_NAME)

    # Assert
    assert not output_path.exists()

    # Cleanup singleton
    dbs.shutdown()


def test_cleanup_InputExists_RunNotFinished_OutputRemoved():
    # Arrange
    input_path = DATABASE_PATH / "input" / "scenarios"
    output_path = DATABASE_PATH / "output" / "scenarios"

    scenario_name = listdir(input_path)[0]
    input_dir = input_path / scenario_name
    output_dir = output_path / scenario_name

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    with open(output_dir / "test123.txt", "w") as f:
        f.write("run not finished")

    # Act
    dbs = read_database(DATABASE_ROOT, SITE_NAME)

    # Assert
    assert input_dir.exists()
    assert not output_dir.exists()

    # Cleanup singleton
    dbs.shutdown()
