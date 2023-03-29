from pathlib import Path

from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"


def test_infographic():
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

    DirectImpacts.infographic(
        test_scenario,
        Path(
            "p:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/database/charleston/output/results"
        )
    )
