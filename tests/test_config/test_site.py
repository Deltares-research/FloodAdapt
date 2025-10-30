from pathlib import Path

import pytest
from pydantic import BaseModel
from pydantic_core import ValidationError

from flood_adapt.config.hazard import (
    AsciiStr,
    RiverModel,
)
from flood_adapt.config.site import (
    Site,
)


def test_save_and_load_file(test_site: Site, tmp_path: Path):
    toml_filepath = tmp_path / "site.toml"
    test_site.save(toml_filepath)

    loaded_site = Site.load_file(toml_filepath)
    assert loaded_site == test_site


def test_save_added_rivers_to_model_saved_correctly(test_site: Site, tmp_path: Path):
    toml_filepath = tmp_path / "site_with_extra_rivers.toml"
    test_site.sfincs.river = test_site.sfincs.river or []
    number_rivers_before = len(test_site.sfincs.river)
    number_additional_rivers = 3

    for i in range(number_additional_rivers):
        test_site.add_river(
            RiverModel(
                name=f"{test_site.sfincs.river[i].description}_{i}",
                description=f"{test_site.sfincs.river[i].description}_{i}",
                x_coordinate=(test_site.sfincs.river[i].x_coordinate - 1000 * i),
                y_coordinate=(test_site.sfincs.river[i].y_coordinate - 1000 * i),
                mean_discharge=test_site.sfincs.river[i].mean_discharge,
            )
        )

    assert test_site.sfincs.river is not None
    assert (
        len(test_site.sfincs.river) == number_rivers_before + number_additional_rivers
    )

    test_site.save(toml_filepath)
    assert toml_filepath.is_file()

    loaded_site = Site.load_file(toml_filepath)
    assert isinstance(loaded_site.sfincs.river, list)
    assert (
        len(loaded_site.sfincs.river) == number_additional_rivers + number_rivers_before
    )


class AsciiValidatorTest(BaseModel):
    string: AsciiStr


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
