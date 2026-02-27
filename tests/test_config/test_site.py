import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel
from pydantic_core import ValidationError

import flood_adapt.objects.forcing.unit_system as us
from flood_adapt.config.hazard import (
    AsciiStr,
    DemModel,
    RiverModel,
)
from flood_adapt.config.settings import Settings
from flood_adapt.config.site import (
    SfincsModel,
    Site,
)
from flood_adapt.objects.forcing.tide_gauge import TideGauge
from tests.data.create_test_static import create_site_config


class AsciiValidatorTest(BaseModel):
    string: AsciiStr


@pytest.fixture
def test_tomls(test_db):
    toml_files = [
        test_db.static_path / "config" / "site.toml",
        test_db.static_path / "config" / "site_without_river.toml",
    ]
    yield toml_files


@pytest.fixture
def test_sites(test_db, test_tomls):
    test_sites = {toml_file.name: Site.load_file(toml_file) for toml_file in test_tomls}
    yield test_sites


def test_loadFile_validFiles(test_tomls):
    for toml_filepath in test_tomls:
        Site.load_file(toml_filepath)


def test_loadFile_invalidFile_raiseFileNotFoundError(test_db):
    with pytest.raises(FileNotFoundError):
        Site.load_file("not_a_file.toml")


def test_loadFile_validFile_returnSite(test_sites):
    test_site = test_sites["site.toml"]
    assert isinstance(test_site, Site)


def test_loadFile_tomlFile_setAttrs(test_sites):
    test_site = test_sites["site.toml"]
    assert isinstance(test_site.sfincs.water_level.datums[0].height, us.UnitfulLength)

    assert test_site.lat == 32.7765
    assert test_site.fiat.config.exposure_crs == "EPSG:4326"
    assert test_site.sfincs.river[0].mean_discharge.value == 5000


def test_loadFile_tomlFile_no_river(test_sites):
    test_site = test_sites["site_without_river.toml"]
    assert isinstance(test_site.name, str)
    assert isinstance(test_site.sfincs, SfincsModel)
    assert isinstance(test_site.sfincs.dem, DemModel)
    assert isinstance(test_site.sfincs.tide_gauge, TideGauge)
    assert test_site.lat == 32.7765
    assert test_site.fiat.config.exposure_crs == "EPSG:4326"


def test_save_addedRiversToModel_savedCorrectly(test_db, test_sites):
    test_site_1_river = test_sites["site.toml"]
    number_rivers_before = len(test_site_1_river.sfincs.river)
    number_additional_rivers = 3

    for i in range(number_additional_rivers):
        test_site_1_river.sfincs.river.append(
            RiverModel(
                name=f"{test_site_1_river.sfincs.river[i].description}_{i}",
                description=f"{test_site_1_river.sfincs.river[i].description}_{i}",
                x_coordinate=(
                    test_site_1_river.sfincs.river[i].x_coordinate - 1000 * i
                ),
                y_coordinate=(
                    test_site_1_river.sfincs.river[i].y_coordinate - 1000 * i
                ),
                mean_discharge=test_site_1_river.sfincs.river[i].mean_discharge,
            )
        )
    new_toml = test_db.static_path / "config" / "site_multiple_rivers.toml"

    test_site_1_river.save(new_toml)
    assert new_toml.is_file()

    test_site_multiple_rivers = Site.load_file(new_toml)

    assert isinstance(test_site_multiple_rivers.sfincs.river, list)
    assert (
        len(test_site_multiple_rivers.sfincs.river)
        == number_additional_rivers + number_rivers_before
    )

    for i, river in enumerate(test_site_multiple_rivers.sfincs.river):
        assert isinstance(river, RiverModel)

        assert isinstance(test_site_multiple_rivers.sfincs.river[i].name, str)
        assert isinstance(test_site_multiple_rivers.sfincs.river[i].x_coordinate, float)
        assert isinstance(
            test_site_multiple_rivers.sfincs.river[i].mean_discharge,
            us.UnitfulDischarge,
        )
        assert (
            test_site_multiple_rivers.sfincs.river[i].mean_discharge.value
            == test_site_1_river.sfincs.river[i].mean_discharge.value
        )


# empty string, easy string, giberish and ascii control bytes shoulda ll be accepted
@pytest.mark.parametrize(
    "string",
    [
        "",
        "hello world",
        "!@#$%^)(^&)^&)",
        "\x00",
        "\x09",
        "\x0a",
        "\x0d",
        "\x1b",
        "\x7f",
    ],
)
def test_ascii_validator_correct(string):
    AsciiValidatorTest(string=string)  # should not raise an error if it's successful


# zero width spacer, some chinese, the greek questionmark, german town name with umlaut, and the pound sign
@pytest.mark.parametrize("string", ["​", "園冬童", ";", "Altötting", "\xa3"])
def test_ascii_validator_incorrect(string):
    with pytest.raises(ValidationError):
        AsciiValidatorTest(string=string)


def test_site_builder_load_file():
    file_path: Path = Path(tempfile.gettempdir()) / "site.toml"
    if file_path.exists():
        file_path.unlink()

    to_save = create_site_config(database_path=Settings().database_path)
    to_save.save(file_path)

    loaded = Site.load_file(file_path)

    assert to_save == loaded
