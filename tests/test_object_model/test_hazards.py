from pathlib import Path

import pandas as pd

from flood_adapt.object_model.hazard.event.synthetic import TideModel
from flood_adapt.object_model.hazard.hazard import Hazard

test_database = Path().absolute() / "tests" / "test_database"


def test_hazard_load():
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
    hazard = Hazard.load_file(test_toml)

    assert hazard.event_obj.attrs.timing == "idealized"
    assert isinstance(hazard.event_obj.attrs.tide, TideModel)


def test_hazard_wl():
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
    test_hazard = Hazard.load_file(test_toml)
    test_hazard.add_wl_ts()

    assert isinstance(test_hazard.wl_ts, pd.DataFrame)
    assert len(test_hazard.wl_ts) > 1
