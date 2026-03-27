import functools
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from hydromt.writers import write_yaml
from hydromt_fiat import FIATModel
from hydromt_fiat.data import fetch_data
from hydromt_fiat.utils import (
    DAMAGE,
    GEOM,
    MODEL_TYPE,
)
from hydromt_sfincs import SfincsModel
from requests.exceptions import ConnectionError, RequestException
from shapely import Point


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def cache_dir(test_data_dir: Path) -> Path:
    return test_data_dir / ".cache"


@pytest.fixture(scope="session")
def region(test_data_dir: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(test_data_dir / "region.geojson")
    assert len(gdf) == 1
    assert gdf.crs is not None
    return gdf


@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    return np.random.default_rng(seed=42)


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


## FIAT
@pytest.fixture(scope="session")
@check_connection
def fiat_global_data_catalog_yml(cache_dir: Path) -> Path:
    data_path = fetch_data("global-data", retries=1, cache_dir=cache_dir)
    assert Path(data_path, "exposure", "jrc_damage_values.csv").is_file()
    p = Path(data_path, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def fake_fiat_data_catalog_yml(
    cache_dir: Path, region: gpd.GeoDataFrame, rng: np.random.Generator
) -> Path:
    """Create fake FIAT buildings data within the SFINCS region."""
    fake_dir = cache_dir / "fake_fiat_data"
    fake_dir.mkdir(parents=True, exist_ok=True)
    buildings_dir = fake_dir / "buildings"
    buildings_dir.mkdir(exist_ok=True)

    # Generate random points inside the sfincs region
    bounds = region.total_bounds
    n_buildings = 20
    points = []
    while len(points) < n_buildings:
        x = rng.uniform(bounds[0], bounds[2])
        y = rng.uniform(bounds[1], bounds[3])
        pt = Point(x, y)
        if region.contains(pt).any():
            points.append(pt)

    building_types = ["woonfunctie", "industriefunctie", "kantoorfunctie"]
    types = rng.choice(building_types, n_buildings)
    buildings = gpd.GeoDataFrame(
        {"gebruiksdoel": types},
        geometry=points,
        crs=region.crs,
    )
    buildings.to_file(buildings_dir / "buildings.fgb", driver="FlatGeobuf")

    # Create buildings link CSV
    link = pd.DataFrame(
        {
            "gebruiksdoel": ["woonfunctie", "industriefunctie", "kantoorfunctie"],
            "object_type": ["residential", "industrial", "commercial"],
            "count": [10, 5, 5],
        }
    )
    link.to_csv(buildings_dir / "buildings-jrc_map.csv", index=False)

    # Write data catalog YAML
    catalog = {
        "buildings": {
            "data_type": "GeoDataFrame",
            "uri": "buildings/buildings.fgb",
            "driver": {
                "name": "pyogrio",
                "filesystem": "local",
            },
            "metadata": {
                "crs": region.crs.to_epsg(),
            },
        },
        "buildings_link": {
            "data_type": "DataFrame",
            "uri": "buildings/buildings-jrc_map.csv",
            "driver": {
                "name": "pandas",
                "filesystem": "local",
            },
        },
    }
    catalog_path = fake_dir / "data_catalog.yml"
    write_yaml(catalog_path, catalog)

    return catalog_path


@pytest.fixture(scope="session")
def build_fiat_model(
    cache_dir: Path,
    fake_fiat_data_catalog_yml: Path,
    fiat_global_data_catalog_yml: Path,
    region: gpd.GeoDataFrame,
):
    ## HydroMT-FIAT
    # Setup the model
    model = FIATModel(
        root=cache_dir / "test_models" / "fiat",
        mode="w+",
        data_libs=[fake_fiat_data_catalog_yml, fiat_global_data_catalog_yml],
    )

    # Add model type and region
    model.setup_config(**{MODEL_TYPE: GEOM})
    model.setup_region(region)

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
def build_sfincs_model_regular(
    cache_dir: Path, sfincs_data_yml: Path, region: gpd.GeoDataFrame
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
        region={"geom": region},
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
    model.mask.create_active(zmin=-3)
    model.mask.create_boundary(btype="waterlevel", zmax=-3)
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
    cache_dir: Path, sfincs_data_yml: Path, region: gpd.GeoDataFrame
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
        region={"geom": region},
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
    model.quadtree_mask.create_active(zmin=-3)
    model.quadtree_mask.create_boundary(btype="waterlevel", zmax=-3)
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
