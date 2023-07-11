import shutil
from pathlib import Path

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.site import Site

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "Charleston"


def test_database_controller():
    dbs = Database(test_database_path, test_site_name)

    assert isinstance(dbs.site, Site)


def test_create_benefit_scenarios():
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


def test_projection_interp_slr():
    dbs = Database(test_database_path, test_site_name)

    slr = dbs.interp_slr("ssp245", 2075)

    assert slr > 1.0
    assert slr < 1.1


def test_projection_plot_slr():
    dbs = Database(test_database_path, test_site_name)
    html_file_loc = dbs.plot_slr_scenarios()

    print(html_file_loc)
    assert Path(html_file_loc).is_file()


def test_has_hazard_run():
    dbs = Database(test_database_path, test_site_name)

    results = [
        dbs.input_path.parent
        / "output"
        / "simulations"
        / "current_extreme12ft_no_measures",
        dbs.input_path.parent
        / "output"
        / "simulations"
        / "current_extreme12ft_strategy_impact_comb",
        dbs.input_path.parent
        / "output"
        / "results"
        / "current_extreme12ft_no_measures",
        dbs.input_path.parent
        / "output"
        / "results"
        / "current_extreme12ft_strategy_impact_comb",
    ]

    for res in results:
        shutil.rmtree(res, ignore_errors=True)

    scenario_name_1 = "current_extreme12ft_no_measures"
    scenario_name_2 = "current_extreme12ft_strategy_impact_comb"

    scenario1 = dbs.get_scenario(scenario_name_1)
    assert scenario1.direct_impacts.hazard.has_run is False
    assert scenario1.direct_impacts.has_run is False
    dbs.run_scenario(scenario_name_1)
    scenario1 = dbs.get_scenario(scenario_name_1)
    assert scenario1.direct_impacts.hazard.has_run is True
    assert scenario1.direct_impacts.has_run == True

    scenario2 = dbs.get_scenario(scenario_name_2)
    assert scenario2.direct_impacts.hazard.has_run is False
    assert scenario2.direct_impacts.has_run is False
    dbs.run_scenario(scenario_name_2)

    scenario2 = dbs.get_scenario(scenario_name_2)
    assert scenario2.direct_impacts.hazard.has_run is True
    assert scenario2.direct_impacts.has_run == True
