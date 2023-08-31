import os
from pathlib import Path

import tomli_w

from flood_adapt.object_model.interface.site import (
    DemModel,
    Obs_stationModel,
    SfincsModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge
from flood_adapt.object_model.site import (
    Site,
)

test_database = Path().absolute() / "tests" / "test_database"


def test_read_site_toml(cleanup_database):
    test_toml = test_database / "charleston" / "static" / "site" / "site.toml"

    assert test_toml.is_file()

    test_data = Site.load_file(test_toml)

    assert isinstance(test_data.attrs.name, str)
    assert isinstance(test_data.attrs.sfincs, SfincsModel)
    assert isinstance(test_data.attrs.dem, DemModel)
    assert isinstance(test_data.attrs.obs_station, Obs_stationModel)
    assert test_data.attrs.lat == 32.77
    assert test_data.attrs.slr.vertical_offset.value == 0.6
    assert test_data.attrs.fiat.exposure_crs == "EPSG:4326"
    assert test_data.attrs.river.mean_discharge.value == 5000


def test_read_site_toml_without_river(cleanup_database):
    test_toml = (
        test_database / "charleston" / "static" / "site" / "site_without_river.toml"
    )

    assert test_toml.is_file()

    test_data = Site.load_file(test_toml)

    assert isinstance(test_data.attrs.name, str)
    assert isinstance(test_data.attrs.sfincs, SfincsModel)
    assert isinstance(test_data.attrs.dem, DemModel)
    assert isinstance(test_data.attrs.obs_station, Obs_stationModel)
    assert test_data.attrs.lat == 32.77
    assert test_data.attrs.slr.vertical_offset.value == 0.6
    assert test_data.attrs.fiat.exposure_crs == "EPSG:4326"


def test_read_site_toml_with_multiple_rivers(cleanup_database):
    test_toml = test_database / "charleston" / "static" / "site" / "site.toml"

    assert test_toml.is_file()

    test_data = Site.load_file(test_toml)

    name = []
    description = []
    x = []
    y = []
    mean_discharge = []
    for ii in [0, 1, 2]:
        name.append(f"{test_data.attrs.river.name[0]}_{ii}")
        description.append(f"{test_data.attrs.river.description[0]} {ii}")
        x.append(test_data.attrs.river.x_coordinate[0] - 1000 * ii)
        y.append(test_data.attrs.river.y_coordinate[0] - 1000 * ii)
        mean_discharge.append(test_data.attrs.river.mean_discharge[0])

    test_data.attrs.river.name = name
    test_data.attrs.river.x_coordinate = x
    test_data.attrs.river.y_coordinate = y
    test_data.attrs.river.mean_discharge = mean_discharge
    test_data.attrs.river.description = description

    test_toml2 = (
        test_database
        / "charleston"
        / "static"
        / "site"
        / "site_with_multiple_rivers.toml"
    )
    with open(test_toml2, "wb") as f:
        tomli_w.dump(test_data.attrs.dict(), f)

    assert test_toml2.is_file()

    test_data2 = Site.load_file(test_toml2)

    assert isinstance(test_data2.attrs.river.name, list)
    assert isinstance(test_data2.attrs.river.x_coordinate, list)
    assert isinstance(test_data2.attrs.river.mean_discharge, list)
    assert isinstance(test_data2.attrs.river.mean_discharge[1], UnitfulDischarge)
    assert test_data2.attrs.river.mean_discharge[1].value == 5000.0

    os.remove(test_toml2)
