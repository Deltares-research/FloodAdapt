from pathlib import Path

from flood_adapt.object_model.interface.site import (
    DemModel,
    Obs_stationModel,
    SfincsModel,
)
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
