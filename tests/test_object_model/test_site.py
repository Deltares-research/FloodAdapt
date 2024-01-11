import os
from pathlib import Path
import pytest

import tomli_w

from flood_adapt.object_model.interface.site import (
    DemModel,
    Obs_stationModel,
    RiverModel,
    SfincsModel,
    WaterLevelReferenceModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge, UnitfulLength
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
    assert isinstance(test_data.attrs.water_level, WaterLevelReferenceModel)
    assert isinstance(test_data.attrs.water_level.other[0].height, UnitfulLength)
    assert test_data.attrs.lat == 32.77
    assert test_data.attrs.slr.vertical_offset.value == 0.6
    assert test_data.attrs.fiat.exposure_crs == "EPSG:4326"
    assert test_data.attrs.river[0].mean_discharge.value == 5000


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

@pytest.mark.skip(reason="ID of observation station is None and site.toml cannot currently be saved")
def test_read_site_toml_with_multiple_rivers(cleanup_database):
    test_toml = test_database / "charleston" / "static" / "site" / "site.toml"

    assert test_toml.is_file()

    test_data = Site.load_file(test_toml)

    for ii in [0, 1, 2]:
        test_data.attrs.river.append(
            RiverModel(
                name=f"{test_data.attrs.river[0].name}_{ii}",
                description=f"{test_data.attrs.river[0].description} {ii}",
                x_coordinate=(test_data.attrs.river[0].x_coordinate - 1000 * ii),
                y_coordinate=(test_data.attrs.river[0].y_coordinate - 1000 * ii),
                mean_discharge=test_data.attrs.river[0].mean_discharge,
            )
        )

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

    assert isinstance(test_data2.attrs.river, list)
    assert isinstance(test_data2.attrs.river[1].name, str)
    assert isinstance(test_data2.attrs.river[1].x_coordinate, float)
    assert isinstance(test_data2.attrs.river[1].mean_discharge, UnitfulDischarge)
    assert test_data2.attrs.river[1].mean_discharge.value == 5000.0

    os.remove(test_toml2)
