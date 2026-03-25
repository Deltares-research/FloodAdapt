import functools
import shutil
from pathlib import Path

import geopandas as gpd
import pytest
from hydromt_fiat import FIATModel
from hydromt_fiat.data import fetch_data
from hydromt_fiat.utils import (
    DAMAGE,
    GEOM,
    MODEL_TYPE,
)
from hydromt_sfincs import SfincsModel
from requests.exceptions import ConnectionError, RequestException


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def cache_dir(test_data_dir: Path) -> Path:
    return test_data_dir / ".cache"


## FIAT
def check_connection(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        try:
            r = fn(*args, **kwargs)
        except RequestException as e:
            raise ConnectionError(
                "Failed to download hydromt test data, check your connection"
            ) from e
        else:
            return r

    return inner


@pytest.fixture(scope="session")
@check_connection
def fiat_buildings_path(cache_dir: Path) -> Path:
    p = fetch_data("test-build-data", retries=1, cache_dir=cache_dir)
    assert Path(p, "buildings", "buildings.fgb").is_file()
    return p


@pytest.fixture(scope="session")
def fiat_data_catalog_yml(fiat_buildings_path: Path) -> Path:
    p = Path(fiat_buildings_path, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
@check_connection
def fiat_global_data_path(cache_dir: Path) -> Path:
    p = fetch_data("global-data", retries=1, cache_dir=cache_dir)
    assert Path(p, "exposure", "jrc_damage_values.csv").is_file()
    return p


@pytest.fixture(scope="session")
def fiat_global_data_catalog_yml(fiat_global_data_path: Path) -> Path:
    p = Path(fiat_global_data_path, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def fiat_region_geojson(fiat_buildings_path: Path) -> Path:
    p = Path(fiat_buildings_path, "region_small.geojson")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def fiat_region(fiat_region_geojson: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(fiat_region_geojson)
    assert len(gdf) == 1
    return gdf


@pytest.fixture(scope="session")
def build_fiat_model(
    cache_dir: Path,
    fiat_data_catalog_yml: Path,
    fiat_global_data_catalog_yml: Path,
    fiat_region: gpd.GeoDataFrame,
):
    ## HydroMT-FIAT
    # Setup the model
    model = FIATModel(
        root=cache_dir / "test_models" / "fiat",
        mode="w+",
        data_libs=[fiat_data_catalog_yml, fiat_global_data_catalog_yml],
    )

    # Add model type and region
    model.setup_config(**{MODEL_TYPE: GEOM})
    model.setup_region(fiat_region)

    # Setup the vulnerability
    model.vulnerability.setup(
        "jrc_curves",
        "jrc_curves_link",
        unit="m",
        continent="europe",
    )

    # Setup the exposure geometry data
    model.exposure_geoms.setup(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
        exposure_type_fill="unknown",
    )
    model.exposure_geoms.setup_max_damage(
        exposure_name="buildings",
        exposure_type=DAMAGE,
        exposure_cost_table_fname="jrc_damage",
        country="Netherlands",  # Select the correct row from the data
    )
    # Needed for flood calculations
    model.exposure_geoms.update_column(
        exposure_name="buildings",
        columns=["ref", "method"],
        values=[0, "centroid"],
    )

    # Write the model
    model.write()
    return model


## SFINCS
@pytest.fixture(scope="session")
def sfincs_data_yml(test_data_dir: Path) -> Path:
    p = test_data_dir / "sfincs_data.yml"
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def sfincs_region_geojson(test_data_dir: Path) -> Path:
    p = test_data_dir / "sfincs_region.geojson"
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def sfincs_region(sfincs_region_geojson: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(sfincs_region_geojson)
    assert len(gdf) == 1
    return gdf


@pytest.fixture(scope="session")
def build_sfincs_model_regular(
    cache_dir: Path, sfincs_data_yml: Path, sfincs_region: gpd.GeoDataFrame
):
    root = cache_dir / "test_models" / "sfincs" / "regular"
    if root.exists():
        shutil.rmtree(root)

    model = SfincsModel(
        root=str(root),
        mode="w+",
        data_libs=["artifact_data", sfincs_data_yml.as_posix()],
    )
    model.config.update(
        tref="20100201 000000",
        tstart="20100205 000000",
        tstop="20100207 000000",
        dtmapout=86400.0,
        dthisout=86400.0,
        tspinup=0.0,
        dtrstout=0.0,
    )
    model.grid.create_from_region(
        region={"geom": sfincs_region},
        res=150,
        crs="utm",
        rotated=True,
    )
    model.elevation.create(
        elevation_list=[
            {"elevation": "merit_hydro", "zmin": 0.001},
            {"elevation": "gebco"},
        ]
    )
    model.mask.create_active(zmin=-5)
    model.mask.create_boundary(btype="waterlevel", zmax=-1)
    model.subgrid.create(
        elevation_list=[
            {"elevation": "merit_hydro", "zmin": 0.001},
            {"elevation": "gebco"},
        ],
        roughness_list=[
            {"lulc": "vito_2015", "reclass_table": "vito_mapping"},
        ],
        write_dep_tif=True,
        nr_subgrid_pixels=6,
        nr_levels=8,
    )
    model.observation_points.create(locations="observations")
    model.cross_sections.create(locations="observation_lines")
    model.thin_dams.create(locations="weir")
    model.weirs.create(locations="weir")
    model.drainage_structures.create(locations="drainage")
    model.rivers.create_river_inflow(
        hydrography="merit_hydro",
        buffer=100,
        river_upa=10,
        river_len=1000,
        keep_rivers_geom=True,
    )
    model.write()
    return model


@pytest.fixture(scope="session")
def build_sfincs_model_quadtree(
    cache_dir: Path, sfincs_data_yml: Path, sfincs_region: gpd.GeoDataFrame
):
    root = cache_dir / "test_models" / "sfincs" / "quadtree"
    if root.exists():
        shutil.rmtree(root)

    model = SfincsModel(
        root=str(root),
        mode="w+",
        data_libs=["artifact_data", sfincs_data_yml.as_posix()],
    )
    model.config.update(
        tref="20100201 000000",
        tstart="20100205 000000",
        tstop="20100207 000000",
        dtmapout=86400.0,
        dthisout=86400.0,
        tspinup=0.0,
        dtrstout=0.0,
    )
    model.quadtree_grid.create_from_region(
        region={"geom": sfincs_region},
        res=150,
        crs="utm",
        rotated=True,
    )
    model.quadtree_elevation.create(
        elevation_list=[
            {"elevation": "merit_hydro", "zmin": 0.001},
            {"elevation": "gebco"},
        ]
    )
    model.quadtree_mask.create_active(zmin=-5)
    model.quadtree_mask.create_boundary(btype="waterlevel", zmax=-1)
    model.quadtree_subgrid.create(
        elevation_list=[
            {"elevation": "merit_hydro", "zmin": 0.001},
            {"elevation": "gebco"},
        ],
        roughness_list=[
            {"lulc": "vito_2015", "reclass_table": "vito_mapping"},
        ],
        write_dep_tif=True,
        nr_subgrid_pixels=6,
        nr_levels=8,
    )
    model.observation_points.create(locations="observations")
    model.cross_sections.create(locations="observation_lines")
    model.thin_dams.create(locations="weir")
    model.weirs.create(locations="weir")
    model.drainage_structures.create(locations="drainage")
    model.rivers.create_river_inflow(
        hydrography="merit_hydro",
        buffer=100,
        river_upa=10,
        river_len=1000,
        keep_rivers_geom=True,
    )
    model.write()
    return model


def test_models(
    build_fiat_model: FIATModel,
    build_sfincs_model_regular: SfincsModel,
    build_sfincs_model_quadtree: SfincsModel,
):
    """Test that the models can be built and written without errors."""
    assert build_fiat_model is not None
    assert build_sfincs_model_regular is not None
    assert build_sfincs_model_quadtree is not None
