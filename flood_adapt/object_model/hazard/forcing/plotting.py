from pathlib import Path
from tempfile import gettempdir

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.template_event import Event
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallConstant,
    RainfallCSV,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.forcing.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.forcing.wind import (
    WindConstant,
    WindCSV,
    WindSynthetic,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IDischarge,
)
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.path_builder import (
    db_path,
)

UNPLOTTABLE_SOURCES = [ForcingSource.TRACK, ForcingSource.METEO, ForcingSource.MODEL]
logger = FloodAdaptLogging.getLogger(__name__)


def plot_forcing(
    event: Event,
    site: Site,
    forcing_type: ForcingType,
) -> str:
    """Plot the forcing data for the event."""
    if event.attrs.forcings[forcing_type] is None:
        return ""

    match forcing_type:
        case ForcingType.RAINFALL:
            return plot_rainfall(event)
        case ForcingType.WIND:
            return plot_wind(event)
        case ForcingType.WATERLEVEL:
            return plot_waterlevel(event, site)
        case ForcingType.DISCHARGE:
            return plot_discharge(event, site)
        case _:
            raise NotImplementedError(
                "Plotting only available for rainfall, wind, waterlevel, and discharge forcings."
            )


def plot_discharge(
    event: Event,
    site: Site,
) -> str:
    rivers: dict[str, IDischarge] = event.attrs.forcings[ForcingType.DISCHARGE]

    if site.attrs.sfincs.river is None:
        raise ValueError("No rivers defined for this site.")
    elif rivers is None:
        return ""

    logger.debug("Plotting discharge data")

    units = Settings().unit_system.discharge

    data = pd.DataFrame()
    errors = []

    for name, discharge in rivers.items():
        try:
            if discharge.source in UNPLOTTABLE_SOURCES:
                logger.debug(
                    f"Plotting not supported for discharge data from {discharge.source}"
                )
                continue
            elif isinstance(
                discharge, (DischargeConstant, DischargeSynthetic, DischargeCSV)
            ):
                river_data = discharge.to_dataframe(event.attrs.time)
            else:
                raise ValueError(f"Unknown discharge source: {discharge.source}")

            # add river_data as a column to the dataframe. keep the same index
            if data.empty:
                data = river_data
            else:
                data = data.join(river_data, how="outer")
        except Exception as e:
            errors.append((name, e))

    if errors:
        logger.error(
            f"Could not retrieve discharge data for {', '.join([entry[0] for entry in errors])}: {errors}"
        )
        return ""

    river_names, river_descriptions = [], []
    for river in site.attrs.sfincs.river:
        river_names.append(river.name)
        river_descriptions.append(river.description or river.name)

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
        xaxis={"range": [event.attrs.time.start_time, event.attrs.time.end_time]},
    )

    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir=event.dir_name, obj_name=event.attrs.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "discharge_timeseries.html"
    fig.write_html(output_loc)
    return str(output_loc)


def plot_waterlevel(
    event: Event,
    site: Site,
) -> str:
    waterlevel = event.attrs.forcings[ForcingType.WATERLEVEL]
    if waterlevel is None:
        return ""
    elif site.attrs.sfincs.water_level is None:
        raise ValueError("No water levels defined for this site.")

    if waterlevel.source in UNPLOTTABLE_SOURCES:
        logger.debug(
            f"Plotting not supported for waterlevel data from {waterlevel.source}"
        )
        return ""

    logger.debug("Plotting water level data")

    data = None
    try:
        if isinstance(waterlevel, WaterlevelGauged):
            if site.attrs.tide_gauge is None:
                raise ValueError("No tide gauge defined for this site.")
            data = TideGauge(site.attrs.tide_gauge).get_waterlevels_in_time_frame(
                event.attrs.time
            )
        elif isinstance(waterlevel, (WaterlevelCSV, WaterlevelSynthetic)):
            data = waterlevel.to_dataframe(event.attrs.time)
        else:
            raise ValueError(f"Unknown waterlevel type: {waterlevel}")

    except Exception as e:
        logger.error(f"Error getting water level data: {e}")
        return ""

    if data is not None and data.empty:
        logger.error(f"Could not retrieve waterlevel data: {waterlevel} {data}")
        return ""

    # Plot actual thing
    units = Settings().unit_system.length

    fig = px.line(data + site.attrs.sfincs.water_level.msl.height.convert(units))

    # plot reference water levels
    fig.add_hline(
        y=site.attrs.sfincs.water_level.msl.height.convert(units),
        line_dash="dash",
        line_color="#000000",
        annotation_text="MSL",
        annotation_position="bottom right",
    )
    if site.attrs.sfincs.water_level.other:
        for wl_ref in site.attrs.sfincs.water_level.other:
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
        xaxis={"range": [event.attrs.time.start_time, event.attrs.time.end_time]},
    )

    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir=event.dir_name, obj_name=event.attrs.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "waterlevel_timeseries.html"

    fig.write_html(output_loc)
    return str(output_loc)


def plot_rainfall(
    event: Event,
) -> str:
    rainfall = event.attrs.forcings[ForcingType.RAINFALL]
    if rainfall is None:
        return ""
    elif rainfall.source in UNPLOTTABLE_SOURCES:
        logger.warning(
            f"Plotting not supported for rainfall datafrom sources {', '.join(UNPLOTTABLE_SOURCES)}"
        )
        return ""

    logger.debug("Plotting rainfall data")

    data = None
    try:
        if isinstance(rainfall, (RainfallConstant, RainfallCSV, RainfallSynthetic)):
            data = rainfall.to_dataframe(event.attrs.time)
        else:
            raise ValueError(f"Unknown rainfall type: {rainfall}")
    except Exception as e:
        logger.error(f"Error getting rainfall data: {e}")
        return ""

    if data is None or data.empty:
        logger.error(f"Could not retrieve rainfall data: {rainfall} {data}")
        return ""

    # Add multiplier
    data *= event.attrs.rainfall_multiplier

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
        yaxis_title={
            "text": f"Rainfall intensity [{Settings().unit_system.intensity}]"
        },
        showlegend=False,
        xaxis={"range": [event.attrs.time.start_time, event.attrs.time.end_time]},
    )
    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir=event.dir_name, obj_name=event.attrs.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "rainfall_timeseries.html"

    fig.write_html(output_loc)
    return str(output_loc)


def plot_wind(
    event: Event,
) -> str:
    logger.debug("Plotting wind data")
    wind = event.attrs.forcings[ForcingType.WIND]
    if wind is None:
        return ""
    elif wind.source in UNPLOTTABLE_SOURCES:
        logger.warning(
            f"Plotting not supported for wind data from sources {', '.join(UNPLOTTABLE_SOURCES)}"
        )
        return ""

    data = None
    try:
        if isinstance(wind, (WindConstant, WindCSV, WindSynthetic)):
            data = wind.to_dataframe(event.attrs.time)
        else:
            raise ValueError(f"Unknown wind type: {wind}")
    except Exception as e:
        logger.error(f"Error getting wind data: {e}")
        return ""

    if data is None or data.empty:
        logger.error(
            f"Could not retrieve wind data: {event.attrs.forcings[ForcingType.WIND]} {data}"
        )
        return ""

    # Plot actual thing
    # Create figure with secondary y-axis

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
        title_text=f"Wind speed [{Settings().unit_system.velocity}]",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text=f"Wind direction {Settings().unit_system.direction}",
        secondary_y=True,
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
        xaxis={"range": [event.attrs.time.start_time, event.attrs.time.end_time]},
        xaxis_title={"text": "Time"},
        showlegend=False,
    )

    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir=event.dir_name, obj_name=event.attrs.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "wind_timeseries.html"

    fig.write_html(output_loc)
    return str(output_loc)
