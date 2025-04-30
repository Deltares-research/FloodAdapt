from pathlib import Path
from tempfile import gettempdir
from typing import List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from flood_adapt.config.site import Site
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.path_builder import (
    db_path,
)
from flood_adapt.objects.events.events import Event, Template
from flood_adapt.objects.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
    IDischarge,
)
from flood_adapt.objects.forcing.rainfall import (
    RainfallConstant,
    RainfallCSV,
    RainfallSynthetic,
)
from flood_adapt.objects.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelSynthetic,
)
from flood_adapt.objects.forcing.wind import (
    WindConstant,
    WindCSV,
    WindSynthetic,
)

# TODO remove from frontend
UNPLOTTABLE_SOURCES = [ForcingSource.TRACK, ForcingSource.METEO, ForcingSource.MODEL]
logger = FloodAdaptLogging.getLogger("Plotting")


def plot_forcing(
    event: Event,
    site: Site,
    forcing_type: ForcingType,
) -> tuple[str, Optional[List[Exception]]]:
    """Plot the forcing data for the event."""
    if event.forcings.get(forcing_type) is None:
        return "", None

    match forcing_type:
        case ForcingType.RAINFALL:
            return plot_rainfall(event, site)
        case ForcingType.WIND:
            return plot_wind(event, site)
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
) -> tuple[str, Optional[List[Exception]]]:
    rivers: List[IDischarge] = event.forcings.get(ForcingType.DISCHARGE)
    if site.sfincs.river is None:
        raise ValueError("No rivers defined for this site.")
    elif not rivers:
        return "", None
    logger.debug("Plotting discharge data")

    units = site.gui.units.default_discharge_units

    data = pd.DataFrame()
    errors = []

    for discharge in rivers:
        try:
            if discharge.source in UNPLOTTABLE_SOURCES:
                logger.debug(
                    f"Plotting not supported for discharge data from `{discharge.source}`"
                )
                continue
            elif isinstance(
                discharge, (DischargeConstant, DischargeSynthetic, DischargeCSV)
            ):
                river_data = discharge.to_dataframe(event.time)
            else:
                raise ValueError(f"Unknown discharge source: `{discharge.source}`")

            # Rename columns to avoid conflicts
            river_data.columns = [discharge.river.name]
            if data.empty:
                data = river_data
            else:
                # add river_data as a column to the dataframe. keep the same index
                data = data.join(river_data, how="outer")
        except Exception as e:
            errors.append((discharge.river.name, e))

    if errors:
        logger.error(
            f"Could not retrieve discharge data for {', '.join([entry[0] for entry in errors])}: {errors}"
        )
        return "", errors

    river_names, river_descriptions = [], []
    for river in site.sfincs.river:
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
        yaxis_title={"text": f"River discharge [{units.value}]"},
        xaxis={"range": [event.time.start_time, event.time.end_time]},
    )

    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir="events", obj_name=event.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "discharge_timeseries.html"
    if output_loc.exists():
        output_loc.unlink()
    fig.write_html(output_loc)
    return str(output_loc), None


def plot_waterlevel(
    event: Event,
    site: Site,
) -> tuple[str, Optional[List[Exception]]]:
    forcing_list = event.forcings.get(ForcingType.WATERLEVEL)
    if not forcing_list:
        return "", None
    elif site.sfincs.water_level is None:
        raise ValueError("No water levels defined for this site.")

    waterlevel = forcing_list[0]
    if waterlevel.source in UNPLOTTABLE_SOURCES:
        logger.debug(
            f"Plotting not supported for waterlevel data from {waterlevel.source}"
        )
        return "", None

    logger.debug("Plotting water level data")
    units = site.gui.units.default_length_units
    data = None
    try:
        if isinstance(waterlevel, WaterlevelGauged):
            if site.sfincs.tide_gauge is None:
                raise ValueError("No tide gauge defined for this site.")
            data = site.sfincs.tide_gauge.get_waterlevels_in_time_frame(
                event.time, units=units
            )

            # Convert to main reference
            datum_correction = site.sfincs.water_level.get_datum(
                site.sfincs.tide_gauge.reference
            ).height.convert(units)
            data += datum_correction

        elif isinstance(waterlevel, WaterlevelCSV):
            data = waterlevel.to_dataframe(event.time)
        elif isinstance(waterlevel, WaterlevelSynthetic):
            data = waterlevel.to_dataframe(time_frame=event.time)
            datum_correction = site.sfincs.water_level.get_datum(
                site.gui.plotting.synthetic_tide.datum
            ).height.convert(units)
            data += datum_correction
        else:
            raise ValueError(f"Unknown waterlevel type: {waterlevel}")

    except Exception as e:
        logger.error(f"Error getting water level data: {e}")
        return "", [e]

    if data is not None and data.empty:
        logger.error(f"Could not retrieve waterlevel data: {waterlevel} {data}")
        return "", None

    if event.template == Template.Synthetic:
        data.index = (
            data.index - data.index[0]
        ).total_seconds() / 3600  # Convert to hours
        x_title = "Hours from start"
    else:
        x_title = "Time"

    # Plot actual thing
    fig = px.line(data)

    # plot main reference
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#000000",
        annotation_text=site.sfincs.water_level.reference,
        annotation_position="bottom right",
    )

    # plot other references
    for wl_ref in site.sfincs.water_level.datums:
        if (
            wl_ref.name == site.sfincs.config.overland_model.reference
            or wl_ref.name in site.gui.plotting.excluded_datums
        ):
            continue

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
        xaxis_title=x_title,
        yaxis_title=f"Water level [{units.value}]",
        yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
        xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
        showlegend=False,
        xaxis={"range": [data.index.min(), data.index.max()]},
    )

    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir="events", obj_name=event.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "waterlevel_timeseries.html"
    if output_loc.exists():
        output_loc.unlink()
    fig.write_html(output_loc)
    return str(output_loc), None


def plot_rainfall(
    event: Event,
    site: Site,
) -> tuple[str, Optional[List[Exception]]]:
    forcing_list = event.forcings.get(ForcingType.RAINFALL)
    if not forcing_list:
        return "", None
    elif forcing_list[0].source in UNPLOTTABLE_SOURCES:
        logger.warning(
            f"Plotting not supported for rainfall datafrom sources {', '.join(UNPLOTTABLE_SOURCES)}"
        )
        return "", None

    rainfall = forcing_list[0]
    logger.debug("Plotting rainfall data")

    data = None
    try:
        if isinstance(rainfall, (RainfallConstant, RainfallCSV, RainfallSynthetic)):
            data = rainfall.to_dataframe(event.time)
        else:
            raise ValueError(f"Unknown rainfall type: {rainfall}")
    except Exception as e:
        logger.error(f"Error getting rainfall data: {e}")
        return "", [e]

    if data is None or data.empty:
        logger.error(f"Could not retrieve rainfall data: {rainfall} {data}")
        return "", None

    # Add multiplier
    data *= event.rainfall_multiplier

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
            "text": f"Rainfall intensity [{site.gui.units.default_intensity_units.value}]"
        },
        showlegend=False,
        xaxis={"range": [event.time.start_time, event.time.end_time]},
    )
    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir="events", obj_name=event.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "rainfall_timeseries.html"
    if output_loc.exists():
        output_loc.unlink()
    fig.write_html(output_loc)
    return str(output_loc), None


def plot_wind(
    event: Event,
    site: Site,
) -> tuple[str, Optional[List[Exception]]]:
    logger.debug("Plotting wind data")
    forcing_list = event.forcings.get(ForcingType.WIND)
    if not forcing_list:
        return "", None
    elif forcing_list[0].source in UNPLOTTABLE_SOURCES:
        logger.warning(
            f"Plotting not supported for wind data from sources {', '.join(UNPLOTTABLE_SOURCES)}"
        )
        return "", None

    wind = forcing_list[0]
    data = None
    try:
        if isinstance(wind, (WindConstant, WindCSV, WindSynthetic)):
            data = wind.to_dataframe(event.time)
        else:
            raise ValueError(f"Unknown wind type: {wind}")
    except Exception as e:
        logger.error(f"Error getting wind data: {e}")
        return "", [e]

    if data is None or data.empty:
        logger.error(
            f"Could not retrieve wind data: {event.forcings.get(ForcingType.WIND)} {data}"
        )
        return "", None

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
        title_text=f"Wind speed [{site.gui.units.default_velocity_units.value}]",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text=f"Wind direction {site.gui.units.default_direction_units.value}",
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
        xaxis={"range": [event.time.start_time, event.time.end_time]},
        xaxis_title={"text": "Time"},
        showlegend=False,
    )

    # Only save to the the event folder if that has been created already.
    # Otherwise this will create the folder and break the db since there is no event.toml yet
    output_dir = db_path(object_dir="events", obj_name=event.name)
    if not output_dir.exists():
        output_dir = gettempdir()
    output_loc = Path(output_dir) / "wind_timeseries.html"
    if output_loc.exists():
        output_loc.unlink()
    fig.write_html(output_loc)
    return str(output_loc), None
