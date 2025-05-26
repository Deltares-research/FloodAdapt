import math
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from plotly.express import line
from plotly.express.colors import sample_colorscale
from pydantic import AfterValidator, BaseModel, Field, model_validator
from tomli import load as load_toml
from typing_extensions import Annotated

from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.tide_gauge import TideGauge
from flood_adapt.objects.forcing.timeseries import Scstype


def ensure_ascii(s: str):
    assert s.isascii()
    return s


AsciiStr = Annotated[str, AfterValidator(ensure_ascii)]


class Cstype(str, Enum):
    """The accepted input for the variable cstype in Site."""

    projected = "projected"
    spherical = "spherical"


class SCSModel(BaseModel):
    """Class describing the accepted input for the variable scs.

    Includes the file with the non-dimensional SCS rainfall curves in the site folder and the SCS rainfall curve type.

    Attributes
    ----------
    file : str
        The path to the SCS rainfall curves file.
    type : Scstype
        The type of the SCS rainfall curve.
    """

    file: str
    type: Scstype


class RiverModel(BaseModel):
    """Model that describes the accepted input for the variable river in Site.

    Attributes
    ----------
    name : str
        The name of the river.
    description : Optional[str], default=None
        description of the river.
    mean_discharge : us.UnitfulDischarge
        The mean discharge of the river.
    x_coordinate : float
        The x coordinate of the river.
    y_coordinate : float
        The y coordinate of the river.
    """

    name: str
    description: Optional[str] = None
    mean_discharge: us.UnitfulDischarge
    x_coordinate: float
    y_coordinate: float


class ObsPointModel(BaseModel):
    """The accepted input for the variable obs_point in Site.

    obs_points is used to define output locations in the hazard model, which will be plotted in the user interface.

    Attributes
    ----------
    name : Union[int, AsciiStr]
        The name of the observation point.
    description : Optional[str], default=""
        The description of the observation point.
    ID : Optional[int], default=None
        The ID of the observation point.
    file : Optional[str], default=None
        The path to the observation point data file.
    """

    name: Union[int, AsciiStr]
    description: Optional[str] = ""
    ID: Optional[int] = (
        None  # if the observation station is also a tide gauge, this ID should be the same as for obs_station
    )
    file: Optional[str] = None  # for locally stored data
    lat: float
    lon: float


class FloodFrequencyModel(BaseModel):
    """The accepted input for the variable flood_frequency in Site."""

    flooding_threshold: us.UnitfulLength


class DemModel(BaseModel):
    """The accepted input for the variable dem in Site.

    Attributes
    ----------
    filename : str
        The path to the digital elevation model file.
    units : us.UnitTypesLength
        The units of the digital elevation model file.
    """

    filename: str
    units: us.UnitTypesLength


class FloodmapType(str, Enum):
    """The accepted input for the variable floodmap in Site."""

    water_level = "water_level"
    water_depth = "water_depth"


class DatumModel(BaseModel):
    """
    The accepted input for the variable datums in WaterlevelReferenceModel.

    Attributes
    ----------
    name : str
        The name of the vertical reference model.
    height : us.UnitfulLength
        The height of the vertical reference model relative to the main reference.
    """

    name: str
    height: us.UnitfulLength


class WaterlevelReferenceModel(BaseModel):
    """The accepted input for the variable water_level in Site.

    Waterlevels timeseries are calculated from user input, assumed to be relative to the `reference` vertical reference model.

    For plotting in the GUI, the `reference` vertical reference model is used as the main zero-reference, all values are relative to this.
    All other vertical reference models are plotted as dashed lines.

    Attributes
    ----------
    reference : str
        The name of the vertical reference model that is used as the main zero-reference.
    datums : list[DatumModel]
        The vertical reference models that are used to calculate the waterlevels timeseries.
        The datums are used to calculate the waterlevels timeseries, which are relative to the `reference` vertical reference model.
    """

    reference: str
    datums: list[DatumModel] = Field(default_factory=list)

    def get_datum(self, name: str) -> DatumModel:
        for datum in self.datums:
            if datum.name == name:
                return datum
        raise ValueError(f"Could not find datum with name {name}")

    @model_validator(mode="after")
    def main_reference_should_be_in_datums_and_eq_zero(self):
        if self.reference not in [datum.name for datum in self.datums]:
            raise ValueError(f"Reference {self.reference} not in {self.datums}")
        if not math.isclose(
            self.get_datum(self.reference).height.value, 0, abs_tol=1e-6
        ):
            raise ValueError(f"Reference {self.reference} height is not zero")
        return self

    @model_validator(mode="after")
    def all_datums_should_have_unique_names(self):
        datum_names = [datum.name for datum in self.datums]
        if len(set(datum_names)) != len(datum_names):
            raise ValueError(f"Duplicate datum names found: {datum_names}")
        return self


class CycloneTrackDatabaseModel(BaseModel):
    """The accepted input for the variable cyclone_track_database in Site.

    Attributes
    ----------
    file : str
        The path to the cyclone track database file.
    """

    file: str


class SlrScenariosModel(BaseModel):
    """The accepted input for the variable slr_scenarios.

    Attributes
    ----------
    file : str
        The path to the sea level rise scenarios file.
    relative_to_year : int
        The year to which the sea level rise scenarios are relative.
    """

    file: str
    relative_to_year: int

    def interp_slr(
        self,
        scenario: str,
        year: float,
        units: us.UnitTypesLength = us.UnitTypesLength.meters,
    ) -> float:
        """Interpolate SLR value and reference it to the SLR reference year from the site toml.

        Parameters
        ----------
        csv_path : Path
            Path to the slr.csv file containing the SLR scenarios.
        scenario : str
            SLR scenario name to use from the column names in self.file
        year : float
            year to evaluate
        units : us.UnitTypesLength, default = us.UnitTypesLength.meters
            The units to convert the SLR value to. Default is meters.

        Returns
        -------
        float
            The interpolated sea level rise value in the specified units, relative to the reference year.

        Raises
        ------
        ValueError
            if the reference year is outside of the time range in the slr.csv file
        ValueError
            if the year to evaluate is outside of the time range in the slr.csv file
        """
        df = pd.read_csv(self.file)
        if year > df["year"].max() or year < df["year"].min():
            raise ValueError(
                "The selected year is outside the range of the available SLR scenarios"
            )

        if (
            self.relative_to_year > df["year"].max()
            or self.relative_to_year < df["year"].min()
        ):
            raise ValueError(
                f"The reference year {self.relative_to_year} is outside the range of the available SLR scenarios"
            )

        slr = np.interp(year, df["year"], df[scenario])
        ref_slr = np.interp(self.relative_to_year, df["year"], df[scenario])

        new_slr = us.UnitfulLength(
            value=slr - ref_slr,
            units=df["units"][0],
        )
        return np.round(new_slr.convert(units), decimals=2)

    def plot_slr_scenarios(
        self,
        scenario_names: list[str],
        output_loc: Path,
        units: us.UnitTypesLength = us.UnitTypesLength.meters,
    ) -> str:
        """
        Plot sea level rise scenarios.

        Returns
        -------
        html_path : str
            The path to the html plot of the sea level rise scenarios.
        """
        df = pd.read_csv(self.file)

        ncolors = len(df.columns) - 2
        if "units" not in df.columns:
            raise ValueError(f"Expected column `units` in {self.file}.")

        _units = df["units"].iloc[0]
        _units = us.UnitTypesLength(_units)

        if "Year" not in df.columns:
            raise ValueError(f"Expected column `Year` in {self.file}.")

        if (
            self.relative_to_year > df["Year"].max()
            or self.relative_to_year < df["Year"].min()
        ):
            raise ValueError(
                f"The reference year {self.relative_to_year} is outside the range of the available SLR scenarios"
            )

        for scn in scenario_names:
            ref_slr = np.interp(self.relative_to_year, df["Year"], df[scn])
            df[scn] -= ref_slr

        df = df.drop(columns="units").melt(id_vars=["Year"]).reset_index(drop=True)
        # convert to units used in GUI
        conversion_factor = us.UnitfulLength(value=1.0, units=_units).convert(units)
        df.iloc[:, -1] = (conversion_factor * df.iloc[:, -1]).round(decimals=2)

        # rename column names that will be shown in html
        df = df.rename(
            columns={
                "variable": "Scenario",
                "value": f"Sea level rise [{units.value}]",
            }
        )

        colors = sample_colorscale(
            "rainbow", [n / (ncolors - 1) for n in range(ncolors)]
        )
        fig = line(
            df,
            x="Year",
            y=f"Sea level rise [{units.value}]",
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
            xaxis_range=[self.relative_to_year, df["Year"].max()],
            legend_title=None,
            # paper_bgcolor="#3A3A3A",
            # plot_bgcolor="#131313",
        )

        # write html to results folder
        output_loc.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(output_loc)
        return str(output_loc)


class FloodModel(BaseModel):
    """The accepted input for the variable overland_model and offshore_model in Site.

    Attributes
    ----------
    name : str
        The name of the directory in `static/templates/<directory>` that contains the template model files.
    reference : str
        The name of the vertical reference model that is used as the reference datum. Should be defined in water_level.datums.
    vertical_offset : Optional[us.UnitfulLength], default = None
        The vertical offset of the vertical reference model relative to the main reference.
        Given that the height of the vertical reference model is often determined by external sources,
        this vertical offset can be used to correct systematic over-/underestimation of a vertical reference model.
    """

    name: str
    reference: str

    # this used to be water_level_offset from events
    vertical_offset: Optional[us.UnitfulLength] = None


class SfincsConfigModel(BaseModel):
    """The expected variables and data types of attributes of the SfincsConfig class.

    Attributes
    ----------
    csname : str
        The name of the CS model.
    cstype : Cstype
        Cstype of the CS model. must be either "projected" or "spherical".
    version : Optional[str], default = None
        The version of the CS model. If None, the version is not specified.
    offshore_model : Optional[FloodModel], default = None
        The offshore model. If None, the offshore model is not specified.
    overland_model : FloodModel
        The overland model. This is the main model used for the simulation.
    floodmap_units : us.UnitTypesLength
        The units used for the output floodmap. Sfincs always produces in metric units, this is used to convert the floodmap to the correct units.
    save_simulation : Optional[bool], default = False
        Whether to keep or delete the simulation files after the simulation is finished and all output files are created.
        If True, the simulation files are kept. If False, the simulation files are deleted.
    """

    csname: str
    cstype: Cstype
    version: Optional[str] = None
    offshore_model: Optional[FloodModel] = None
    overland_model: FloodModel
    floodmap_units: us.UnitTypesLength
    save_simulation: Optional[bool] = False


class SfincsModel(BaseModel):
    """The expected variables and data types of attributes of the Sfincs class.

    Attributes
    ----------
    config : SfincsConfigModel
        The configuration of the Sfincs model.
    water_level : WaterlevelReferenceModel
        The collection of all datums and the main reference datum.
    dem : DemModel
        The digital elevation model.
    flood_frequency : FloodFrequencyModel, default = FloodFrequencyModel()
        The flood frequency model.
    slr : SlrScenariosModel
        Specification of the sea level rise scenarios.
    cyclone_track_database : CycloneTrackDatabaseModel, optional, default = None
        The cyclone track database model.
    scs : SCSModel, optional, default = None
        The SCS model.
    tide_gauge : TideGauge, optional, default = None
        The tide gauge model.
    river : list[RiverModel], optional, default = None
        The river model.
    obs_point : list[ObsPointModel], optional, default = None
        The observation point model.
    """

    config: SfincsConfigModel
    water_level: WaterlevelReferenceModel
    cyclone_track_database: Optional[CycloneTrackDatabaseModel] = None
    slr_scenarios: Optional[SlrScenariosModel] = None
    scs: Optional[SCSModel] = None  # optional for the US to use SCS rainfall curves
    dem: DemModel

    flood_frequency: FloodFrequencyModel = FloodFrequencyModel(
        flooding_threshold=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters)
    )  # TODO we dont actually use this anywhere?

    tide_gauge: Optional[TideGauge] = None
    river: Optional[list[RiverModel]] = None
    obs_point: Optional[list[ObsPointModel]] = None

    @staticmethod
    def read_toml(path: Path) -> "SfincsModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return SfincsModel(**toml_contents)

    @model_validator(mode="after")
    def ensure_references_exist(self):
        datum_names = [d.name for d in self.water_level.datums]

        if self.config.overland_model.reference not in datum_names:
            raise ValueError(
                f"Could not find reference `{self.config.overland_model.reference}` in available datums: {datum_names}."
            )

        if self.config.offshore_model is not None:
            if self.config.offshore_model.reference not in datum_names:
                raise ValueError(
                    f"Could not find reference `{self.config.offshore_model.reference}` in available datums: {datum_names}."
                )

        if self.tide_gauge is not None:
            if self.tide_gauge.reference not in datum_names:
                raise ValueError(
                    f"Could not find reference `{self.tide_gauge.reference}` in available datums: {datum_names}."
                )

        return self
