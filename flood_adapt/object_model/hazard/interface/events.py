import os
from abc import abstractmethod
from pathlib import Path
from tempfile import gettempdir
from typing import Any, ClassVar, List, Type

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pydantic import (
    Field,
    field_serializer,
    model_validator,
)

from flood_adapt.misc.config import Settings
from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.interface.models import (
    Mode,
    Template,
    TimeModel,
)
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import Site
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesVelocity,
)


class IEventModel(IObjectModel):
    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]]

    time: TimeModel
    template: Template
    mode: Mode
    water_level_offset: UnitfulLength = UnitfulLength(
        value=0, units=UnitTypesLength.meters
    )

    forcings: dict[ForcingType, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    def create_forcings(self):
        if "forcings" in self:
            forcings = {}
            for ftype, forcing_attrs in self["forcings"].items():
                if isinstance(forcing_attrs, IForcing):
                    # forcing_attrs is already a forcing object
                    forcings[ftype] = forcing_attrs
                elif (
                    isinstance(forcing_attrs, dict)
                    and "_type" in forcing_attrs
                    and "_source" in forcing_attrs
                ):
                    # forcing_attrs is a dict with forcing attributes
                    forcings[ftype] = ForcingFactory.load_dict(forcing_attrs)
                else:
                    # forcing_attrs is a dict with sub-forcing attributes. Currently only used for discharge forcing
                    for name, sub_forcing in forcing_attrs.items():
                        if ftype not in forcings:
                            forcings[ftype] = {}

                        if isinstance(sub_forcing, IForcing):
                            forcings[ftype][name] = sub_forcing
                        else:
                            forcings[ftype][name] = ForcingFactory.load_dict(
                                sub_forcing
                            )
            self["forcings"] = forcings
        return self

    @model_validator(mode="after")
    def validate_forcings(self):
        def validate_concrete_forcing(concrete_forcing):
            _type = concrete_forcing._type
            _source = concrete_forcing._source

            # Check type
            if _type not in self.__class__.ALLOWED_FORCINGS:
                allowed_types = ", ".join(
                    t.value for t in self.__class__.ALLOWED_FORCINGS.keys()
                )
                raise ValueError(
                    f"Forcing type {_type.value} is not allowed. Allowed types are: {allowed_types}"
                )

            # Check source
            if _source not in self.__class__.ALLOWED_FORCINGS[_type]:
                allowed_sources = ", ".join(
                    s.value for s in self.__class__.ALLOWED_FORCINGS[_type]
                )
                raise ValueError(
                    f"Forcing source {_source.value} is not allowed for forcing type {_type.value}. "
                    f"Allowed sources are: {allowed_sources}"
                )

        for concrete_forcing in self.forcings.values():
            if concrete_forcing is None:
                continue

            if isinstance(concrete_forcing, dict):
                for _, _concrete_forcing in concrete_forcing.items():
                    validate_concrete_forcing(_concrete_forcing)
            else:
                validate_concrete_forcing(concrete_forcing)

        return self

    @field_serializer("forcings")
    @classmethod
    def serialize_forcings(
        cls, value: dict[ForcingType, IForcing | dict[str, IForcing]]
    ) -> dict[str, dict[str, Any]]:
        dct = {}
        for ftype, forcing in value.items():
            if not forcing:
                continue
            if isinstance(forcing, IForcing):
                dct[ftype.value] = forcing.model_dump(exclude_none=True)
            else:
                dct[ftype.value] = {
                    name: forcing.model_dump(exclude_none=True)
                    for name, forcing in forcing.items()
                }
        return dct

    @classmethod
    def get_allowed_forcings(cls) -> dict[str, List[str]]:
        return {k.value: [s.value for s in v] for k, v in cls.ALLOWED_FORCINGS.items()}

    @abstractmethod
    def default(cls) -> "IEventModel":
        """Return the default event model."""
        ...


class IEvent(IObject[IEventModel]):
    MODEL_TYPE: Type[IEventModel]
    dir_name = ObjectDir.event

    attrs: IEventModel
    _site = None

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        for forcing in self.attrs.forcings.values():
            if forcing is None:
                continue
            if isinstance(forcing, dict):
                for _, _forcing in forcing.items():
                    _forcing.save_additional(output_dir)
            else:
                forcing.save_additional(output_dir)

    @abstractmethod
    def process(self, scenario: IScenario = None):
        """
        Process the event to generate forcing data.

        The simplest implementation of the process method is to do nothing.
        Some forcings are just data classes that do not require processing as they contain all information as attributes.
        For more complicated events, overwrite this method in the subclass and implement the necessary steps to generate the forcing data.

        - Read event- ( and possibly scenario) to see what forcings are needed
        - Prepare forcing data (download, run offshore model, etc.)
        - Set forcing data in forcing objects if necessary
        """
        ...

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        _self = self.attrs.model_dump(
            exclude={"name", "description"}, exclude_none=True
        )
        _other = other.attrs.model_dump(
            exclude={"name", "description"}, exclude_none=True
        )
        return _self == _other

    def plot_forcing(
        self,
        forcing_type: ForcingType,
        units: (
            UnitTypesLength
            | UnitTypesIntensity
            | UnitTypesDischarge
            | UnitTypesVelocity
            | None
        ) = None,
    ) -> str | None:
        """Plot the forcing data for the event."""
        if self._site is None:
            self._site = Site.load_file(
                db_path(top_level_dir=TopLevelDir.static, object_dir=ObjectDir.site)
                / "site.toml"
            )

        match forcing_type:
            case ForcingType.RAINFALL:
                return self.plot_rainfall(units=units)
            case ForcingType.WIND:
                return self.plot_wind(velocity_units=units)
            case ForcingType.WATERLEVEL:
                return self.plot_waterlevel(units=units)
            case ForcingType.DISCHARGE:
                return self.plot_discharge(units=units)
            case _:
                raise NotImplementedError(
                    "Plotting only available for rainfall, wind, waterlevel, and discharge forcings."
                )

    def plot_waterlevel(self, units: UnitTypesLength):
        if self.attrs.forcings[ForcingType.WATERLEVEL] is None:
            return ""

        if self.attrs.forcings[ForcingType.WATERLEVEL]._source in [
            ForcingSource.METEO,
            ForcingSource.MODEL,
        ]:
            self.logger.warning(
                f"Plotting not supported for waterlevel data from {self.attrs.forcings[ForcingType.WATERLEVEL]._source}"
            )
            return ""

        self.logger.debug("Plotting water level data")

        units = units or Settings().unit_system.length
        xlim1, xlim2 = self.attrs.time.start_time, self.attrs.time.end_time

        data = None
        try:
            data = self.attrs.forcings[ForcingType.WATERLEVEL].get_data(
                t0=xlim1, t1=xlim2
            )
        except Exception as e:
            self.logger.error(f"Error getting water level data: {e}")
            return

        if data is not None and data.empty:
            self.logger.error(
                f"Could not retrieve waterlevel data: {self.attrs.forcings[ForcingType.WATERLEVEL]} {data}"
            )
            return

        # Plot actual thing
        fig = px.line(data + self._site.attrs.water_level.msl.height.convert(units))

        # plot reference water levels
        fig.add_hline(
            y=self._site.attrs.water_level.msl.height.convert(units),
            line_dash="dash",
            line_color="#000000",
            annotation_text="MSL",
            annotation_position="bottom right",
        )
        if self._site.attrs.water_level.other:
            for wl_ref in self._site.attrs.water_level.other:
                fig.add_hline(
                    y=wl_ref.height.convert(units),
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
            yaxis_title=f"Water level [{units}]",
            yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            showlegend=False,
            xaxis={"range": [xlim1, xlim2]},
        )

        # Only save to the the event folder if that has been created already.
        # Otherwise this will create the folder and break the db since there is no event.toml yet
        output_dir = db_path(object_dir=self.dir_name, obj_name=self.attrs.name)
        if not output_dir.exists():
            output_dir = gettempdir()
        output_loc = Path(output_dir) / "waterlevel_timeseries.html"

        fig.write_html(output_loc)
        return str(output_loc)

    def plot_rainfall(self, units: UnitTypesIntensity = None) -> str | None:
        units = units or Settings().unit_system.intensity

        if self.attrs.forcings[ForcingType.RAINFALL] is None:
            return ""

        if self.attrs.forcings[ForcingType.RAINFALL]._source in [
            ForcingSource.TRACK,
            ForcingSource.METEO,
        ]:
            self.logger.warning(
                "Plotting not supported for rainfall data from track or meteo"
            )
            return ""

        self.logger.debug("Plotting rainfall data")

        # set timing
        xlim1, xlim2 = self.attrs.time.start_time, self.attrs.time.end_time

        if self.attrs.forcings[ForcingType.RAINFALL] is None:
            return

        data = None
        try:
            data = self.attrs.forcings[ForcingType.RAINFALL].get_data(
                t0=xlim1, t1=xlim2
            )
        except Exception as e:
            self.logger.error(f"Error getting rainfall data: {e}")
            return

        if data is None or data.empty:
            self.logger.error(
                f"Could not retrieve rainfall data: {self.attrs.forcings[ForcingType.RAINFALL]} {data}"
            )
            return

        # Plot actual thing
        fig = px.line(data_frame=data)

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
            yaxis_title={"text": f"Rainfall intensity [{units}]"},
            showlegend=False,
            xaxis={"range": [xlim1, xlim2]},
        )
        # Only save to the the event folder if that has been created already.
        # Otherwise this will create the folder and break the db since there is no event.toml yet
        output_dir = db_path(object_dir=self.dir_name, obj_name=self.attrs.name)
        if not output_dir.exists():
            output_dir = gettempdir()
        output_loc = Path(output_dir) / "rainfall_timeseries.html"

        fig.write_html(output_loc)
        return str(output_loc)

    def plot_discharge(self, units: UnitTypesDischarge = None) -> str:
        units = units or Settings().unit_system.discharge

        # set timing relative to T0 if event is synthetic
        xlim1, xlim2 = self.attrs.time.start_time, self.attrs.time.end_time

        if self.attrs.forcings[ForcingType.DISCHARGE] is None:
            return ""

        self.logger.debug("Plotting discharge data")

        rivers = self.attrs.forcings[ForcingType.DISCHARGE]

        data = pd.DataFrame()
        errors = []

        for name, river in rivers.items():
            try:
                river_data = river.get_data(t0=xlim1, t1=xlim2)
                # add river_data as a column to the dataframe. keep the same index
                if data.empty:
                    data = river_data
                else:
                    data = data.join(river_data, how="outer")
            except Exception as e:
                errors.append((name, e))

        if errors:
            self.logger.error(
                f"Could not retrieve discharge data for {', '.join([entry[0] for entry in errors])}: {errors}"
            )
            return ""

        river_names = [i.name for i in self._site.attrs.river]
        river_descriptions = [i.description for i in self._site.attrs.river]
        river_descriptions = np.where(
            river_descriptions is None, river_names, river_descriptions
        ).tolist()

        # Plot actual thing
        fig = go.Figure()
        for ii, col in enumerate(data.columns):
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data[col],
                    name=river_descriptions[ii],
                    mode="lines",
                )
            )

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
            yaxis_title={"text": f"River discharge [{units}]"},
            xaxis={"range": [xlim1, xlim2]},
        )

        # Only save to the the event folder if that has been created already.
        # Otherwise this will create the folder and break the db since there is no event.toml yet
        output_dir = db_path(object_dir=self.dir_name, obj_name=self.attrs.name)
        if not output_dir.exists():
            output_dir = gettempdir()
        output_loc = Path(output_dir) / "discharge_timeseries.html"
        fig.write_html(output_loc)
        return str(output_loc)

    def plot_wind(
        self,
        velocity_units: UnitTypesVelocity = None,
        direction_units: UnitTypesDirection = None,
    ) -> str:
        if self.attrs.forcings[ForcingType.WIND] is None:
            return ""

        if self.attrs.forcings[ForcingType.WIND]._source in [
            ForcingSource.TRACK,
            ForcingSource.METEO,
        ]:
            self.logger.warning(
                "Plotting not supported for wind data from track or meteo"
            )
            return ""

        self.logger.debug("Plotting wind data")

        velocity_units = velocity_units or Settings().unit_system.velocity
        direction_units = direction_units or Settings().unit_system.direction

        xlim1, xlim2 = self.attrs.time.start_time, self.attrs.time.end_time

        data = None
        try:
            data = self.attrs.forcings[ForcingType.WIND].get_data(xlim1, xlim2)
        except Exception as e:
            self.logger.error(f"Error getting wind data: {e}")

        if data is None or data.empty:
            self.logger.error(
                f"Could not retrieve wind data: {self.attrs.forcings[ForcingType.WIND]} {data}"
            )
            return ""

        # Plot actual thing
        # Create figure with secondary y-axis
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add traces
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data.iloc[:, 0],
                name="Wind speed",
                mode="lines",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=data.index, y=data.iloc[:, 1], name="Wind direction", mode="markers"
            ),
            secondary_y=True,
        )

        # Set y-axes titles
        fig.update_yaxes(
            title_text=f"Wind speed [{velocity_units}]",
            secondary_y=False,
        )
        fig.update_yaxes(
            title_text=f"Wind direction {direction_units}", secondary_y=True
        )

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
            xaxis={"range": [xlim1, xlim2]},
            xaxis_title={"text": "Time"},
            showlegend=False,
        )

        # Only save to the the event folder if that has been created already.
        # Otherwise this will create the folder and break the db since there is no event.toml yet
        output_dir = db_path(object_dir=self.dir_name, obj_name=self.attrs.name)
        if not output_dir.exists():
            output_dir = gettempdir()
        output_loc = Path(output_dir) / "wind_timeseries.html"

        fig.write_html(output_loc)
        return str(output_loc)