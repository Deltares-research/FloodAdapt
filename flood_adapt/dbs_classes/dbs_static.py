from pathlib import Path
from typing import Any, Callable, Optional, Tuple, Union

import geopandas as gpd
import pandas as pd
from cht_cyclones.cyclone_track_database import CycloneTrackDatabase

from flood_adapt.adapter.docker import FiatContainer, SfincsContainer
from flood_adapt.adapter.fiat_adapter import FiatAdapter
from flood_adapt.adapter.interface.hazard_adapter import IHazardAdapter
from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.dbs_classes.interface.static import IDbsStatic
from flood_adapt.misc.exceptions import ConfigError, DatabaseError


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


class DbsStatic(IDbsStatic):
    _cached_data: dict[str, Any] = {}
    _database: IDatabase

    _fiat_container: FiatContainer
    _sfincs_container: SfincsContainer

    def __init__(
        self,
        database: IDatabase,
    ) -> None:
        """Initialize any necessary attributes."""
        self._database = database
        self._settings = database._settings

        # Note that Python objects to interact with the containers are initialized here.
        # not the Docker containers themselves.
        # The containers are initialized by calling the ``start_docker`` method.
        # The containers are destroyed by calling the ``stop_docker`` method.
        self._fiat_container = FiatContainer(version=self._settings.fiat_version)
        self._sfincs_container = SfincsContainer(version=self._settings.sfincs_version)

    def load_static_data(self):
        """Read data into the cache.

        This is used to read data from the database and store it in the cache.
        """
        self.get_aggregation_areas()
        self.get_model_boundary()
        self.get_model_grid()
        self.get_obs_points()
        if self._database.site.sfincs.slr_scenarios is not None:
            self.get_slr_scn_names()
        self.get_buildings()
        self.get_property_types()

    @cache_method_wrapper
    def get_aggregation_areas(self) -> dict[str, gpd.GeoDataFrame]:
        """Get a list of the aggregation areas that are provided in the site configuration.

        These are expected to much the ones in the FIAT model.

        Returns
        -------
        list[gpd.GeoDataFrame]
            list of gpd.GeoDataFrames with the polygons defining the aggregation areas
        """
        aggregation_areas = {}
        for aggr_dict in self._database.site.fiat.config.aggregation:
            aggregation_areas[aggr_dict.name] = gpd.read_file(
                self._database.static_path / aggr_dict.file,
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
    def get_aggregation_area_by_type_and_name(
        self, area_type: str, area_name: str
    ) -> gpd.GeoDataFrame:
        areas = self.get_aggregation_areas()
        if area_type not in areas:
            raise DatabaseError(f"Aggregation area type '{area_type}' does not exist.")
        gdf = areas[area_type]
        if area_name not in gdf["name"].to_numpy():
            raise DatabaseError(
                f"Aggregation area '{area_name}' does not exist in type '{area_type}'."
            )
        return gdf.loc[gdf["name"] == area_name, :]

    @cache_method_wrapper
    def get_model_boundary(self) -> gpd.GeoDataFrame:
        """Get the model boundary from the SFINCS model."""
        bnd = self.get_overland_sfincs_model().get_model_boundary()
        bnd = bnd[["geometry"]]
        return bnd

    @cache_method_wrapper
    def get_model_grid(self):
        """Get the model grid from the SFINCS model.

        Returns
        -------
        QuadtreeGrid
            The model grid
        """
        grid = self.get_overland_sfincs_model().get_model_grid()
        return grid

    @cache_method_wrapper
    def get_obs_points(self) -> Optional[gpd.GeoDataFrame]:
        """Get the observation points from the flood hazard model."""
        if self._database.site.sfincs.obs_point is None:
            return None

        names = []
        descriptions = []
        lat = []
        lon = []
        for pt in self._database.site.sfincs.obs_point:
            names.append(pt.name)
            descriptions.append(pt.description)
            lat.append(pt.lat)
            lon.append(pt.lon)

        # create gpd.GeoDataFrame from obs_points in site file
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
            gpd.GeoDataFrame with the map in crs 4326

        Raises
        ------
        DatabaseError
            If the file is not found
        """
        # Read the map
        full_path = self._database.static_path / path
        if not full_path.is_file():
            raise DatabaseError(f"File {full_path} not found")
        return gpd.read_file(full_path, engine="pyogrio").to_crs(4326)

    @cache_method_wrapper
    def get_slr_scn_names(self) -> list:
        """Get the names of the sea level rise scenarios from the file provided.

        Returns
        -------
        list
            List of scenario names
        """
        if self._database.site.sfincs.slr_scenarios is None:
            raise ConfigError("No sea level rise scenarios defined in the site config.")
        input_file = self._database.static_path.joinpath(
            self._database.site.sfincs.slr_scenarios.file
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
    def get_buildings(self) -> gpd.GeoDataFrame:
        """Get the building footprints from the FIAT model.

        This should only be the buildings excluding any other types (e.g., roads)
        The parameters non_building_names in the site config is used for that.

        Returns
        -------
        gpd.GeoDataFrame
            building footprints with all the FIAT columns
        """
        return self.get_fiat_model().get_buildings()

    @cache_method_wrapper
    def get_property_types(self) -> list:
        """_summary_.

        Returns
        -------
        list
            _description_
        """
        return self.get_fiat_model().get_property_types()

    def get_hazard_models(self) -> list[IHazardAdapter]:
        """Get the hazard models from the database.

        Returns
        -------
        list[HazardAdapter]
            List of hazard models
        """
        return [self.get_overland_sfincs_model()]

    def get_impact_models(self) -> list[IImpactAdapter]:
        """Get the impact models from the database.

        Returns
        -------
        list[ImpactAdapter]
            List of impact models
        """
        return [self.get_fiat_model()]

    def get_overland_sfincs_model(self) -> SfincsAdapter:
        """Get the template offshore SFINCS model."""
        overland_path = (
            self._database.static_path
            / "templates"
            / self._database.site.sfincs.config.overland_model.name
        )
        with SfincsAdapter(
            model_root=overland_path, container=self._sfincs_container
        ) as overland_model:
            return overland_model

    def get_offshore_sfincs_model(self) -> SfincsAdapter:
        """Get the template overland Sfincs model."""
        if self._database.site.sfincs.config.offshore_model is None:
            raise ConfigError("No offshore model defined in the site configuration.")

        offshore_path = (
            self._database.static_path
            / "templates"
            / self._database.site.sfincs.config.offshore_model.name
        )
        with SfincsAdapter(
            model_root=offshore_path, container=self._sfincs_container
        ) as offshore_model:
            return offshore_model

    def get_fiat_model(self) -> FiatAdapter:
        """Get the path to the FIAT model."""
        if self._database.site.fiat is None:
            raise ConfigError("No FIAT model defined in the site configuration.")
        template_path = self._database.static_path / "templates" / "fiat"

        with FiatAdapter(
            model_root=template_path,
            config=self._database.site.fiat.config,
            exe_path=self._settings.fiat_bin_path,
            delete_crashed_runs=self._settings.delete_crashed_runs,
            config_base_path=self._database.static_path,
            container=self._fiat_container,
        ) as fm:
            return fm

    def get_fiat_container(self) -> FiatContainer:
        """Get the Docker container for FIAT, if defined."""
        return self._fiat_container

    def get_sfincs_container(self) -> SfincsContainer:
        """Get the Docker container for SFINCS, if defined."""
        return self._sfincs_container

    @cache_method_wrapper
    def get_cyclone_track_database(self) -> CycloneTrackDatabase:
        if self._database.site.sfincs.cyclone_track_database is None:
            raise ConfigError(
                "No cyclone track database defined in the site configuration."
            )
        database_file = (
            self._database.static_path
            / "cyclone_track_database"
            / self._database.site.sfincs.cyclone_track_database.file
        ).as_posix()
        return CycloneTrackDatabase("ibtracs", file_name=database_file)

    def clear(self):
        """Clear the cache."""
        self._cached_data.clear()

    def start_docker(self) -> None:
        if self._settings.manual_docker_containers:
            return

        self._sfincs_container.start(self._database.base_path)
        self._fiat_container.start(self._database.base_path)

    def stop_docker(self) -> None:
        if self._settings.manual_docker_containers:
            return

        self._sfincs_container.stop()
        self._fiat_container.stop()
