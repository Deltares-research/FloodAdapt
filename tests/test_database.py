import shutil
from pathlib import Path

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.site import Site

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "Charleston"


def test_database_controller(cleanup_database):
    dbs = Database(test_database_path, test_site_name)

    assert isinstance(dbs.site, Site)


def test_create_benefit_scenarios(cleanup_database):
    dbs = Database(test_database_path, test_site_name)

    benefit_toml = (
        test_database_path
        / "charleston"
        / "input"
        / "benefits"
        / "benefit_raise_properties_2050"
        / "benefit_raise_properties_2050.toml"
    )

    assert benefit_toml.is_file()

    benefit = Benefit.load_file(benefit_toml)
    dbs.create_benefit_scenarios(benefit)

    # Check if scenarios were created and then delete them
    scenarios_path = test_database_path.joinpath("charleston", "input", "scenarios")

    path1 = scenarios_path.joinpath("all_projections_test_set_elevate_comb_correct")
    path2 = scenarios_path.joinpath("all_projections_test_set_no_measures")
    path3 = scenarios_path.joinpath("current_test_set_elevate_comb_correct")

    assert path1.is_dir()
    assert path2.is_dir()
    assert path3.is_dir()

    # Delete scenarios created
    shutil.rmtree(path1)
    shutil.rmtree(path2)
    shutil.rmtree(path3)


def test_projection_interp_slr(cleanup_database):
    dbs = Database(test_database_path, test_site_name)

    slr = dbs.interp_slr("ssp245", 2075)

    assert slr > 1.0
    assert slr < 1.1


def test_projection_plot_slr(cleanup_database):
    dbs = Database(test_database_path, test_site_name)
    html_file_loc = dbs.plot_slr_scenarios()

    print(html_file_loc)
    assert Path(html_file_loc).is_file()


def test_has_hazard_run(cleanup_database):
    dbs = Database(test_database_path, test_site_name)
    scenario_name = "current_extreme12ft_no_measures"
    output_path = dbs.output_path.joinpath("Scenarios", scenario_name)
    if output_path.exists():
        shutil.rmtree(output_path)
    scenario1 = dbs.get_scenario(scenario_name)
    assert scenario1.direct_impacts.hazard.has_run is False
    assert scenario1.direct_impacts.has_run is False
    dbs.run_scenario(scenario_name)
    scenario1 = dbs.get_scenario(scenario_name)
    assert scenario1.direct_impacts.hazard.has_run is True
    assert scenario1.direct_impacts.has_run is True
