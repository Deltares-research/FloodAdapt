from pathlib import Path

import pytest

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

test_database = Path().absolute() / "tests" / "test_database"


@pytest.mark.skip(reason="not implemented yet")
def test_add_wl():
    model_root = Path(
        "n:\Projects\11207500\11207949\F. Other information\Test_data\database\charleston\output\simulations\current_kingTideNov2021_no_measures\sfincs_charleston_large_v01"
    )

    sf = SfincsAdapter()

    sf.load_overland_sfincs_model(model_root=model_root)

    print("test")
