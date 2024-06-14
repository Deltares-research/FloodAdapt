from pathlib import Path
from typing import Any, Callable, Tuple, Union

import geopandas as gpd
import pandas as pd
from geopandas import GeoDataFrame
from hydromt_fiat.fiat import FiatModel
from hydromt_sfincs.quadtree import QuadtreeGrid

from flood_adapt.object_model.interface.database import IDatabase


def cache_method_wrapper(func: Callable) -> Callable:
    def wrapper(self, *args: Tuple[Any], **kwargs: dict[str, Any]) -> Any:
        if func.__name__ not in self._cached_data:
            self._cached_data[func.__name__] = {}

        args_key = (
            str(args) + str(sorted(kwargs.items())) if args or kwargs else "no_args"
        )
        if args_key in self._cached_data[func.__name__]:
            return self._cached_data[func.__name__][args_key]

        result = func(self, *args, **kwargs)
        self._cached_data[func.__name__][args_key] = result

        return result

    return wrapper


class DbsStatic:

    _cached_data: dict[str, Any] = {}
    _database: IDatabase = None

    def __init__(self, database: IDatabase):
        """Initialize any necessary attributes."""
        self._database = database

    @cache_method_wrapper
    def get_aggregation_areas(self) -> dict:
        """Get a list of the aggregation areas that are provided in the site configuration.

        These are expected to much the ones in the FIAT model.

        Returns
        -------
        list[GeoDataFrame]
            list of geodataframes with the polygons defining the aggregation areas
        """
        aggregation_areas = {}
        for aggr_dict in self._database.site.attrs.fiat.aggregation:
            aggregation_areas[aggr_dict.name] = gpd.read_file(
                self._database.static_path / "site" / aggr_dict.file,
                engine="pyogrio",
            ).to_crs(4326)
            # Use always the same column name for name labels
            aggregation_areas[aggr_dict.name] = aggregation_areas[
                aggr_dict.name
            ].rename(columns={aggr_dict.field_name: "name"})
            # Make sure they are ordered alphabetically
            aggregation_areas[aggr_dict.name].sort_values(by="name").reset_index(
                drop=True
            )
        return aggregation_areas

    @cache_method_wrapper
    def get_model_boundary(self) -> GeoDataFrame:
        """Get the model boundary from the SFINCS model."""
        bnd = self._database.static_sfincs_model.get_model_boundary()
        return bnd

    @cache_method_wrapper
    def get_model_grid(self) -> QuadtreeGrid:
        """Get the model grid from the SFINCS model.

        Returns
        -------
        QuadtreeGrid
            The model grid
        """
        grid = self._database.static_sfincs_model.get_model_grid()
        return grid

    @cache_method_wrapper
    def get_obs_points(self) -> GeoDataFrame:
        """Get the observation points from the flood hazard model."""
        names = []
        descriptions = []
        lat = []
        lon = []
        if self._database.site.attrs.obs_point is not None:
            obs_points = self._database.site.attrs.obs_point
            for pt in obs_points:
                names.append(pt.name)
                descriptions.append(pt.description)
                lat.append(pt.lat)
                lon.append(pt.lon)

        # create GeoDataFrame from obs_points in site file
        df = pd.DataFrame({"name": names, "description": descriptions})
        # TODO: make crs flexible and add this as a parameter to site.toml?
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326"
        )
        return gdf

    @cache_method_wrapper
    def get_static_map(self, path: Union[str, Path]) -> gpd.GeoDataFrame:
        """Get a map from the static folder.

        Parameters
        ----------
        path : Union[str, Path]
            Path to the map relative to the static folder

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with the map in crs 4326

        Raises
        ------
        FileNotFoundError
            If the file is not found
        """
        # Read the map
        full_path = self._database.static_path / path
        if full_path.is_file():
            return gpd.read_file(full_path, engine="pyogrio").to_crs(4326)

        # If the file is not found, throw an error
        raise FileNotFoundError(f"File {full_path} not found")

    @cache_method_wrapper
    def get_slr_scn_names(self) -> list:
        """Get the names of the sea level rise scenarios from the file provided.

        Returns
        -------
        list
            List of scenario names
        """
        input_file = self._database.static_path.joinpath(
            self._database.site.attrs.slr.scenarios.file
        )
        df = pd.read_csv(input_file)
        names = df.columns[2:].to_list()
        return names

    @cache_method_wrapper
    def get_green_infra_table(self, measure_type: str) -> pd.DataFrame:
        """Return a table with different types of green infrastructure measures and their infiltration depths.

        This is read by a csv file in the database.

        Returns
        -------
        pd.DataFrame
            Table with values
        """
        # Read file from database
        df = pd.read_csv(
            self._database.static_path.joinpath(
                "green_infra_table", "green_infra_lookup_table.csv"
            )
        )

        # Get column with values
        val_name = "Infiltration depth"
        col_name = [name for name in df.columns if val_name in name][0]
        if not col_name:
            raise KeyError(f"A column with a name containing {val_name} was not found!")

        # Get list of types per measure
        df["types"] = [
            [x.strip() for x in row["types"].split(",")] for i, row in df.iterrows()
        ]

        # Show specific values based on measure type
        inds = [i for i, row in df.iterrows() if measure_type in row["types"]]
        df = df.drop(columns="types").iloc[inds, :]

        return df

    @cache_method_wrapper
    def get_buildings(self) -> GeoDataFrame:
        """Get the building footprints from the FIAT model.

        This should only be the buildings excluding any other types (e.g., roads)
        The parameters non_building_names in the site config is used for that.

        Returns
        -------
        GeoDataFrame
            building footprints with all the FIAT columns
        """
        # use hydromt-fiat to load the fiat model
        fm = FiatModel(
            root=self._database.static_path / "templates" / "fiat",
            mode="r",
        )
        fm.read()
        buildings = fm.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self._database.site.attrs.fiat.non_building_names,
            return_gdf=True,
        )

        del fm

        return buildings

    @cache_method_wrapper
    def get_property_types(self) -> list:
        """_summary_.

        Returns
        -------
        list
            _description_
        """
        # use hydromt-fiat to load the fiat model
        fm = FiatModel(
            root=self._database.static_path / "templates" / "fiat",
            mode="r",
        )
        fm.read()
        types = fm.exposure.get_primary_object_type()
        for name in self._database.site.attrs.fiat.non_building_names:
            if name in types:
                types.remove(name)
        # Add "all" type for using as identifier
        types.append("all")

        del fm

        return types
