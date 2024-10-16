from unittest.mock import patch


@patch("flood_adapt.object_model.hazard.run_sfincs.sys.platform", "linux")
def test_run_sfincs_on_linux(test_db):
    # Assert
    name = "current_extreme12ft_no_measures"
    scn = test_db.scenarios.get(name)

    # Act
    scn.run()

    # Assert
    assert (test_db.scenarios.get_database_path(get_input_path=False) / name).exists()


@patch("flood_adapt.object_model.hazard.run_sfincs.sys.platform", "win32")
def test_run_sfincs_on_windows(test_db):
    # Assert
    name = "current_extreme12ft_no_measures"
    scn = test_db.scenarios.get(name)

    # Act
    scn.run()

    # Assert
    assert (test_db.scenarios.get_database_path(get_input_path=False) / name).exists()
