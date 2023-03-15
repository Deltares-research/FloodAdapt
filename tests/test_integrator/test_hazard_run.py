from pathlib import Path

from flood_adapt.object_model.hazard.hazard import Hazard

test_database = Path().absolute() / "tests" / "test_database"


def test_hazard_run():
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
    test_hazard = Hazard()
    test_hazard.run_sfincs()
