import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel
from pydantic_core import ValidationError

import flood_adapt.objects.forcing.unit_system as us
from flood_adapt.config.sfincs import (
    AsciiStr,
    DemModel,
    RiverModel,
    TideGauge,
)
from flood_adapt.config.site import (
    SfincsModel,
    Site,
)
from tests.data.create_test_static import create_site_config


class AsciiValidatorTest(BaseModel):
    string: AsciiStr


@pytest.fixture()
def test_dict():
    config_values = {
        "name": "charleston",
        "description": "Charleston, SC - DUMMY MODEL",
        "lat": 32.77,
        "lon": -79.95,
        "sfincs": {
            "csname": "WGS 84 / UTM zone 17N",
            "cstype": "projected",
            "offshore_model": "offshore",
            "overland_model": "overland",
            "ambient_air_pressure": 102000,
            "floodmap_no_data_value": -9999,
            "floodmap_units": "feet",
            "save_simulation": "False",
        },
        "water_level": {
            "reference": {"name": "MLLW", "height": {"value": 0.0, "units": "meters"}},
            "msl": {"name": "MSL", "height": {"value": 0.89, "units": "meters"}},
            "localdatum": {
                "name": "NAVD88",
                "height": {"value": 0.957, "units": "meters"},
            },
            "other": [
                {"name": "MHHW", "height": {"value": 1.757, "units": "meters"}},
                {"name": "MLLW", "height": {"value": 0.0, "units": "meters"}},
            ],
        },
        "cyclone_track_database": {"file": "IBTrACS.NA.v04r00.nc"},
        "slr": {
            "relative_to_year": 2020,
        },
        "gui": {
            "default_length_units": "feet",
            "default_distance_units": "miles",
            "default_area_units": "sf",
            "default_volume_units": "cf",
            "default_velocity_units": "knots",
            "default_direction_units": "deg N",
            "default_discharge_units": "cfs",
            "default_intensity_units": "inch/hr",
            "default_cumulative_units": "inch",
            "tide_harmonic_amplitude": {"value": 3.0, "units": "feet"},
            "mapbox_layers": {
                "flood_map_depth_min": 0.328,
                "flood_map_zbmax": 3.28,
                "flood_map_bins": [1, 3, 5],
                "flood_map_colors": ["#BED2FF", "#B4D79E", "#1F80B8", "#081D58"],
                "aggregation_dmg_bins": [0.00001, 1000000, 2500000, 5000000, 10000000],
                "aggregation_dmg_colors": [
                    "#FFFFFF",
                    "#FEE9CE",
                    "#FDBB84",
                    "#FC844E",
                    "#E03720",
                    "#860000",
                ],
                "footprints_dmg_bins": [0.00001, 15000, 50000, 100000, 250000],
                "footprints_dmg_colors": [
                    "#FFFFFF",
                    "#FEE9CE",
                    "#FDBB84",
                    "#FC844E",
                    "#E03720",
                    "#860000",
                ],
                "svi_bins": [0.05, 0.2, 0.4, 0.6, 0.8],
                "svi_colors": [
                    "#FFFFFF",
                    "#FEE9CE",
                    "#FDBB84",
                    "#FC844E",
                    "#E03720",
                    "#860000",
                ],
                "benefits_bins": [0, 0.01, 1000000, 10000000, 50000000],
                "benefits_colors": [
                    "#FF7D7D",
                    "#FFFFFF",
                    "#DCEDC8",
                    "#AED581",
                    "#7CB342",
                    "#33691E",
                ],
            },
        },
        "risk": {
            "return_periods": [1, 2, 5, 10, 25, 50, 100],
            "flooding_threshold": {"value": 0.5, "units": "feet"},
        },
        "dem": {"filename": "charleston_14m.tif", "units": "meters"},
        "fiat": {
            "exposure_crs": "EPSG:4326",
            "floodmap_type": "water_level",
            "non_building_names": ["road"],
            "damage_unit": "$",
            "building_footprints": "templates/fiat/footprints/Buildings.shp",
            "roads_file_name": "spatial2.gpkg",
            "new_development_file_name": "spatial3.gpkg",
            "save_simulation": "False",
            "svi": {
                "geom": "templates/fiat/svi/CDC_svi_2020.gpkg",
                "field_name": "SVI",
            },
            "bfe": {
                "geom": "bfe/bfe.geojson",
                "table": "bfe/bfe.csv",
                "field_name": "bfe",
            },
            "aggregation": [
                {
                    "name": "aggr_lvl_1",
                    "file": "templates/fiat/aggregation_areas/aggr_lvl_1.geojson",
                    "field_name": "name",
                    "equity": {
                        "census_data": "templates/fiat/equity/census_data_aggr_lvl_1.csv",
                        "percapitaincome_label": "PerCapitaIncome",
                        "totalpopulation_label": "TotalPopulation",
                    },
                },
                {
                    "name": "aggr_lvl_2",
                    "file": "templates/fiat/aggregation_areas/aggr_lvl_2.geojson",
                    "field_name": "name",
                    "equity": {
                        "census_data": "templates/fiat/equity/census_data_aggr_lvl_2.csv",
                        "percapitaincome_label": "PerCapitaIncome",
                        "totalpopulation_label": "TotalPopulation",
                    },
                },
            ],
        },
        "river": [
            {
                "name": "cooper",
                "description": "Cooper River",
                "x_coordinate": 595546.3,
                "y_coordinate": 3675590.6,
                "mean_discharge": {"value": 5000.0, "units": "cfs"},
            }
        ],
        "obs_station": {
            "name": 8665530,
            "description": "Charleston Cooper River Entrance",
            "ID": 8665530,
            "lat": 32.78,
            "lon": -79.9233,
            "mllw": {"value": 0.0, "units": "meters"},
            "mhhw": {"value": 1.757, "units": "meters"},
            "localdatum": {"value": 0.957, "units": "meters"},
            "msl": {"value": 0.890, "units": "meters"},
        },
        "obs_point": [
            {
                "name": "ashley_river",
                "description": "Ashley River - James Island Expy",
                "lat": 32.7765,
                "lon": -79.9543,
            },
            {
                "name": 8665530,
                "description": "Charleston Cooper River Entrance",
                "ID": 8665530,
                "lat": 32.78,
                "lon": -79.9233,
            },
        ],
        "benefits": {
            "current_year": 2023,
            "current_projection": "current",
            "baseline_strategy": "no_measures",
            "event_set": "test_set",
        },
        "scs": {"file": "scs_rainfall.csv", "type": "type_3"},
        "standard_objects": {...},
    }
    yield config_values


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


def test_loadFile_tomlFile_setAttrs(test_sites, test_dict):
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

    to_save = create_site_config()
    to_save.save(file_path)

    loaded = Site.load_file(file_path)

    assert to_save == loaded
