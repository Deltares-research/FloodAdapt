import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
from geopandas import GeoDataFrame
from hydromt_fiat.fiat import FiatModel
from hydromt_sfincs import SfincsModel

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength
from flood_adapt.object_model.measure_factory import MeasureFactory
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.strategy import Strategy


class Database(IDatabase):
    """Implementation of IDatabase class that holds the site information and has methods
    to get static data info, and all the input information.
    Additionally it can manipulate (add, edit, copy and delete) any of the objects in the input
    """

    input_path: Path
    site: ISite

    def __init__(self, database_path: Union[str, os.PathLike], site_name: str) -> None:
        """Database is initialized with a path and a site name

        Parameters
        ----------
        database_path : Union[str, os.PathLike]
            database path
        site_name : str
            site name (same as in the folder structure)
        """
        self.input_path = Path(database_path) / site_name / "input"
        self.site = Site.load_file(
            Path(database_path) / site_name / "static" / "site" / "site.toml"
        )
        # self.update()

    # General methods
    def get_aggregation_areas(self) -> list[GeoDataFrame]:
        """Get a list of the aggregation areas that are provided in the site configuration.
        These are expected to much the ones in the FIAT model

        Returns
        -------
        list[GeoDataFrame]
            list of geodataframes with the polygons defining the aggregation areas
        """
        aggregation_areas = [
            gpd.read_file(
                self.input_path.parent / "static" / "site" / aggr_dict.file
            ).to_crs(4326)
            for aggr_dict in self.site.attrs.fiat.aggregation
        ]
        # Make sure they are ordered alphabetically
        aggregation_areas = [
            aggregation_areas.sort_values(
                by=self.site.attrs.fiat.aggregation[i].field_name
            ).reset_index(drop=True)
            for i, aggregation_areas in enumerate(aggregation_areas)
        ]
        return aggregation_areas

    def get_slr_scn_names(self) -> list:
        input_file = self.input_path.parent.joinpath("static", "slr", "slr.csv")
        df = pd.read_csv(input_file)
        return df.columns[2:].to_list()

    def interp_slr(self, slr_scenario: str, year: float) -> float:
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

        df = df.drop(columns="units").melt(id_vars=["Year"]).reset_index(drop=True)
        # convert to units used in GUI
        slr_current_units = UnitfulLength(value=df.iloc[0, -1], units=units)
        gui_units = self.site.attrs.gui.default_length_units
        slr_gui_units = slr_current_units.convert(gui_units)
        conversion_factor = slr_gui_units / slr_current_units.value
        df.iloc[:, -1] = conversion_factor * df.iloc[:, -1]

        # rename column names that will be shown in html
        df = df.rename(
            columns={
                "variable": "Scenario",
                "value": "Sea level rise [{}]".format(gui_units),
            }
        )

        colors = px.colors.sample_colorscale(
            "rainbow", [n / (ncolors - 1) for n in range(ncolors)]
        )
        fig = px.line(
            df,
            x="Year",
            y=f"Sea level rise [{gui_units}]",
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
            if event["template"] == "Synthetic":
                temp_event = Synthetic.load_dict(event)
                temp_event.add_tide_and_surge_ts()
                wl_df = temp_event.tide_surge_ts
                wl_df.index = np.arange(
                    -temp_event.attrs.time.duration_before_t0,
                    temp_event.attrs.time.duration_after_t0 + 1 / 3600,
                    1 / 6,
                )
            elif event["template"] == "Historical_nearshore":
                wl_df = input_wl_df

            # convert to units used in GUI
            wl_df["Time"] = wl_df.index
            wl_current_units = UnitfulLength(
                value=float(wl_df.iloc[0, 0]), units="meters"
            )
            gui_units = self.site.attrs.gui.default_length_units
            wl_gui_units = wl_current_units.convert(gui_units)
            if wl_current_units.value == 0:
                conversion_factor = 1
            else:
                conversion_factor = wl_gui_units / wl_current_units.value
            wl_df[1] = conversion_factor * wl_df[1]
            wl_df = wl_df.rename(
                columns={1: f"Water level (tide + surge) [{gui_units}]"}
            )

            # Plot actual thing
            fig = px.line(
                wl_df,
                x="Time",
                y=f"Water level (tide + surge) [{gui_units}]",
            )

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
                # paper_bgcolor="#3A3A3A",
                # plot_bgcolor="#131313",
            )

            # write html to results folder
            output_loc = self.input_path.parent.joinpath("temp", "wl.html")
            output_loc.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(output_loc)
            return str(output_loc)

        else:
            NotImplementedError(
                "Plotting only available for Synthetic and Historical Nearshore event."
            )

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
            primary_object_type=["ALL"],
            non_building_names=self.site.attrs.fiat.non_building_names,
            return_gdf=True,
        )

        return buildings

    # Measure methods
    def get_measure(self, name: str) -> IMeasure:
        """Get the respective measure object using the name of the measure.

        Parameters
        ----------
        name : str
            name of the measure

        Returns
        -------
        IMeasure
            object of one of the measure types (e.g., IElevate)
        """
        measure_path = self.input_path / "measures" / name / f"{name}.toml"
        measure = MeasureFactory.get_measure_object(measure_path)
        return measure

    def save_measure(self, measure: IMeasure) -> None:
        """Saves a measure object in the database.

        Parameters
        ----------
        measure : IMeasure
            object of one of the measure types (e.g., IElevate)

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of measures should be unique.
        """
        names = self.get_measures()["name"]
        if measure.attrs.name in names:
            raise ValueError(
                f"'{measure.attrs.name}' name is already used by another measure. Choose a different name"
            )
        else:
            # TODO: how to save the extra files? e.g., polygons
            (self.input_path / "measures" / measure.attrs.name).mkdir()
            measure.save(
                self.input_path
                / "measures"
                / measure.attrs.name
                / f"{measure.attrs.name}.toml"
            )

    def edit_measure(self, measure: IMeasure):
        """Edits an already existing measure in the database.

        Parameters
        ----------
        measure : IMeasure
            object of one of the measure types (e.g., IElevate)
        """
        # TODO should you be able to edit a measure that is already used in a strategy?
        measure.save(
            self.input_path
            / "measures"
            / measure.attrs.name
            / f"{measure.attrs.name}.toml"
        )

    def delete_measure(self, name: str):
        """Deletes an already existing measure in the database.

        Parameters
        ----------
        name : str
            name of the measure

        Raises
        ------
        ValueError
            Raise error if measure to be deleted is already used in a strategy.
        """
        # TODO check strategies that use a measure
        strategies = [
            Strategy.load_file(path) for path in self.get_strategies()["path"]
        ]
        used_strategy = [
            name in measures
            for measures in [strategy.attrs.measures for strategy in strategies]
        ]
        if any(used_strategy):
            strategies = [
                strategy.attrs.name
                for i, strategy in enumerate(strategies)
                if used_strategy[i]
            ]
            # TODO split this
            text = "strategy" if len(strategies) == 1 else "strategies"
            raise ValueError(
                f"'{name}' measure cannot be deleted since it is already used in {text} {strategies}"
            )
        else:
            measure_path = self.input_path / "measures" / name
            shutil.rmtree(measure_path, ignore_errors=True)

    def copy_measure(self, old_name: str, new_name: str, new_long_name: str):
        """Copies (duplicates) an existing measures, and gives it a new name.

        Parameters
        ----------
        old_name : str
            name of the existing measure
        new_name : str
            name of the new measure
        new_long_name : str
            long_name of the new measure
        """
        # First do a get
        measure = self.get_measure(old_name)
        measure.attrs.name = new_name
        measure.attrs.long_name = new_long_name
        # Then a save
        self.save_measure(measure)
        # Then save all the accompanied files
        src = self.input_path / "measures" / old_name
        dest = self.input_path / "measures" / new_name
        for file in src.glob("*"):
            if "toml" not in file.name:
                shutil.copy(file, dest / file.name)

    # Event methods
    def get_event(self, name: str) -> IEvent:
        """Get the respective event object using the name of the event.

        Parameters
        ----------
        name : str
            name of the event

        Returns
        -------
        IMeasure
            object of one of the events
        """
        event_path = self.input_path / "events" / f"{name}" / f"{name}.toml"
        event_template = Event.get_template(event_path)
        event = EventFactory.get_event(event_template).load_file(event_path)
        return event

    def save_event(self, event: IEvent) -> None:
        """Saves a synthetic event object in the database.

        Parameters
        ----------
        event : IEvent
            object of one of the synthetic event types

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of measures should be unique.
        """
        names = self.get_events()["name"]
        if event.attrs.name in names:
            raise ValueError(
                f"'{event.attrs.name}' name is already used by another event. Choose a different name"
            )
        else:
            (self.input_path / "events" / event.attrs.name).mkdir()
            event.save(
                self.input_path
                / "events"
                / event.attrs.name
                / f"{event.attrs.name}.toml"
            )

    def write_to_csv(self, name: str, event: IEvent, df: pd.DataFrame):
        df.to_csv(
            Path(self.input_path, "events", event.attrs.name, f"{name}.csv"),
            header=False,
        )

    def edit_event(self, event: IEvent):
        """Edits an already existing event in the database.

        Parameters
        ----------
        event : IEvent
            object of the event
        """
        # TODO should you be able to edit a measure that is already used in a hazard?
        event.save(
            self.input_path / "events" / event.attrs.name / f"{event.attrs.name}.toml"
        )

    def delete_event(self, name: str):
        """Deletes an already existing event in the database.

        Parameters
        ----------
        name : str
            name of the event
        """

        # TODO: check if event is used in a hazard

        event_path = self.input_path / "events" / name
        shutil.rmtree(event_path, ignore_errors=True)

    def copy_event(self, old_name: str, new_name: str, new_long_name: str):
        """Copies (duplicates) an existing event, and gives it a new name.

        Parameters
        ----------
        old_name : str
            name of the existing event
        new_name : str
            name of the new event
        new_long_name : str
            long_name of the new event
        """
        # First do a get
        event = self.get_event(old_name)
        event.attrs.name = new_name
        event.attrs.long_name = new_long_name
        # Then a save
        self.save_event(event)
        # Then save all the accompanied files
        src = self.input_path / "events" / old_name
        dest = self.input_path / "events" / new_name
        for file in src.glob("*"):
            if "toml" not in file.name:
                shutil.copy(file, dest / file.name)

    # Projection methods
    def get_projection(self, name: str) -> IProjection:
        """Get the respective projection object using the name of the projection.

        Parameters
        ----------
        name : str
            name of the projection

        Returns
        -------
        IProjection
            object of one of the projection types
        """
        projection_path = self.input_path / "projections" / name / f"{name}.toml"
        projection = Projection.load_file(projection_path)
        return projection

    def save_projection(self, projection: IProjection) -> None:
        """Saves a projection object in the database.

        Parameters
        ----------
        projection : IProjection
            object of one of the projection types

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of projections should be unique.
        """
        names = self.get_projections()["name"]
        if projection.attrs.name in names:
            raise ValueError(
                f"'{projection.attrs.name}' name is already used by another projection. Choose a different name"
            )
        else:
            (self.input_path / "projections" / projection.attrs.name).mkdir()
            projection.save(
                self.input_path
                / "projections"
                / projection.attrs.name
                / f"{projection.attrs.name}.toml"
            )

    def edit_projection(self, projection: IProjection):
        """Edits an already existing projection in the database.

        Parameters
        ----------
        projection : IProjection
            object of one of the projection types (e.g., IElevate)
        """
        projection.save(
            self.input_path
            / "projections"
            / projection.attrs.name
            / f"{projection.attrs.name}.toml"
        )

    def delete_projection(self, name: str):
        """Deletes an already existing projection in the database.

        Parameters
        ----------
        name : str
            name of the projection

        """
        # TODO: make check if projection is used in strategies

        projection_path = self.input_path / "projections" / name
        shutil.rmtree(projection_path, ignore_errors=True)

    def copy_projection(self, old_name: str, new_name: str, new_long_name: str):
        """Copies (duplicates) an existing projection, and gives it a new name.

        Parameters
        ----------
        old_name : str
            name of the existing projection
        new_name : str
            name of the new projection
        new_long_name : str
            long_name of the new projection
        """
        # First do a get
        projection = self.get_projection(old_name)
        projection.attrs.name = new_name
        projection.attrs.long_name = new_long_name
        # Then a save
        self.save_projection(projection)
        # Then save all the accompanied files
        src = self.input_path / "projections" / old_name
        dest = self.input_path / "projections" / new_name
        for file in src.glob("*"):
            if "toml" not in file.name:
                shutil.copy(file, dest / file.name)

    # Strategy methods
    def get_strategy(self, name: str) -> IStrategy:
        """Get the respective strategy object using the name of the strategy.

        Parameters
        ----------
        name : str
            name of the strategy

        Returns
        -------
        IStrategy
            strategy object
        """
        strategy_path = self.input_path / "strategies" / name / f"{name}.toml"
        strategy = Strategy.load_file(strategy_path)
        return strategy

    def save_strategy(self, strategy: IStrategy) -> None:
        """Saves a strategy object in the database.

        Parameters
        ----------
        measure : IStrategy
            object of strategy type

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of strategies should be unique.
        """
        names = self.get_strategies()["name"]
        if strategy.attrs.name in names:
            raise ValueError(
                f"'{strategy.attrs.name}' name is already used by another strategy. Choose a different name"
            )
        else:
            (self.input_path / "strategies" / strategy.attrs.name).mkdir()
            strategy.save(
                self.input_path
                / "strategies"
                / strategy.attrs.name
                / f"{strategy.attrs.name}.toml"
            )

    def delete_strategy(self, name: str):
        """Deletes an already existing strategy in the database.

        Parameters
        ----------
        name : str
            name of the strategy

        Raises
        ------
        ValueError
            Raise error if strategy to be deleted is already used in a scenario.
        """
        scenarios = [Scenario.load_file(path) for path in self.get_scenarios()["path"]]
        used_scenario = [name == scenario.attrs.strategy for scenario in scenarios]

        if any(used_scenario):
            scenarios = [
                scenario.attrs.name
                for i, scenario in enumerate(scenarios)
                if used_scenario[i]
            ]
            # TODO split this
            text = "scenario" if len(scenarios) == 1 else "scenarios"
            raise ValueError(
                f"'{name}' measure cannot be deleted since it is already used in {text} {scenarios}"
            )
        else:
            strategy_path = self.input_path / "strategies" / name
            shutil.rmtree(strategy_path, ignore_errors=True)

    # scenario methods
    def get_scenario(self, name: str) -> IScenario:
        """Get the respective scenario object using the name of the scenario.

        Parameters
        ----------
        name : str
            name of the scenario

        Returns
        -------
        IScenario
            Scenario object
        """
        scenario_path = self.input_path / "scenarios" / name / f"{name}.toml"
        scenario = Scenario.load_file(scenario_path)
        scenario.init_object_model()
        return scenario

    def save_scenario(self, scenario: IScenario) -> None:
        """Saves a scenario object in the database.

        Parameters
        ----------
        measure : IScenario
            object of scenario type

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of scenarios should be unique.
        """
        names = self.get_scenarios()["name"]
        if scenario.attrs.name in names:
            raise ValueError(
                f"'{scenario.attrs.name}' name is already used by another scenario. Choose a different name"
            )
        else:
            (self.input_path / "scenarios" / scenario.attrs.name).mkdir()
            scenario.save(
                self.input_path
                / "scenarios"
                / scenario.attrs.name
                / f"{scenario.attrs.name}.toml"
            )

    def edit_scenario(self, scenario: IScenario):
        """Edits an already existing scenario in the database.

        Parameters
        ----------
        scenario : IScenario
            object of one of the scenario types (e.g., IScenario)
        """
        scenario.save(
            self.input_path
            / "scenarios"
            / scenario.attrs.name
            / f"{scenario.attrs.name}.toml"
        )

    def delete_scenario(self, name: str):
        """Deletes an already existing scenario in the database.

        Parameters
        ----------
        name : str
            name of the scenario

        Raises
        ------
        ValueError
            Raise error if scenario has already model output
        """
        scenario_path = self.input_path / "scenarios" / name
        scenario = Scenario.load_file(scenario_path / f"{name}.toml")
        scenario.init_object_model()
        if scenario.direct_impacts.hazard.has_run:
            raise ValueError(
                f"'{name}' scenario cannot be deleted since the hazard model has already run."
            )
        else:
            shutil.rmtree(scenario_path, ignore_errors=True)

    def update(self) -> None:
        self.projections = self.get_projections()
        self.events = self.get_events()
        self.measures = self.get_measures()
        self.strategies = self.get_strategies()
        self.scenarios = self.get_scenarios()

    def get_projections(self) -> dict[str, Any]:
        """Returns a dictionary with info on the projections that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'long_name', 'path' and 'last_modification_date' info
        """
        projections = self.get_object_list(object_type="projections")
        objects = [Projection.load_file(path) for path in projections["path"]]
        projections["name"] = [obj.attrs.name for obj in objects]
        projections["long_name"] = [obj.attrs.long_name for obj in objects]
        return projections

    def get_events(self) -> dict[str, Any]:
        """Returns a dictionary with info on the events that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'long_name', 'path' and 'last_modification_date' info
        """
        events = self.get_object_list(object_type="events")
        objects = [Hazard.get_event_object(path) for path in events["path"]]
        events["name"] = [obj.attrs.name for obj in objects]
        events["long_name"] = [obj.attrs.long_name for obj in objects]
        return events

    def get_measures(self) -> dict[str, Any]:
        """Returns a dictionary with info on the measures that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'long_name', 'path' and 'last_modification_date' info
        """
        measures = self.get_object_list(object_type="measures")
        objects = [MeasureFactory.get_measure_object(path) for path in measures["path"]]
        measures["name"] = [obj.attrs.name for obj in objects]
        measures["long_name"] = [obj.attrs.long_name for obj in objects]
        measures["geometry"] = [
            gpd.read_file(path.parent.joinpath(obj.attrs.polygon_file))
            if obj.attrs.polygon_file is not None
            else None
            for (path, obj) in zip(measures["path"], objects)
        ]
        return measures

    def get_strategies(self) -> dict[str, Any]:
        """Returns a dictionary with info on the strategies that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'long_name', 'path' and 'last_modification_date' info
        """
        strategies = self.get_object_list(object_type="strategies")
        objects = [Strategy.load_file(path) for path in strategies["path"]]
        strategies["name"] = [obj.attrs.name for obj in objects]
        strategies["long_name"] = [obj.attrs.long_name for obj in objects]
        return strategies

    def get_scenarios(self) -> dict[str, Any]:
        """Returns a dictionary with info on the events that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'long_name', 'path' and 'last_modification_date' info
        """
        scenarios = self.get_object_list(object_type="scenarios")
        objects = [Scenario.load_file(path) for path in scenarios["path"]]
        scenarios["name"] = [obj.attrs.name for obj in objects]
        scenarios["long_name"] = [obj.attrs.long_name for obj in objects]
        scenarios["Projection"] = [obj.attrs.projection for obj in objects]
        scenarios["Event"] = [obj.attrs.event for obj in objects]
        scenarios["Strategy"] = [obj.attrs.strategy for obj in objects]
        scenarios["finished"] = [
            obj.init_object_model().direct_impacts.has_run for obj in objects
        ]

        return scenarios

    def get_outputs(self) -> dict[str, Any]:
        all_scenarios = pd.DataFrame(self.get_scenarios())
        if len(all_scenarios) > 0:
            df = all_scenarios[all_scenarios["finished"]]
        else:
            df = all_scenarios
        finished = df.drop(columns="finished").reset_index(drop=True)
        return finished.to_dict()

    def get_topobathy_path(self) -> str:
        path = self.input_path.parent.joinpath("static", "dem", "tiles", "topobathy")
        return str(path)

    def get_index_path(self) -> str:
        path = self.input_path.parent.joinpath("static", "dem", "tiles", "indices")
        return str(path)

    def get_max_water_level(self, scenario_name: str):
        """returns an array with the maximum water levels of the SFINCS simulation

        Parameters
        ----------
        scenario_name : str
            name of scenario

        Returns
        -------
        _type_
            _description_
        """
        # raise NotImplementedError
        model_path = self.input_path.parent.joinpath(
            "output", "simulations", scenario_name, "overland"
        )
        mod = SfincsModel(model_path, mode="r")

        zsmax = mod.results["zsmax"][0, :, :].to_numpy()

        return zsmax

    def get_fiat_results(self, scenario_name: str):
        csv_path = self.input_path.parent.joinpath(
            "output",
            "results",
            scenario_name,
            f"{scenario_name}_results.csv",
        )
        csv_path2 = self.input_path.parent.joinpath(
            "output",
            "results",
            scenario_name,
            f"{scenario_name}_results_filt.csv",
        )
        if not csv_path2.exists():
            df = pd.read_csv(csv_path)
            df = df[df["Primary Object Type"] != "road"]
            df = df[df["Inundation Depth Event Structure"] > 0]
            df = df[~df["Aggregation Label: Subdivision"].isna()]
            df.to_csv(csv_path2)
        df = pd.read_csv(csv_path2)
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.X, df.Y))
        gdf = gdf[["Total Damage Event", "geometry"]]
        gdf["Total Damage Event"] = np.round(gdf["Total Damage Event"], 0)
        gdf.crs = 4326
        return gdf

    def get_fiat_footprints(self, scenario_name: str):
        shp_path = self.input_path.parent.joinpath(
            "output",
            "results",
            scenario_name,
            f"{scenario_name}_results.shp",
        )
        shp_path2 = self.input_path.parent.joinpath(
            "output",
            "results",
            scenario_name,
            f"{scenario_name}_results_filt.shp",
        )
        # ("Occup Type" != 'road') AND ( "AGG ID" != 'Not aggregated') AND( "Dmg Total" > 0 )
        if not shp_path2.exists():
            shp = gpd.read_file(shp_path)
            shp = shp[shp["Occup Type"] != "road"]
            shp = shp[shp["AGG ID"] != "Not aggregated"]
            shp = shp[shp["Dmg Total"] > 0]
            shp = shp[["Dmg Total", "geometry"]]
            shp["Dmg Total"] = np.round(shp["Dmg Total"], 0)
            shp.to_file(shp_path2)
        shp = gpd.read_file(shp_path2)
        return shp

    def get_aggregation(self, scenario_name: str):
        shp_path = self.input_path.parent.joinpath(
            "output",
            "results",
            scenario_name,
            f"{scenario_name}_subdivision_aggregated.shp",
        )
        gdf = gpd.read_file(shp_path)
        gdf = gdf[["Dmg Total", "geometry"]]

        return gdf

    def get_object_list(self, object_type: str) -> dict[str, Any]:
        """Given an object type (e.g., measures) get a dictionary with all the toml paths
        and last modification dates that exist in the database.

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
        scenario = self.get_scenario(scenario_name)

        simulations = list(
            self.input_path.parent.joinpath("output", "simulations").glob("*")
        )

        scns_simulated = [self.get_scenario(sim.name) for sim in simulations]

        for scn in scns_simulated:
            if scn.direct_impacts.hazard == scenario.direct_impacts.hazard:
                path_0 = self.input_path.parent.joinpath(
                    "output", "simulations", scn.attrs.name
                )
                path_new = self.input_path.parent.joinpath(
                    "output", "simulations", scenario.attrs.name
                )

                shutil.copytree(path_0, path_new)
                print(f"Hazard simulation is used from the '{scn.attrs.name}' scenario")

    def run_scenario(self, scenario_name: Union[str, list[str]]) -> None:
        """Runs a scenario hazard and impacts.

        Parameters
        ----------
        scenario_name : Union[str, list[str]]
            name(s) of the scenarios to run.
        """
        if not isinstance(scenario_name, list):
            scenario_name = [scenario_name]
        for scn in scenario_name:
            self.has_run_hazard(scn)
            scenario = self.get_scenario(scn)
            scenario.run()
