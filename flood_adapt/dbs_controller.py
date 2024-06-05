import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import xarray as xr
from cht_cyclones.tropical_cyclone import TropicalCyclone
from geopandas import GeoDataFrame

from flood_adapt.dbs_classes.dbs_benefit import DbsBenefit
from flood_adapt.dbs_classes.dbs_event import DbsEvent
from flood_adapt.dbs_classes.dbs_measure import DbsMeasure
from flood_adapt.dbs_classes.dbs_projection import DbsProjection
from flood_adapt.dbs_classes.dbs_scenario import DbsScenario
from flood_adapt.dbs_classes.dbs_static import DbsStatic
from flood_adapt.dbs_classes.dbs_strategy import DbsStrategy
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site


class Database(IDatabase):
    """Implementation of IDatabase class that holds the site information and has methods to get static data info, and all the input information.

    Additionally it can manipulate (add, edit, copy and delete) any of the objects in the input.
    """

    _instance = None

    database_path: Union[str, os.PathLike]
    database_name: str
    _init_done: bool = False

    input_path: Path
    static_path: Path
    output_path: Path

    _site: ISite

    static_sfincs_model: SfincsAdapter

    _events: DbsEvent
    _scenarios: DbsScenario
    _strategies: DbsStrategy
    _measures: DbsMeasure
    _projections: DbsProjection
    _benefits: DbsBenefit

    def __new__(cls, *args, **kwargs):
        if not cls._instance:  # Singleton pattern
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        database_path: Union[str, os.PathLike] = None,
        database_name: str = None,
    ) -> None:
        """
        Initialize the DatabaseController object.

        Parameters
        ----------
        database_path : Union[str, os.PathLike]
            The path to the database root
        database_name : str
            The name of the database.
        -----
        """
        if database_path is None or database_name is None:
            if not self._init_done:
                raise ValueError(
                    """Database path and name must be provided for the first initialization. 
                    To do this, run api_static.read_database(database_path, site_name) first."""
                )
            else:
                return  # Skip re-initialization

        if (
            self._init_done
            and self.database_path == database_path
            and self.database_name == database_name
        ):
            return  # Skip re-initialization

        # If the database is not initialized, or a new path or name is provided, (re-)initialize
        logging.info(
            f"(Re-)Initializing database to {database_name} at {database_path}"
        )
        self.database_path = database_path
        self.database_name = database_name

        self.input_path = Path(database_path / database_name / "input")
        self.static_path = Path(database_path / database_name / "static")
        self.output_path = Path(database_path / database_name / "output")

        self._site = Site.load_file(self.static_path / "site" / "site.toml")

        # Get the static sfincs model
        sfincs_path = self.static_path.joinpath(
            "templates", self._site.attrs.sfincs.overland_model
        )
        self.static_sfincs_model = SfincsAdapter(
            model_root=sfincs_path, site=self._site
        )

        # Initialize the different database objects
        self._static = DbsStatic(self)
        self._events = DbsEvent(self)
        self._scenarios = DbsScenario(self)
        self._strategies = DbsStrategy(self)
        self._measures = DbsMeasure(self)
        self._projections = DbsProjection(self)
        self._benefits = DbsBenefit(self)

        self._init_done = True

    # Property methods
    @property
    def site(self) -> ISite:
        return self._site

    @property
    def static(self) -> DbsStatic:
        return self._static

    @property
    def events(self) -> DbsEvent:
        return self._events

    @property
    def scenarios(self) -> DbsScenario:
        return self._scenarios

    @property
    def strategies(self) -> DbsStrategy:
        return self._strategies

    @property
    def measures(self) -> DbsMeasure:
        return self._measures

    @property
    def projections(self) -> DbsProjection:
        return self._projections

    @property
    def benefits(self) -> DbsBenefit:
        return self._benefits

    # General methods
    def get_aggregation_areas(self) -> dict:
        """Get a list of the aggregation areas that are provided in the site configuration.
        These are expected to much the ones in the FIAT model

        Returns
        -------
        list[GeoDataFrame]
            list of geodataframes with the polygons defining the aggregation areas
        """
        aggregation_areas = {}
        for aggr_dict in self.site.attrs.fiat.aggregation:
            aggregation_areas[aggr_dict.name] = gpd.read_file(
                self.input_path.parent / "static" / "site" / aggr_dict.file,
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

    def get_model_boundary(self) -> GeoDataFrame:
        """Get the model boundary from the SFINCS model"""
        bnd = self.static_sfincs_model.get_model_boundary()
        return bnd

    def get_model_grid(self) -> QuadtreeGrid:
        """Get the model grid from the SFINCS model

        Returns
        -------
        QuadtreeGrid
            The model grid
        """
        grid = self.static_sfincs_model.get_model_grid()
        return grid

    def get_obs_points(self) -> GeoDataFrame:
        """Get the observation points from the flood hazard model"""
        if self.site.attrs.obs_point is not None:
            obs_points = self.site.attrs.obs_point
            names = []
            descriptions = []
            lat = []
            lon = []
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

    def get_static_map(self, path: Union[str, Path]) -> gpd.GeoDataFrame:
        """Get a map from the static folder

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
        full_path = self.static_path / path
        if full_path.is_file():
            return gpd.read_file(full_path, engine="pyogrio").to_crs(4326)

        # If the file is not found, throw an error
        raise FileNotFoundError(f"File {full_path} not found")

    def get_slr_scn_names(self) -> list:
        input_file = self.input_path.parent.joinpath("static", "slr", "slr.csv")
        df = pd.read_csv(input_file)
        return df.columns[2:].to_list()

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
            self.input_path.parent.joinpath(
                "static", "green_infra_table", "green_infra_lookup_table.csv"
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

    def interp_slr(self, slr_scenario: str, year: float) -> float:
        r"""Interpolate SLR value and reference it to the SLR reference year from the site toml.

        Parameters
        ----------
        slr_scenario : str
            SLR scenario name from the coulmn names in static\slr\slr.csv
        year : float
            year to evaluate

        Returns
        -------
        float
            _description_

        Raises
        ------
        ValueError
            if the reference year is outside of the time range in the slr.csv file
        ValueError
            if the year to evaluate is outside of the time range in the slr.csv file
        """
        input_file = self.input_path.parent.joinpath("static", "slr", "slr.csv")
        df = pd.read_csv(input_file)
        if year > df["year"].max() or year < df["year"].min():
            raise ValueError(
                "The selected year is outside the range of the available SLR scenarios"
            )
        else:
            slr = np.interp(year, df["year"], df[slr_scenario])
            ref_year = self.site.attrs.slr.relative_to_year
            if ref_year > df["year"].max() or ref_year < df["year"].min():
                raise ValueError(
                    f"The reference year {ref_year} is outside the range of the available SLR scenarios"
                )
            else:
                ref_slr = np.interp(ref_year, df["year"], df[slr_scenario])
                new_slr = UnitfulLength(
                    value=slr - ref_slr,
                    units=df["units"][0],
                )
                gui_units = self.site.attrs.gui.default_length_units
                return np.round(new_slr.convert(gui_units), decimals=2)

    # TODO: should probably be moved to frontend
    def plot_slr_scenarios(self) -> str:
        input_file = self.input_path.parent.joinpath("static", "slr", "slr.csv")
        df = pd.read_csv(input_file)
        ncolors = len(df.columns) - 2
        try:
            units = df["units"].iloc[0]
            units = UnitTypesLength(units)
        except ValueError(
            "Column " "units" " in input/static/slr/slr.csv file missing."
        ) as e:
            print(e)

        try:
            if "year" in df.columns:
                df = df.rename(columns={"year": "Year"})
            elif "Year" in df.columns:
                pass
        except ValueError(
            "Column " "year" " in input/static/slr/slr.csv file missing."
        ) as e:
            print(e)

        ref_year = self.site.attrs.slr.relative_to_year
        if ref_year > df["Year"].max() or ref_year < df["Year"].min():
            raise ValueError(
                f"The reference year {ref_year} is outside the range of the available SLR scenarios"
            )
        else:
            scenarios = self._static.get_slr_scn_names()
            for scn in scenarios:
                ref_slr = np.interp(ref_year, df["Year"], df[scn])
                df[scn] -= ref_slr

        df = df.drop(columns="units").melt(id_vars=["Year"]).reset_index(drop=True)
        # convert to units used in GUI
        slr_current_units = UnitfulLength(value=1.0, units=units)
        conversion_factor = slr_current_units.convert(
            self.site.attrs.gui.default_length_units
        )
        df.iloc[:, -1] = (conversion_factor * df.iloc[:, -1]).round(decimals=2)

        # rename column names that will be shown in html
        df = df.rename(
            columns={
                "variable": "Scenario",
                "value": "Sea level rise [{}]".format(
                    self.site.attrs.gui.default_length_units
                ),
            }
        )

        colors = px.colors.sample_colorscale(
            "rainbow", [n / (ncolors - 1) for n in range(ncolors)]
        )
        fig = px.line(
            df,
            x="Year",
            y=f"Sea level rise [{self.site.attrs.gui.default_length_units}]",
            color="Scenario",
            color_discrete_sequence=colors,
        )

        # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

        fig.update_layout(
            autosize=False,
            height=100 * 1.2,
            width=280 * 1.3,
            margin={"r": 0, "l": 0, "b": 0, "t": 0},
            font={"size": 10, "color": "black", "family": "Arial"},
            title_font={"size": 10, "color": "black", "family": "Arial"},
            legend_font={"size": 10, "color": "black", "family": "Arial"},
            legend_grouptitlefont={"size": 10, "color": "black", "family": "Arial"},
            legend={"entrywidthmode": "fraction", "entrywidth": 0.2},
            yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            xaxis_title=None,
            xaxis_range=[ref_year, df["Year"].max()],
            legend_title=None,
            # paper_bgcolor="#3A3A3A",
            # plot_bgcolor="#131313",
        )

        # write html to results folder
        output_loc = self.input_path.parent.joinpath("temp", "slr.html")
        output_loc.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(output_loc)
        return str(output_loc)

    def plot_wl(self, event: IEvent, input_wl_df: pd.DataFrame = None) -> str:
        if (
            event["template"] == "Synthetic"
            or event["template"] == "Historical_nearshore"
        ):
            gui_units = self.site.attrs.gui.default_length_units
            if event["template"] == "Synthetic":
                event["name"] = "temp_event"
                temp_event = Synthetic.load_dict(event)
                temp_event.add_tide_and_surge_ts()
                wl_df = temp_event.tide_surge_ts
                wl_df.index = np.arange(
                    -temp_event.attrs.time.duration_before_t0,
                    temp_event.attrs.time.duration_after_t0 + 1 / 3600,
                    1 / 6,
                )
                xlim1 = -temp_event.attrs.time.duration_before_t0
                xlim2 = temp_event.attrs.time.duration_after_t0
            elif event["template"] == "Historical_nearshore":
                wl_df = input_wl_df
                xlim1 = pd.to_datetime(event["time"]["start_time"])
                xlim2 = pd.to_datetime(event["time"]["end_time"])

            # Plot actual thing
            fig = px.line(
                wl_df + self.site.attrs.water_level.msl.height.convert(gui_units)
            )

            # plot reference water levels
            fig.add_hline(
                y=self.site.attrs.water_level.msl.height.convert(gui_units),
                line_dash="dash",
                line_color="#000000",
                annotation_text="MSL",
                annotation_position="bottom right",
            )
            if self.site.attrs.water_level.other:
                for wl_ref in self.site.attrs.water_level.other:
                    fig.add_hline(
                        y=wl_ref.height.convert(gui_units),
                        line_dash="dash",
                        line_color="#3ec97c",
                        annotation_text=wl_ref.name,
                        annotation_position="bottom right",
                    )

            fig.update_layout(
                autosize=False,
                height=100 * 2,
                width=280 * 2,
                margin={"r": 0, "l": 0, "b": 0, "t": 0},
                font={"size": 10, "color": "black", "family": "Arial"},
                title_font={"size": 10, "color": "black", "family": "Arial"},
                legend=None,
                xaxis_title="Time",
                yaxis_title=f"Water level [{gui_units}]",
                yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                showlegend=False,
                xaxis={"range": [xlim1, xlim2]},
                # paper_bgcolor="#3A3A3A",
                # plot_bgcolor="#131313",
            )

            # write html to results folder
            output_loc = self.input_path.parent.joinpath("temp", "timeseries.html")
            output_loc.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(output_loc)
            return str(output_loc)

        else:
            NotImplementedError(
                "Plotting only available for timeseries and synthetic tide + surge."
            )
            return str("")

    def plot_rainfall(
        self, event: IEvent, input_rainfall_df: pd.DataFrame = None
    ) -> (
        str
    ):  # I think we need a separate function for the different timeseries when we also want to plot multiple rivers
        if (
            event["rainfall"]["source"] == "shape"
            or event["rainfall"]["source"] == "timeseries"
        ):
            temp_event = EventFactory.get_event(event["template"]).load_dict(event)
            if (
                temp_event.attrs.rainfall.source == "shape"
                and temp_event.attrs.rainfall.shape_type == "scs"
            ):
                scsfile = self.input_path.parent.joinpath(
                    "static", "scs", self.site.attrs.scs.file
                )
                if scsfile.is_file() is False:
                    ValueError(
                        "Information about SCS file and type missing in site.toml"
                    )
                temp_event.add_rainfall_ts(
                    scsfile=scsfile, scstype=self.site.attrs.scs.type
                )
                df = temp_event.rain_ts
            elif event["rainfall"]["source"] == "timeseries":
                df = input_rainfall_df
            else:
                temp_event.add_rainfall_ts()
                df = temp_event.rain_ts

            # set timing relative to T0 if event is synthetic
            if event["template"] == "Synthetic":
                df.index = np.arange(
                    -temp_event.attrs.time.duration_before_t0,
                    temp_event.attrs.time.duration_after_t0 + 1 / 3600,
                    1 / 6,
                )
                xlim1 = -temp_event.attrs.time.duration_before_t0
                xlim2 = temp_event.attrs.time.duration_after_t0
            else:
                xlim1 = pd.to_datetime(event["time"]["start_time"])
                xlim2 = pd.to_datetime(event["time"]["end_time"])

            # Plot actual thing
            fig = px.line(data_frame=df)

            # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

            fig.update_layout(
                autosize=False,
                height=100 * 2,
                width=280 * 2,
                margin={"r": 0, "l": 0, "b": 0, "t": 0},
                font={"size": 10, "color": "black", "family": "Arial"},
                title_font={"size": 10, "color": "black", "family": "Arial"},
                legend=None,
                yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                xaxis_title={"text": "Time"},
                yaxis_title={
                    "text": f"Rainfall intensity [{self.site.attrs.gui.default_intensity_units}]"
                },
                showlegend=False,
                xaxis={"range": [xlim1, xlim2]},
                # paper_bgcolor="#3A3A3A",
                # plot_bgcolor="#131313",
            )

            # write html to results folder
            output_loc = self.input_path.parent.joinpath("temp", "timeseries.html")
            output_loc.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(output_loc)
            return str(output_loc)

        else:
            NotImplementedError(
                "Plotting only available for timeseries and shape type rainfall."
            )
            return str("")

    def plot_river(
        self, event: IEvent, input_river_df: list[pd.DataFrame]
    ) -> (
        str
    ):  # I think we need a separate function for the different timeseries when we also want to plot multiple rivers
        temp_event = EventFactory.get_event(event["template"]).load_dict(event)
        event_dir = self.input_path.joinpath("events", temp_event.attrs.name)
        temp_event.add_dis_ts(event_dir, self.site.attrs.river, input_river_df)
        river_descriptions = [i.description for i in self.site.attrs.river]
        river_names = [i.description for i in self.site.attrs.river]
        river_descriptions = np.where(
            river_descriptions is None, river_names, river_descriptions
        ).tolist()
        df = temp_event.dis_df

        # set timing relative to T0 if event is synthetic
        if event["template"] == "Synthetic":
            df.index = np.arange(
                -temp_event.attrs.time.duration_before_t0,
                temp_event.attrs.time.duration_after_t0 + 1 / 3600,
                1 / 6,
            )
            xlim1 = -temp_event.attrs.time.duration_before_t0
            xlim2 = temp_event.attrs.time.duration_after_t0
        else:
            xlim1 = pd.to_datetime(event["time"]["start_time"])
            xlim2 = pd.to_datetime(event["time"]["end_time"])

        # Plot actual thing
        fig = go.Figure()
        for ii, col in enumerate(df.columns):
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    name=river_descriptions[ii],
                    mode="lines",
                )
            )

        # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

        fig.update_layout(
            autosize=False,
            height=100 * 2,
            width=280 * 2,
            margin={"r": 0, "l": 0, "b": 0, "t": 0},
            font={"size": 10, "color": "black", "family": "Arial"},
            title_font={"size": 10, "color": "black", "family": "Arial"},
            yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            xaxis_title={"text": "Time"},
            yaxis_title={
                "text": f"River discharge [{self.site.attrs.gui.default_discharge_units}]"
            },
            xaxis={"range": [xlim1, xlim2]},
            # paper_bgcolor="#3A3A3A",
            # plot_bgcolor="#131313",
        )

        # write html to results folder
        output_loc = self.input_path.parent.joinpath("temp", "timeseries.html")
        output_loc.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(output_loc)
        return str(output_loc)

    def plot_wind(
        self, event: IEvent, input_wind_df: pd.DataFrame = None
    ) -> (
        str
    ):  # I think we need a separate function for the different timeseries when we also want to plot multiple rivers
        if event["wind"]["source"] == "timeseries":
            df = input_wind_df

            # Plot actual thing
            # Create figure with secondary y-axis
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # Add traces
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[1],
                    name="Wind speed",
                    mode="lines",
                ),
                secondary_y=False,
            )

            fig.add_trace(
                go.Scatter(x=df.index, y=df[2], name="Wind direction", mode="markers"),
                secondary_y=True,
            )

            # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})
            # Set y-axes titles
            fig.update_yaxes(
                title_text=f"Wind speed [{self.site.attrs.gui.default_velocity_units}]",
                secondary_y=False,
            )
            fig.update_yaxes(title_text="Wind direction [deg N]", secondary_y=True)
            fig.update_layout(
                autosize=False,
                height=100 * 2,
                width=280 * 2,
                margin={"r": 0, "l": 0, "b": 0, "t": 0},
                font={"size": 10, "color": "black", "family": "Arial"},
                title_font={"size": 10, "color": "black", "family": "Arial"},
                legend=None,
                yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                xaxis_title={"text": "Time"},
                showlegend=False,
                # paper_bgcolor="#3A3A3A",
                # plot_bgcolor="#131313",
            )

            # write html to results folder
            output_loc = self.input_path.parent.joinpath("temp", "timeseries.html")
            output_loc.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(output_loc)
            return str(output_loc)

        else:
            NotImplementedError(
                "Plotting only available for timeseries and shape type wind."
            )
            return str("")

    def get_buildings(self) -> GeoDataFrame:
        """Get the building footprints from the FIAT model.
        This should only be the buildings excluding any other types (e.g., roads)
        The parameters non_building_names in the site config is used for that

        Returns
        -------
        GeoDataFrame
            building footprints with all the FIAT columns
        """
        # use hydromt-fiat to load the fiat model
        fm = FiatModel(
            root=self.input_path.parent / "static" / "templates" / "fiat",
            mode="r",
        )
        fm.read()
        buildings = fm.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self.site.attrs.fiat.non_building_names,
            return_gdf=True,
        )

        return buildings

    def get_property_types(self) -> list:
        """_summary_

        Returns
        -------
        list
            _description_
        """
        # use hydromt-fiat to load the fiat model
        fm = FiatModel(
            root=self.input_path.parent / "static" / "templates" / "fiat",
            mode="r",
        )
        fm.read()
        types = fm.exposure.get_primary_object_type()
        for name in self.site.attrs.fiat.non_building_names:
            if name in types:
                types.remove(name)
        # Add "all" type for using as identifier
        types.append("all")
        return types

    def write_to_csv(self, name: str, event: IEvent, df: pd.DataFrame):
        df.to_csv(
            Path(self.input_path, "events", event.attrs.name, f"{name}.csv"),
            header=False,
        )

    def write_cyc(self, event: IEvent, track: TropicalCyclone):
        cyc_file = (
            self.input_path
            / "events"
            / event.attrs.name
            / f"{event.attrs.track_name}.cyc"
        )
        # cht_cyclone function to write TropicalCyclone as .cyc file
        track.write_track(filename=cyc_file, fmt="ddb_cyc")

    def check_benefit_scenarios(self, benefit: IBenefit) -> pd.DataFrame:
        """Return a dataframe with the scenarios needed for this benefit assessment run.

        Parameters
        ----------
        benefit : IBenefit
        """
        return benefit.check_scenarios()

    def create_benefit_scenarios(self, benefit: IBenefit) -> None:
        """Create any scenarios that are needed for the (cost-)benefit assessment and are not there already.

        Parameters
        ----------
        benefit : IBenefit
        """
        # If the check has not been run yet, do it now
        if not hasattr(benefit, "scenarios"):
            benefit.check_scenarios()

        # Iterate through the scenarios needed and create them if not existing
        for index, row in benefit.scenarios.iterrows():
            if row["scenario created"] == "No":
                scenario_dict = {}
                scenario_dict["event"] = row["event"]
                scenario_dict["projection"] = row["projection"]
                scenario_dict["strategy"] = row["strategy"]
                scenario_dict["name"] = "_".join(
                    [row["projection"], row["event"], row["strategy"]]
                )

                scenario_obj = Scenario.load_dict(scenario_dict, self.input_path)

                self._scenarios.save(scenario_obj)

        # Update the scenarios check
        benefit.check_scenarios()

    def run_benefit(self, benefit_name: Union[str, list[str]]) -> None:
        """Run a (cost-)benefit analysis.

        Parameters
        ----------
        benefit_name : Union[str, list[str]]
            name(s) of the benefits to run.
        """
        if not isinstance(benefit_name, list):
            benefit_name = [benefit_name]
        for name in benefit_name:
            benefit = self._benefits.get(name)
            benefit.run_cost_benefit()

    def update(self) -> None:
        self.projections = self._projections.list_objects()
        self.events = self._events.list_objects()
        self.measures = self._measures.list_objects()
        self.strategies = self._strategies.list_objects()
        self.scenarios = self._scenarios.list_objects()
        self.benefits = self._benefits.list_objects()

    def get_outputs(self) -> dict[str, Any]:
        """Return a dictionary with info on the outputs that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'path', 'last_modification_date' and "finished" info
        """
        all_scenarios = pd.DataFrame(self._scenarios.list_objects())
        if len(all_scenarios) > 0:
            df = all_scenarios[all_scenarios["finished"]]
        else:
            df = all_scenarios
        finished = df.drop(columns="finished").reset_index(drop=True)
        return finished.to_dict()

    def get_topobathy_path(self) -> str:
        """Return the path of the topobathy tiles in order to create flood maps with water level maps.

        Returns
        -------
        str
            path to topobathy tiles
        """
        path = self.input_path.parent.joinpath("static", "dem", "tiles", "topobathy")
        return str(path)

    def get_index_path(self) -> str:
        """Return the path of the index tiles which are used to connect each water level cell with the topobathy tiles.

        Returns
        -------
        str
            path to index tiles
        """
        path = self.input_path.parent.joinpath("static", "dem", "tiles", "indices")
        return str(path)

    def get_depth_conversion(self) -> float:
        """Return the flood depth conversion that is need in the gui to plot the flood map.

        Returns
        -------
        float
            conversion factor
        """
        # Get conresion factor need to get from the sfincs units to the gui units
        units = UnitfulLength(value=1, units=self.site.attrs.gui.default_length_units)
        unit_cor = units.convert(new_units="meters")

        return unit_cor

    def get_max_water_level(
        self,
        scenario_name: str,
        return_period: int = None,
    ) -> np.array:
        """Return an array with the maximum water levels during an event.

        Parameters
        ----------
        scenario_name : str
            name of scenario
        return_period : int, optional
            return period in years, by default None

        Returns
        -------
        np.array
            2D map of maximum water levels
        """
        # If single event read with hydromt-sfincs
        if not return_period:
            map_path = self.input_path.parent.joinpath(
                "output",
                "Scenarios",
                scenario_name,
                "Flooding",
                "max_water_level_map.nc",
            )
            map = xr.open_dataarray(map_path)

            zsmax = map.to_numpy()

        else:
            file_path = self.input_path.parent.joinpath(
                "output",
                "Scenarios",
                scenario_name,
                "Flooding",
                f"RP_{return_period:04d}_maps.nc",
            )
            zsmax = xr.open_dataset(file_path)["risk_map"][:, :].to_numpy().T
        return zsmax

    def get_fiat_footprints(self, scenario_name: str) -> GeoDataFrame:
        """Return a geodataframe of the impacts at the footprint level.

        Parameters
        ----------
        scenario_name : str
            name of scenario

        Returns
        -------
        GeoDataFrame
            impacts at footprint level
        """
        out_path = self.input_path.parent.joinpath(
            "output", "Scenarios", scenario_name, "Impacts"
        )
        footprints = out_path / f"Impacts_building_footprints_{scenario_name}.gpkg"
        gdf = gpd.read_file(footprints, engine="pyogrio")
        gdf = gdf.to_crs(4326)
        return gdf

    def get_roads(self, scenario_name: str) -> GeoDataFrame:
        """Return a geodataframe of the impacts at roads.

        Parameters
        ----------
        scenario_name : str
            name of scenario

        Returns
        -------
        GeoDataFrame
            Impacts at roads
        """
        out_path = self.input_path.parent.joinpath(
            "output", "Scenarios", scenario_name, "Impacts"
        )
        roads = out_path / f"Impacts_roads_{scenario_name}.gpkg"
        gdf = gpd.read_file(roads, engine="pyogrio")
        gdf = gdf.to_crs(4326)
        return gdf

    def get_aggregation(self, scenario_name: str) -> dict[GeoDataFrame]:
        """Get a dictionary with the aggregated damages as geodataframes.

        Parameters
        ----------
        scenario_name : str
            name of the scenario

        Returns
        -------
        dict[GeoDataFrame]
            dictionary with aggregated damages per aggregation type
        """
        out_path = self.input_path.parent.joinpath(
            "output", "Scenarios", scenario_name, "Impacts"
        )
        gdfs = {}
        for aggr_area in out_path.glob(f"Impacts_aggregated_{scenario_name}_*.gpkg"):
            label = aggr_area.stem.split(f"{scenario_name}_")[-1]
            gdfs[label] = gpd.read_file(aggr_area, engine="pyogrio")
            gdfs[label] = gdfs[label].to_crs(4326)
        return gdfs

    def get_aggregation_benefits(self, benefit_name: str) -> dict[GeoDataFrame]:
        """Get a dictionary with the aggregated benefits as geodataframes.

        Parameters
        ----------
        benefit_name : str
            name of the benefit analysis

        Returns
        -------
        dict[GeoDataFrame]
            dictionary with aggregated benefits per aggregation type
        """
        out_path = self.input_path.parent.joinpath(
            "output",
            "Benefits",
            benefit_name,
        )
        gdfs = {}
        for aggr_area in out_path.glob("benefits_*.gpkg"):
            label = aggr_area.stem.split("benefits_")[-1]
            gdfs[label] = gpd.read_file(aggr_area, engine="pyogrio")
            gdfs[label] = gdfs[label].to_crs(4326)
        return gdfs

    def get_object_list(self, object_type: str) -> dict[str, Any]:
        """Get a dictionary with all the toml paths and last modification dates that exist in the database that correspond to object_type.

        Parameters
        ----------
        object_type : str
            Can be 'projections', 'events', 'measures', 'strategies' or 'scenarios'

        Returns
        -------
        dict[str, Any]
            Includes 'path' and 'last_modification_date' info
        """
        paths = [
            path / f"{path.name}.toml"
            for path in list((self.input_path / object_type).iterdir())
        ]
        last_modification_date = [
            datetime.fromtimestamp(file.stat().st_mtime) for file in paths
        ]

        objects = {
            "path": paths,
            "last_modification_date": last_modification_date,
        }

        return objects

    def has_run_hazard(self, scenario_name: str) -> None:
        """Check if there is already a simulation that has the exact same hazard component.

        If yes that is copied to avoid running the hazard model twice.

        Parameters
        ----------
        scenario_name : str
            name of the scenario to check if needs to be rerun for hazard
        """
        scenario = self._scenarios.get(scenario_name)

        simulations = list(
            self.input_path.parent.joinpath("output", "Scenarios").glob("*")
        )

        scns_simulated = [self._scenarios.get(sim.name) for sim in simulations]

        for scn in scns_simulated:
            if scn.direct_impacts.hazard == scenario.direct_impacts.hazard:
                path_0 = self.input_path.parent.joinpath(
                    "output", "Scenarios", scn.attrs.name, "Flooding"
                )
                path_new = self.input_path.parent.joinpath(
                    "output", "Scenarios", scenario.attrs.name, "Flooding"
                )
                if (
                    scn.direct_impacts.hazard.has_run_check()
                ):  # only copy results if the hazard model has actually finished and skip simulation folders
                    shutil.copytree(
                        path_0,
                        path_new,
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("simulations"),
                    )
                    print(
                        f"Hazard simulation is used from the '{scn.attrs.name}' scenario"
                    )

    def run_scenario(self, scenario_name: Union[str, list[str]]) -> None:
        """Run a scenario hazard and impacts.

        Parameters
        ----------
        scenario_name : Union[str, list[str]]
            name(s) of the scenarios to run.

        Raises
        ------
        RuntimeError
            If an error occurs while running one of the scenarios
        """
        if not isinstance(scenario_name, list):
            scenario_name = [scenario_name]

        errors = []
        for scn in scenario_name:
            try:
                self.has_run_hazard(scn)
                scenario = self.scenarios.get(scn)
                scenario.run()
            except RuntimeError as e:
                if "SFINCS model failed to run." in str(e):
                    errors.append(str(scn))

        if errors:
            raise RuntimeError(
                "SFincs model failed to run for the following scenarios: "
                + ", ".join(errors)
                + ". Check the logs for more information."
            )
