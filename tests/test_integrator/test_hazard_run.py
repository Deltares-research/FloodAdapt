from pathlib import Path

from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"
import pytest


# @pytest.mark.skip(reason="There is no sfincs.inp checked in")
@pytest.mark.asyncio
async def test_hazard_run_synthetic_wl():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.init_object_model()
    await test_scenario.direct_impacts.hazard.run_sfincs()


# @pytest.mark.skip(reason="There is no sfincs.inp checked in")
@pytest.mark.asyncio
async def test_hazard_run_synthetic_discharge():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_rivershape_windconst_no_measures"
        / "current_extreme12ft_rivershape_windconst_no_measures.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.init_object_model()
    # test = await test_scenario.direct_impacts.hazard.run_sfincs()
    test_scenario.direct_impacts.hazard.has_run = False
    test = await test_scenario.direct_impacts.hazard.run_models()
    await test
    print(test)
