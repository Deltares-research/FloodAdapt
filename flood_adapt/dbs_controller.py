import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone
from geopandas import GeoDataFrame
from plotly.express import line
from plotly.express.colors import sample_colorscale
from plotly.graph_objects import Figure, Scatter
from plotly.subplots import make_subplots
from xarray import open_dataarray, open_dataset

from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.config import Settings
from flood_adapt.dbs_classes.dbs_benefit import DbsBenefit
from flood_adapt.dbs_classes.dbs_event import DbsEvent
from flood_adapt.dbs_classes.dbs_measure import DbsMeasure
from flood_adapt.dbs_classes.dbs_projection import DbsProjection
from flood_adapt.dbs_classes.dbs_scenario import DbsScenario
from flood_adapt.dbs_classes.dbs_static import DbsStatic
from flood_adapt.dbs_classes.dbs_strategy import DbsStrategy
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.utils import finished_file_exists


class Database(IDatabase):
    """Implementation of IDatabase class that holds the site information and has methods to get static data info, and all the input information.

    Additionally it can manipulate (add, edit, copy and delete) any of the objects in the input.
    """

    _instance = None

    database_path: Union[str, os.PathLike]
    database_name: str
    _init_done: bool = False

    base_path: Path
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
        self._logger = FloodAdaptLogging.getLogger(__name__)
        self._logger.info(
            f"(Re-)Initializing database to {database_name} at {database_path}"
        )
        self.database_path = database_path
        self.database_name = database_name

        # Set the paths
        self.base_path = Path(database_path) / database_name
        self.input_path = self.base_path / "input"
        self.static_path = self.base_path / "static"
        self.output_path = self.base_path / "output"

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

        # Delete any unfinished/crashed scenario output
        self.cleanup()

        self._init_done = True

    def shutdown(self):
        """Explicitly shut down the database controller singleton and clear all data stored in its memory."""
        self.__class__._instance = None
        self._init_done = False
        self.database_path = None
        self.database_name = None

        self.base_path = None
        self.input_path = None
        self.static_path = None
        self.output_path = None
        self._site = None

        self.static_sfincs_model = None
        self._logger = None
        self._static = None
        self._events = None
        self._scenarios = None
        self._strategies = None
        self._measures = None
        self._projections = None
        self._benefits = None

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
        input_file = self.input_path.parent.joinpath(
            "static", self.site.attrs.slr.scenarios.file
        )
        df = pd.read_csv(input_file)
        if year > df["year"].max() or year < df["year"].min():
            raise ValueError(
                "The selected year is outside the range of the available SLR scenarios"
            )
        else:
            slr = np.interp(year, df["year"], df[slr_scenario])
            ref_year = self.site.attrs.slr.scenarios.relative_to_year
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
        input_file = self.input_path.parent.joinpath(
            "static", self.site.attrs.slr.scenarios.file
        )
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

        ref_year = self.site.attrs.slr.scenarios.relative_to_year
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

        colors = sample_colorscale(
            "rainbow", [n / (ncolors - 1) for n in range(ncolors)]
        )
        fig = line(
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

    def plot_wl(self, event: IEvent | dict, input_wl_df: pd.DataFrame = None) -> str:
        if isinstance(event, dict):
            event = EventFactory.get_event(event["template"]).load_dict(event)

        match event.attrs.template:
            case "Synthetic":
                event.add_tide_and_surge_ts()
                wl_df = event.tide_surge_ts
                wl_df.index = np.arange(
                    -event.attrs.time.duration_before_t0,
                    event.attrs.time.duration_after_t0 + 1 / 3600,
                    1 / 6,
                )
                xlim1 = -event.attrs.time.duration_before_t0
                xlim2 = event.attrs.time.duration_after_t0
            case "Historical_nearshore":
                if input_wl_df is None:
                    self._logger.warning(
                        "No water level data provided to plot for historical nearshore event, continuing..."
                    )
                    return ""
                wl_df = input_wl_df
                xlim1 = pd.to_datetime(event.attrs.time.start_time)
                xlim2 = pd.to_datetime(event.attrs.time.end_time)
            case _:
                raise NotImplementedError(
                    "Plotting only available for timeseries and synthetic tide + surge."
                )
                return str("")

        gui_units = self.site.attrs.gui.default_length_units

        # Plot actual thing
        fig = line(wl_df + self.site.attrs.water_level.msl.height.convert(gui_units))

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

    def plot_rainfall(
        self, event: IEvent | dict, input_rainfall_df: pd.DataFrame = None
    ) -> str:  # I think we need a separate function for the different timeseries when we also want to plot multiple rivers
        if isinstance(event, dict):
            event = EventFactory.get_event(event["template"]).load_dict(event)

        match event.attrs.rainfall.source:
            case "shape":
                scs_file, scs_type = None, None
                if event.attrs.rainfall.shape_type == "scs":
                    if self.site.attrs.scs is None:
                        ValueError(
                            "Information about SCS file and type missing in site.toml"
                        )
                    else:
                        scs_file = self.input_path.parent.joinpath(
                            "static", "scs", self.site.attrs.scs.file
                        )
                        scs_type = self.site.attrs.scs.type
                event.add_rainfall_ts(scsfile=scs_file, scstype=scs_type)
                df = event.rain_ts
            case "timeseries":
                if input_rainfall_df is None:
                    self._logger.warning(
                        "No rainfall data provided to plot for timeseries event, continuing..."
                    )
                    return ""
                df = input_rainfall_df
            case "constant":
                time = pd.date_range(
                    start=event.attrs.time.start_time,
                    end=event.attrs.time.end_time,
                    freq="H",
                )
                df = pd.DataFrame(
                    index=time,
                    data={
                        "intensity": [event.attrs.rainfall.constant_intensity.value]
                        * len(time),
                    },
                )
            case _:
                self._logger.warning(
                    "Plotting only available for timeseries, shape and constant rainfall."
                )
                return ""

        # set timing relative to T0 if event is synthetic
        if event.attrs.template == "Synthetic":
            xlim1 = -event.attrs.time.duration_before_t0
            xlim2 = event.attrs.time.duration_after_t0 + 1 / 3600
            step = (xlim2 - xlim1) / df.index.size
            df.index = np.arange(
                xlim1,
                xlim2,
                step,
            )
        else:
            xlim1 = pd.to_datetime(event.attrs.time.start_time)
            xlim2 = pd.to_datetime(event.attrs.time.end_time)

        # Plot actual thing
        fig = line(data_frame=df)

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

    def plot_river(
        self, event: IEvent | dict, input_river_df: list[pd.DataFrame]
    ) -> str:  # I think we need a separate function for the different timeseries when we also want to plot multiple rivers
        if isinstance(event, dict):
            event = EventFactory.get_event(event["template"]).load_dict(event)

        if any(df.empty for df in input_river_df) and any(
            river.source == "timeseries" for river in event.attrs.river
        ):
            self._logger.warning(
                "No/incomplete river discharge data provided to plot for timeseries event, continuing..."
            )
            return ""

        event_dir = self.events.get_database_path().joinpath(event.attrs.name)
        event.add_dis_ts(event_dir, self.site.attrs.river, input_river_df)
        river_descriptions = [i.description for i in self.site.attrs.river]
        river_names = [i.description for i in self.site.attrs.river]
        river_descriptions = np.where(
            river_descriptions is None, river_names, river_descriptions
        ).tolist()
        df = event.dis_df

        # set timing relative to T0 if event is synthetic
        if event.attrs.template == "Synthetic":
            df.index = np.arange(
                -event.attrs.time.duration_before_t0,
                event.attrs.time.duration_after_t0 + 1 / 3600,
                1 / 6,
            )
            xlim1 = -event.attrs.time.duration_before_t0
            xlim2 = event.attrs.time.duration_after_t0
        else:
            xlim1 = pd.to_datetime(event.attrs.time.start_time)
            xlim2 = pd.to_datetime(event.attrs.time.end_time)

        # Plot actual thing
        fig = Figure()
        for ii, col in enumerate(df.columns):
            fig.add_trace(
                Scatter(
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
        self, event: IEvent | dict, input_wind_df: pd.DataFrame = None
    ) -> str:  # I think we need a separate function for the different timeseries when we also want to plot multiple rivers
        if isinstance(event, dict):
            event = EventFactory.get_event(event["template"]).load_dict(event)

        if event.attrs.wind.source not in ["timeseries", "constant"]:
            self._logger.warning(
                "Plotting only available for timeseries and constant type wind."
            )
            return ""

        match event.attrs.wind.source:
            case "timeseries":
                if input_wind_df is None:
                    self._logger.warning(
                        "No wind data provided to plot for timeseries event, continuing..."
                    )
                    return ""
                df = input_wind_df
                df = df.rename(
                    columns={1: "speed", 2: "direction"}
                )  # rename column names for consistency
            case "constant":
                time = pd.date_range(
                    start=event.attrs.time.start_time,
                    end=event.attrs.time.end_time,
                    freq="H",
                )
                df = pd.DataFrame(
                    index=time,
                    data={
                        "speed": [event.attrs.wind.constant_speed.value] * len(time),
                        "direction": [event.attrs.wind.constant_direction.value]
                        * len(time),
                    },
                )
            case _:
                self._logger.warning(
                    "Plotting only available for timeseries and constant type wind."
                )
                return ""

        # Plot actual thing
        # Create figure with secondary y-axis

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add traces
        fig.add_trace(
            Scatter(
                x=df.index,
                y=df["speed"],
                name="Wind speed",
                mode="lines",
            ),
            secondary_y=False,
        )

        fig.add_trace(
            Scatter(
                x=df.index, y=df["direction"], name="Wind direction", mode="markers"
            ),
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

    def write_to_csv(self, name: str, event: IEvent, df: pd.DataFrame):
        df.to_csv(
            self.events.get_database_path().joinpath(event.attrs.name, f"{name}.csv"),
            header=False,
        )

    def write_cyc(self, event: IEvent, track: TropicalCyclone):
        cyc_file = (
            self.events.get_database_path()
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
                # Check if scenario already exists (because it was created before in the loop)
                try:
                    self.scenarios.save(scenario_obj)
                except ValueError as e:
                    if "name is already used" not in str(e):
                        # some other error was raised, so we re-raise it
                        raise e
                    # otherwise, if it already exists and we dont need to save it, we can just continue

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
            map_path = self.scenarios.get_database_path(get_input_path=False).joinpath(
                scenario_name,
                "Flooding",
                "max_water_level_map.nc",
            )
            map = open_dataarray(map_path)

            zsmax = map.to_numpy()

        else:
            file_path = self.scenarios.get_database_path(get_input_path=False).joinpath(
                scenario_name,
                "Flooding",
                f"RP_{return_period:04d}_maps.nc",
            )
            zsmax = open_dataset(file_path)["risk_map"][:, :].to_numpy().T
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
        out_path = self.scenarios.get_database_path(get_input_path=False).joinpath(
            scenario_name, "Impacts"
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
        out_path = self.scenarios.get_database_path(get_input_path=False).joinpath(
            scenario_name, "Impacts"
        )
        roads = out_path / f"Impacts_roads_{scenario_name}.gpkg"
        gdf = gpd.read_file(roads, engine="pyogrio")
        gdf = gdf.to_crs(4326)
        return gdf

    def get_aggregation(self, scenario_name: str) -> dict[str, gpd.GeoDataFrame]:
        """Return a dictionary with the aggregated impacts as geodataframes.

        Parameters
        ----------
        scenario_name : str
            name of the scenario

        Returns
        -------
        dict[GeoDataFrame]
            dictionary with aggregated damages per aggregation type
        """
        out_path = self.scenarios.get_database_path(get_input_path=False).joinpath(
            scenario_name, "Impacts"
        )
        gdfs = {}
        for aggr_area in out_path.glob(f"Impacts_aggregated_{scenario_name}_*.gpkg"):
            label = aggr_area.stem.split(f"{scenario_name}_")[-1]
            gdfs[label] = gpd.read_file(aggr_area, engine="pyogrio")
            gdfs[label] = gdfs[label].to_crs(4326)
        return gdfs

    def get_aggregation_benefits(self, benefit_name: str) -> dict[str, GeoDataFrame]:
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
        out_path = self.benefits.get_database_path(get_input_path=False).joinpath(
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

        # Dont do anything if the hazard model has already been run in itself
        if scenario.direct_impacts.hazard.has_run_check():
            return

        simulations = list(
            self.input_path.parent.joinpath("output", "Scenarios").glob("*")
        )

        scns_simulated = [self._scenarios.get(sim.name) for sim in simulations]

        for scn in scns_simulated:
            if scn.direct_impacts.hazard == scenario.direct_impacts.hazard:
                path_0 = self.scenarios.get_database_path(
                    get_input_path=False
                ).joinpath(scn.attrs.name, "Flooding")
                path_new = self.scenarios.get_database_path(
                    get_input_path=False
                ).joinpath(scenario.attrs.name, "Flooding")
                if scn.direct_impacts.hazard.has_run_check():  # only copy results if the hazard model has actually finished and skip simulation folders
                    shutil.copytree(
                        path_0,
                        path_new,
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("simulations"),
                    )
                    self._logger.info(
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

    def cleanup(self) -> None:
        """
        Remove corrupted scenario output.

        This method removes any scenario output that:
            - is corrupted due to unfinished runs
            - does not have a corresponding input

        """
        if not Settings().delete_crashed_runs:
            return

        scn_input_path = self.scenarios.get_database_path()
        scn_output_path = self.scenarios.get_database_path(get_input_path=False)
        if not scn_output_path.is_dir():
            return

        input_scenarios = [
            (scn_input_path / dir).resolve() for dir in os.listdir(scn_input_path)
        ]
        output_scenarios = [
            (scn_output_path / dir).resolve() for dir in os.listdir(scn_output_path)
        ]

        for dir in output_scenarios:
            if dir.name not in [path.name for path in input_scenarios]:
                # input was deleted
                shutil.rmtree(dir)
            elif not finished_file_exists(dir):
                # corrupted output due to unfinished run
                shutil.rmtree(dir)
