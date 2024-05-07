import shutil
from pathlib import Path

from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.site import Site


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
