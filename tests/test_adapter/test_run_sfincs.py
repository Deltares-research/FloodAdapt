import shutil
from pathlib import Path

import pytest

from flood_adapt.adapter.run_fiat import execute_fiat
from flood_adapt.adapter.run_sfincs import execute_sfincs


@pytest.fixture
def setup_sfincs_dir(tmp_path):
    path = Path("/home/lblom/dev/template/Flooding/simulations/overland")

    sim_dir = tmp_path / "testsfincs"

    shutil.copytree(path, sim_dir)

    return sim_dir


def test_run_sfincs_on_linux(setup_sfincs_dir):
    # Act

    success = execute_sfincs(setup_sfincs_dir)

    # Assert

    assert success


@pytest.fixture
def setup_fiat_dir(tmp_path):
    path = Path("/home/lblom/dev/template/fiat")

    sim_dir = tmp_path / "testfiat"

    shutil.copytree(path, sim_dir)

    return sim_dir


def test_run_fiat_on_linux(setup_fiat_dir):
    # Act

    success = execute_fiat(setup_fiat_dir)

    # Assert

    assert success


# def test_run_sfincs_on_windows(test_db):
#     # Assert
#     name = "current_extreme12ft_no_measures"
#     scn = test_db.scenarios.get(name)

#     # Act
#     scn.run()

#     # Assert
#     assert (test_db.scenarios.get_database_path(get_input_path=False) / name).exists()
