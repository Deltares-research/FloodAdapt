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

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.io.fiat import Fiat
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

    def interp_slr(self, slr_scenario: str, year: float) -> UnitfulLength:
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
                    value=np.round(slr - ref_slr, decimals=2),
                    units=df["units"][0],
                )
                return new_slr

    def plot_slr_scenarios(self) -> None:
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

        df = df.set_index("Year").drop(columns="units").stack().reset_index()
        df = df.rename(
            columns={"level_1": "Scenario", 0: "Sea level rise [{}]".format(units)}
        )

        colors = px.colors.sample_colorscale(
            "rainbow", [n / (ncolors - 1) for n in range(ncolors)]
        )
        fig = px.line(
            df,
            x="Year",
            y=f"Sea level rise [{units}]",
            color="Scenario",
            color_discrete_sequence=colors,
        )

        # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

        fig.update_layout(
            autosize=True,
            height=200,
            width=500,
            margin={"r": 20, "l": 20, "b": 20, "t": 20},
            font={"size": 11, "family": "Arial"},
        )

        # write html to results folder
        fig.write_html(self.input_path.parent.joinpath("static", "slr", "slr.html"))

    def get_buildings(self) -> GeoDataFrame:
        """Get the building footprints from the FIAT model.
        This should only be the buildings excluding any other types (e.g., roads)
        The parameters non_building_names in the site config is used for that

        Returns
        -------
        GeoDataFrame
            building footprints with all the FIAT columns
        """
        fiat_model = Fiat(
            fiat_path=self.input_path.parent / "static" / "templates" / "fiat",
            crs=self.site.attrs.fiat.exposure_crs,
        )
        buildings = fiat_model.get_buildings(
            type="ALL", non_building_names=self.site.attrs.fiat.non_building_names
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
        projections = self.get_object_list(object_type="Projections")
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
        events = self.get_object_list(object_type="Events")
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
        measures = self.get_object_list(object_type="Measures")
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
        strategies = self.get_object_list(object_type="Strategies")
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
        scenarios = self.get_object_list(object_type="Scenarios")
        objects = [Scenario.load_file(path) for path in scenarios["path"]]
        scenarios["name"] = [obj.attrs.name for obj in objects]
        scenarios["long_name"] = [obj.attrs.long_name for obj in objects]
        return scenarios

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
