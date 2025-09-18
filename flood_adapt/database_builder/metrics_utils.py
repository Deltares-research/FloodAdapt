from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import tomli_w
from pydantic import BaseModel, Field, field_validator

from flood_adapt.adapter.fiat_adapter import _FIAT_COLUMNS


def combine_filters(*filters):
    """
    Combine multiple SQL filter strings with AND operators.

    Parameters
    ----------
    *filters : str
        Variable number of filter strings to combine.

    Returns
    -------
    str
        Combined filter string with AND operators, excluding empty filters.
    """
    return " AND ".join(f for f in filters if f)


def pascal_case(s):
    """
    Convert a string to PascalCase.

    Parameters
    ----------
    s : str
        Input string to convert.

    Returns
    -------
    str
        String converted to PascalCase.
    """
    return "".join(word.capitalize() for word in s.split())


class FieldMapping(BaseModel):
    """
    Represents a mapping of a database field to a list of allowed values.

    Parameters
    ----------
    field_name : str
        The name of the database field/column
    values : List[str]
        List of values that should match this field

    Methods
    -------
    to_sql_filter()
        Generate SQL filter string for this field mapping.
    """

    field_name: str
    values: List[str]

    def to_sql_filter(self) -> str:
        """
        Generate SQL filter string for this field mapping.

        Returns
        -------
        str
            SQL WHERE clause condition string for this field mapping.
        """
        quoted_values = ", ".join([f"'{v}'" for v in self.values])
        return f"`{self.field_name}` IN ({quoted_values})"


class TypeMapping(BaseModel):
    """
    Container for multiple field mappings that define object type filtering.

    Parameters
    ----------
    mappings : List[FieldMapping]
        List of field mappings that together define the type criteria

    Methods
    -------
    add_mapping(field_name, values)
        Add a new field mapping.
    to_sql_filter()
        Generate combined SQL filter string from all mappings.
    """

    mappings: List[FieldMapping] = Field(default_factory=list)

    def add_mapping(self, field_name: str, values: List[str]) -> None:
        """
        Add a new field mapping.

        Parameters
        ----------
        field_name : str
            Name of the database field.
        values : List[str]
            List of allowed values for this field.
        """
        self.mappings.append(FieldMapping(field_name=field_name, values=values))

    def to_sql_filter(self) -> str:
        """
        Generate combined SQL filter string from all mappings.

        Returns
        -------
        str
            Combined SQL WHERE clause condition string.
        """
        if not self.mappings:
            return ""
        filter_parts = [mapping.to_sql_filter() for mapping in self.mappings]
        return " AND ".join(filter_parts)


class MetricModel(BaseModel):
    """
    Represents a metric configuration for infometric analysis.

    Parameters
    ----------
    name : str
        The short name of the metric.
    long_name : Optional[str], default=None
        The long descriptive name of the metric. Defaults to `name` if not provided.
    show_in_metrics_table : Optional[bool], default=True
        Indicates whether the metric should be displayed in the metrics table.
    description : Optional[str], default=None
        A detailed description of the metric. Defaults to `name` if not provided.
    select : str
        The SQL select statement or expression for the metric.
    filter : Optional[str], default=""
        An optional SQL filter to apply to the metric. Defaults to no filter.

    Methods
    -------
    set_defaults(value, info)
        Sets default values for `long_name` and `description` fields using the `name` field if they are not provided.
    """

    name: str
    long_name: Optional[str] = None
    show_in_metrics_table: Optional[bool] = True
    description: Optional[str] = None
    select: str
    filter: Optional[str] = ""  # This defaults to no filter

    @field_validator("long_name", "description", mode="after")
    @classmethod
    def set_defaults(cls, value, info):
        """
        Set default values for long_name and description fields.

        Parameters
        ----------
        value : Any
            The current field value.
        info : Any
            Field validation info containing all field values.

        Returns
        -------
        str
            The field value or the default value from 'name' field.
        """
        # info.data contains all field values
        if value is None:
            # Use 'name' field as default
            return info.data.get("name")
        return value


class ImpactCategoriesModel(BaseModel):
    """
    Model for defining impact categories with associated colors, field, unit, and bins.

    Parameters
    ----------
    categories : list[str], default=["Minor", "Major", "Severe"]
        List of impact category names.
    colors : Optional[list[str]], default=["#ffa500", "#ff0000", "#000000"]
        List of colors corresponding to each category.
    field : str
        The database field name used for categorization.
    unit : str
        The unit of measurement for the field.
    bins : list[float]
        List of threshold values for binning the field values.

    Methods
    -------
    validate_colors_length(colors, info)
        Validate that colors list length matches categories list length.
    validate_bins_length(bins, info)
        Validate that bins list length is one less than categories list length.
    """

    categories: list[str] = Field(default_factory=lambda: ["Minor", "Major", "Severe"])
    colors: Optional[list[str]] = Field(
        default_factory=lambda: ["#ffa500", "#ff0000", "#000000"]
    )
    field: str = _FIAT_COLUMNS.inundation_depth
    unit: str
    bins: list[float]

    @field_validator("colors", mode="before")
    @classmethod
    def validate_colors_length(cls, colors, info):
        """
        Validate that colors list length matches categories list length.

        Parameters
        ----------
        colors : list[str]
            List of color values.
        info : Any
            Field validation info containing all field values.

        Returns
        -------
        list[str]
            The validated colors list.

        Raises
        ------
        ValueError
            If colors length doesn't match categories length.
        """
        categories = info.data.get("categories")
        if categories and colors and len(colors) != len(categories):
            raise ValueError("Length of 'colors' must match length of 'categories'.")
        return colors

    @field_validator("bins", mode="before")
    @classmethod
    def validate_bins_length(cls, bins, info):
        """
        Validate that bins list length is one less than categories list length.

        Parameters
        ----------
        bins : list[float]
            List of bin threshold values.
        info : Any
            Field validation info containing all field values.

        Returns
        -------
        list[float]
            The validated bins list.

        Raises
        ------
        ValueError
            If bins length is not one less than categories length.
        """
        categories = info.data.get("categories")
        if categories and len(bins) != len(categories) - 1:
            raise ValueError(
                "Length of 'bins' must be one less than length of 'categories'."
            )
        return bins


class BuildingsInfographicModel(BaseModel):
    """
    Model for building infographic configuration.

    Parameters
    ----------
    types : list[str]
        List of building types.
    icons : list[str]
        List of icon names corresponding to each building type.
    type_mapping : dict[str, TypeMapping]
        Mapping of building types to their database filtering criteria.
    impact_categories : ImpactCategoriesModel
        Impact categories configuration.

    Methods
    -------
    validate_icons_length(icons, info)
        Validate that icons list length matches types list length.
    get_template(type)
        Get a pre-configured template for OSM or NSI building types.
    """

    # Define building types
    types: list[str]
    icons: list[str]
    type_mapping: dict[str, TypeMapping]
    # Define impact categories
    impact_categories: ImpactCategoriesModel

    @field_validator("icons", mode="before")
    @classmethod
    def validate_icons_length(cls, icons, info):
        """
        Validate that icons list length matches types list length.

        Parameters
        ----------
        icons : list[str]
            List of icon names.
        info : Any
            Field validation info containing all field values.

        Returns
        -------
        list[str]
            The validated icons list.

        Raises
        ------
        ValueError
            If icons length doesn't match types length.
        """
        types = info.data.get("types")
        if types and len(icons) != len(types):
            raise ValueError("Length of 'icons' must equal to the length of 'types'.")
        return icons

    @staticmethod
    def get_template(type: Literal["OSM", "NSI"]):
        """
        Get a pre-configured template for building infographics.

        Parameters
        ----------
        type : Literal["OSM", "NSI"]
            The database type to create a template for.

        Returns
        -------
        BuildingsInfographicModel
            Pre-configured building infographic model.
        """
        if type == "OSM":
            config = BuildingsInfographicModel(
                types=["Residential", "Commercial", "Industrial"],
                icons=["house", "cart", "factory"],
                type_mapping={
                    "Residential": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name=_FIAT_COLUMNS.primary_object_type,
                                values=["residential"],
                            )
                        ]
                    ),
                    "Commercial": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name=_FIAT_COLUMNS.primary_object_type,
                                values=["commercial"],
                            )
                        ]
                    ),
                    "Industrial": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name=_FIAT_COLUMNS.primary_object_type,
                                values=["industrial"],
                            )
                        ]
                    ),
                },
                impact_categories=ImpactCategoriesModel(
                    unit="meters", bins=[0.25, 1.5]
                ),
            )
        elif type == "NSI":
            config = BuildingsInfographicModel(
                types=[
                    "Residential",
                    "Commercial",
                    "Health facilities",
                    "Schools",
                    "Emergency facilities",
                ],
                icons=["house", "cart", "hospital", "school", "firetruck"],
                type_mapping={
                    "Residential": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name=_FIAT_COLUMNS.primary_object_type,
                                values=["RES"],
                            )
                        ]
                    ),
                    "Commercial": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name="Secondary Object Type",
                                values=[
                                    "COM1",
                                    "COM2",
                                    "COM3",
                                    "COM4",
                                    "COM5",
                                    "COM8",
                                    "COM9",
                                ],
                            )
                        ]
                    ),
                    "Health facilities": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name="Secondary Object Type",
                                values=["RES6", "COM6", "COM7"],
                            )
                        ]
                    ),
                    "Schools": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name="Secondary Object Type",
                                values=["EDU1", "EDU2"],
                            )
                        ]
                    ),
                    "Emergency facilities": TypeMapping(
                        mappings=[
                            FieldMapping(
                                field_name="Secondary Object Type", values=["GOV2"]
                            )
                        ]
                    ),
                },
                impact_categories=ImpactCategoriesModel(unit="feet", bins=[1, 6]),
            )
        return config


class SviModel(BaseModel):
    """
    Model for Social Vulnerability Index (SVI) configuration.

    Parameters
    ----------
    classes : list[str], default=["Low", "High"]
        List of vulnerability class names.
    colors : list[str], default=["#D5DEE1", "#88A2AA"]
        List of colors corresponding to each vulnerability class.
    thresholds : list[float], default=[0.7]
        List of threshold values for vulnerability classification.

    Methods
    -------
    validate_colors_length(colors, info)
        Validate that colors list length matches classes list length.
    validate_thresholds_length(thresholds, info)
        Validate that thresholds list length is one less than classes list length.
    """

    classes: list[str] = Field(default_factory=lambda: ["Low", "High"])
    colors: list[str] = Field(default_factory=lambda: ["#D5DEE1", "#88A2AA"])
    thresholds: list[float] = Field(default_factory=lambda: [0.7])

    @field_validator("colors", mode="before")
    @classmethod
    def validate_colors_length(cls, colors, info):
        """
        Validate that colors list length matches classes list length.

        Parameters
        ----------
        colors : list[str]
            List of color values.
        info : Any
            Field validation info containing all field values.

        Returns
        -------
        list[str]
            The validated colors list.

        Raises
        ------
        ValueError
            If colors length doesn't match classes length.
        """
        classes = info.data.get("classes")
        if classes and colors and len(colors) != len(classes):
            raise ValueError("Length of 'colors' must match length of 'classes'.")
        return colors

    @field_validator("thresholds", mode="before")
    @classmethod
    def validate_thresholds_length(cls, thresholds, info):
        """
        Validate that thresholds list length is one less than classes list length.

        Parameters
        ----------
        thresholds : list[float]
            List of threshold values.
        info : Any
            Field validation info containing all field values.

        Returns
        -------
        list[float]
            The validated thresholds list.

        Raises
        ------
        ValueError
            If thresholds length is not one less than classes length.
        """
        classes = info.data.get("classes")
        if classes and len(thresholds) != len(classes) - 1:
            raise ValueError(
                "Length of 'thresholds' must be one less than length of 'classes'."
            )
        return thresholds


class HomesInfographicModel(BaseModel):
    """
    Model for Homes and SVI (Social Vulnerability Index) infographic configuration.

    Parameters
    ----------
    svi : SviModel
        SVI classification configuration.
    mapping : TypeMapping
        Database field mapping for filtering relevant objects.
    impact_categories : ImpactCategoriesModel
        Impact categories configuration.

    Methods
    -------
    get_template(svi_threshold, type)
        Get a pre-configured template for SVI infographics.
    """

    svi: Optional[SviModel] = None
    mapping: TypeMapping
    impact_categories: ImpactCategoriesModel

    @staticmethod
    def get_template(
        type: Literal["OSM", "NSI"] = "OSM", svi_threshold: Optional[float] = None
    ):
        """
        Get a pre-configured template for SVI infographics.

        Parameters
        ----------
        svi_threshold : Optional[float], default=None
            The SVI threshold value for vulnerability classification. If not provided, SVI will be None.
        type : Literal["OSM", "NSI"], default="OSM"
            The database type to create a template for.

        Returns
        -------
        HomesInfographicModel
            Pre-configured Homes infographic model.
        """
        if svi_threshold is not None:
            svi_model = SviModel(thresholds=[svi_threshold])
        else:
            svi_model = None

        if type == "OSM":
            config = HomesInfographicModel(
                svi=svi_model,
                mapping=TypeMapping(
                    mappings=[
                        FieldMapping(
                            field_name=_FIAT_COLUMNS.primary_object_type,
                            values=["residential"],
                        )
                    ]
                ),
                impact_categories=ImpactCategoriesModel(
                    categories=["Flooded", "Displaced"],
                    colors=None,
                    unit="meters",
                    bins=[1.5],
                ),
            )
        elif type == "NSI":
            config = HomesInfographicModel(
                svi=svi_model,
                mapping=TypeMapping(
                    mappings=[
                        FieldMapping(
                            field_name=_FIAT_COLUMNS.primary_object_type, values=["RES"]
                        )
                    ]
                ),
                impact_categories=ImpactCategoriesModel(
                    categories=["Flooded", "Displaced"],
                    colors=None,
                    unit="feet",
                    bins=[6],
                ),
            )
        return config


class RoadsInfographicModel(BaseModel):
    """
    Model for roads infographic configuration.

    Parameters
    ----------
    categories : list[str], default=["Slight", "Minor", "Major", "Severe"]
        List of road impact category names.
    colors : list[str], default=["#e0f7fa", "#80deea", "#26c6da", "#006064"]
        List of colors corresponding to each category.
    icons : list[str], default=["walking_person", "car", "truck", "ambulance"]
        List of icon names for each category.
    users : list[str], default=["Pedestrians", "Cars", "Trucks", "Rescue vehicles"]
        List of road user types for each category.
    thresholds : list[float]
        List of threshold values for categorizing road impacts.
    field : str, default=_FIAT_COLUMNS.inundation_depth
        The database field name used for categorization.
    unit : str
        The unit of measurement for the field.
    road_length_field : str, default=_FIAT_COLUMNS.segment_length
        The database field name containing road segment lengths.

    Methods
    -------
    validate_lengths(v, info)
        Validate that all list attributes have the same length.
    get_template(unit_system)
        Get a pre-configured template for metric or imperial units.
    """

    categories: list[str] = Field(
        default_factory=lambda: ["Slight", "Minor", "Major", "Severe"]
    )
    colors: list[str] = Field(
        default_factory=lambda: ["#e0f7fa", "#80deea", "#26c6da", "#006064"]
    )
    icons: list[str] = Field(
        default_factory=lambda: ["walking_person", "car", "truck", "ambulance"]
    )
    users: list[str] = Field(
        default_factory=lambda: ["Pedestrians", "Cars", "Trucks", "Rescue vehicles"]
    )
    thresholds: list[float]
    field: str = _FIAT_COLUMNS.inundation_depth
    unit: str
    road_length_field: str = _FIAT_COLUMNS.segment_length

    @field_validator("categories", mode="after")
    @classmethod
    def validate_lengths(cls, v, info):
        """
        Validate that all list attributes have the same length.

        Parameters
        ----------
        v : list[str]
            The categories list.
        info : Any
            Field validation info containing all field values.

        Returns
        -------
        list[str]
            The validated categories list.

        Raises
        ------
        ValueError
            If list attributes don't have the same length.
        """
        # Check that categories, colors, icons, users, thresholds have the same length
        attrs = ["categories", "colors", "icons", "users", "thresholds"]
        lengths = [len(info.data.get(attr, [])) for attr in attrs]
        if len(set(lengths)) > 1:
            raise ValueError(
                f"Attributes {attrs} must all have the same length, got lengths: {lengths}"
            )
        return v

    @staticmethod
    def get_template(unit_system: Literal["metric", "imperial"]):
        """
        Get a pre-configured template for roads infographics.

        Parameters
        ----------
        unit_system : Literal["metric", "imperial"]
            The unit system to use for thresholds and measurements.

        Returns
        -------
        RoadsInfographicModel
            Pre-configured roads infographic model.
        """
        if unit_system == "metric":
            config = RoadsInfographicModel(
                thresholds=[0.1, 0.2, 0.4, 0.8],
                unit="meters",
            )
        elif unit_system == "imperial":
            config = RoadsInfographicModel(
                thresholds=[0.3, 0.5, 1, 2],
                unit="feet",
            )
        return config


class EventInfographicModel(BaseModel):
    """
    Model for event-based infographic configuration.

    Parameters
    ----------
    buildings : Optional[BuildingsInfographicModel], default=None
        Buildings infographic configuration.
    svi : Optional[SviInfographicModel], default=None
        SVI infographic configuration.
    roads : Optional[RoadsInfographicModel], default=None
        Roads infographic configuration.
    """

    buildings: Optional[BuildingsInfographicModel] = None
    svi: Optional[HomesInfographicModel] = None
    roads: Optional[RoadsInfographicModel] = None


class FloodExceedanceModel(BaseModel):
    """
    Model for flood exceedance probability configuration.

    Parameters
    ----------
    column : str, default=_FIAT_COLUMNS.inundation_depth
        The database column name for flood depth measurements.
    threshold : float, default=0.1
        The flood depth threshold value.
    unit : str, default="meters"
        The unit of measurement for the threshold.
    period : int, default=30
        The time period in years for exceedance analysis.
    """

    column: str = _FIAT_COLUMNS.inundation_depth
    threshold: float = 0.1
    unit: str = "meters"
    period: int = 30


class RiskInfographicModel(BaseModel):
    """
    Model for risk-based infographic configuration.

    Parameters
    ----------
    homes : HomesInfographicModel
        Homes infographic configuration.
    flood_exceedances : FloodExceedanceModel
        Flood exceedance configuration.

    Methods
    -------
    get_template(type, svi_threshold)
        Get a pre-configured template for risk infographics.
    """

    homes: HomesInfographicModel
    flood_exceedance: FloodExceedanceModel

    @staticmethod
    def get_template(
        type: Literal["OSM", "NSI"], svi_threshold: Optional[float] = None
    ):
        """
        Get a pre-configured template for risk infographics.

        Parameters
        ----------
        type : Literal["OSM", "NSI"]
            The database type to create a template for.
        svi_threshold : Optional[float], default=None
            The SVI threshold value for vulnerability classification.

        Returns
        -------
        RiskInfographicModel
            Pre-configured risk infographic model.
        """
        if type == "OSM":
            config = RiskInfographicModel(
                homes=HomesInfographicModel.get_template(
                    type="OSM", svi_threshold=svi_threshold
                ),
                flood_exceedance=FloodExceedanceModel(),
            )
        elif type == "NSI":
            config = RiskInfographicModel(
                homes=HomesInfographicModel.get_template(
                    type="NSI", svi_threshold=svi_threshold
                ),
                flood_exceedance=FloodExceedanceModel(unit="feet", threshold=0.2),
            )
        return config


def get_filter(
    type_mapping: TypeMapping,
    cat_field: str,
    cat_idx: int,
    bins: list[float],
    base_filt="",
) -> str:
    """
    Construct a SQL filter string based on provided type mapping and category criteria.

    Parameters
    ----------
    type_mapping : TypeMapping
        TypeMapping object containing field mappings to filter on.
    cat_field : str
        Name of the field representing the category in the database.
    cat_idx : int
        Index indicating which category bin to use for filtering.
    bins : list[float]
        List of bin thresholds for the category field.
    base_filt : str, default=""
        Additional base filter string to prepend.

    Returns
    -------
    str
        A SQL filter string combining type and category conditions.
    """
    # Build type filters using TypeMapping
    type_filter = type_mapping.to_sql_filter()

    # Add category filter
    if cat_idx == 0:
        cat_filter = f"`{cat_field}` <= {bins[0]}"
    elif cat_idx == len(bins):
        cat_filter = f"`{cat_field}` > {bins[-1]}"
    else:
        cat_filter = (
            f"`{cat_field}` <= {bins[cat_idx]} AND `{cat_field}` > {bins[cat_idx-1]}"
        )

    return combine_filters(base_filt, type_filter, cat_filter)


class Metrics:
    """Main class for managing impact metrics configuration and generation."""

    def __init__(self, dmg_unit: str, return_periods: list[float]):
        """
        Initialize the Metrics class.

        Parameters
        ----------
        dmg_unit : str
            The unit of measurement for damage values.
        return_periods : list[float]
            List of return periods in years for risk analysis.
        """
        self.dmg_unit = dmg_unit
        self.return_periods = return_periods

        # Initialize all metric lists as empty instance attributes
        self.mandatory_metrics_event: list[MetricModel] = []
        self.mandatory_metrics_risk: list[MetricModel] = []
        self.additional_metrics_event: list[MetricModel] = []
        self.additional_metrics_risk: list[MetricModel] = []
        self.infographics_metrics_event: list[MetricModel] = []
        self.infographics_metrics_risk: list[MetricModel] = []
        self.additional_risk_configs: dict = {}
        self.infographics_config: dict = {}

    @staticmethod
    def write_metrics(metrics, path, aggr_levels=[]):
        """
        Write metrics configuration to a TOML file.

        Parameters
        ----------
        metrics : list[MetricModel]
            List of metric models to write.
        path : Union[str, Path]
            Path to the output TOML file.
        aggr_levels : list[str], default=[]
            List of aggregation levels.
        """
        attrs = {}
        attrs["aggregateBy"] = aggr_levels
        attrs["queries"] = [metric.model_dump() for metric in metrics]

        # Save metrics configuration
        with open(path, "wb") as f:
            tomli_w.dump(attrs, f)

    def write(
        self,
        metrics_path: Union[str, Path, PathLike],
        aggregation_levels: List[str],
        infographics_path: Optional[Union[str, Path, PathLike]] = None,
    ) -> None:
        """
        Write all metrics (mandatory, additional, and infographics) to TOML files.

        Parameters
        ----------
        metrics_path : Union[str, Path, PathLike]
            The directory path where the metrics configuration files will be saved.
        aggregation_levels : List[str]
            A list of aggregation levels to include in the metrics configuration files.
        infographics_path : Optional[Union[str, Path, PathLike]], default=None
            The directory path where infographics configuration files will be saved.
            Required if infographics configurations are present.

        Raises
        ------
        ValueError
            If infographics_path is None but infographics configurations exist.
        """
        path_im = Path(metrics_path)
        path_im.mkdir(parents=True, exist_ok=True)

        # Write mandatory event metrics
        self.write_metrics(
            self.mandatory_metrics_event,
            path_im / "mandatory_metrics_config.toml",
            aggregation_levels,
        )

        # Write mandatory risk metrics
        if self.mandatory_metrics_risk:
            self.write_metrics(
                self.mandatory_metrics_risk,
                path_im / "mandatory_metrics_config_risk.toml",
                aggregation_levels,
            )

        # Write additional event metrics if any
        if self.additional_metrics_event:
            self.write_metrics(
                self.additional_metrics_event,
                path_im / "additional_metrics_config.toml",
                aggregation_levels,
            )

        # Write additional risk metrics if any
        if self.additional_metrics_risk:
            self.write_metrics(
                self.additional_metrics_risk,
                path_im / "additional_metrics_config_risk.toml",
                aggregation_levels,
            )

        # Write infographics event metrics if any
        if (
            hasattr(self, "infographics_metrics_event")
            and self.infographics_metrics_event
        ):
            self.write_metrics(
                self.infographics_metrics_event,
                path_im / "infographic_metrics_config.toml",
                aggregation_levels,
            )

        # Write infographics risk metrics if any
        if (
            hasattr(self, "infographics_metrics_risk")
            and self.infographics_metrics_risk
        ):
            self.write_metrics(
                self.infographics_metrics_risk,
                path_im / "infographic_metrics_config_risk.toml",
                aggregation_levels,
            )

        # Save additional risk configurations if available
        if hasattr(self, "additional_risk_configs") and self.additional_risk_configs:
            with open(path_im / "metrics_additional_risk_configs.toml", "wb") as f:
                tomli_w.dump(self.additional_risk_configs, f)

        # Save infographics configuration if available
        if self.infographics_config:
            if infographics_path is None:
                raise ValueError(
                    "infographics_path must be provided to save infographics configuration."
                )
            infographics_path = Path(infographics_path)
            infographics_path.mkdir(parents=True, exist_ok=True)
            if "buildings" in self.infographics_config:
                with open(infographics_path / "config_charts.toml", "wb") as f:
                    tomli_w.dump(self.infographics_config["buildings"], f)
            if "svi" in self.infographics_config:
                with open(infographics_path / "config_people.toml", "wb") as f:
                    tomli_w.dump(self.infographics_config["svi"], f)
            if "roads" in self.infographics_config:
                with open(infographics_path / "config_roads.toml", "wb") as f:
                    tomli_w.dump(self.infographics_config["roads"], f)
            if "risk" in self.infographics_config:
                with open(infographics_path / "config_risk_charts.toml", "wb") as f:
                    tomli_w.dump(self.infographics_config["risk"], f)

    def create_mandatory_metrics_event(self) -> list[MetricModel]:
        """
        Create mandatory metrics for event analysis.

        Returns
        -------
        list[MetricModel]
            List of mandatory event metrics.
        """
        self.mandatory_metrics_event.append(
            MetricModel(
                name="TotalDamageEvent",
                description="Total building damage",
                long_name=f"Total building damage ({self.dmg_unit})",
                select=f"SUM(`{_FIAT_COLUMNS.total_damage}`)",
                filter="",
                show_in_metrics_table=True,
            )
        )
        return self.mandatory_metrics_event

    def create_mandatory_metrics_risk(self) -> list[MetricModel]:
        """
        Create mandatory metrics for risk analysis.

        Returns
        -------
        list[MetricModel]
            List of mandatory risk metrics.
        """
        self.mandatory_metrics_risk.append(
            MetricModel(
                name="ExpectedAnnualDamages",
                description="Expected annual damages",
                long_name=f"Expected annual damages ({self.dmg_unit})",
                select=f"SUM(`{_FIAT_COLUMNS.risk_ead}`)",
                filter="",
                show_in_metrics_table=True,
            )
        )
        for rp in self.return_periods:
            self.mandatory_metrics_risk.append(
                MetricModel(
                    name=f"TotalDamageRP{int(rp)}",
                    description=f"Total damage with return period of {int(rp)} years",
                    long_name=f"Total building damage - {int(rp)}Y ({self.dmg_unit})",
                    select=f"SUM(`{_FIAT_COLUMNS.total_damage_rp.format(years=int(rp))}`)",
                    filter="",
                    show_in_metrics_table=True,
                )
            )

        return self.mandatory_metrics_risk

    def add_event_metric(self, metric: MetricModel) -> None:
        """
        Add an additional event metric.

        Parameters
        ----------
        metric : MetricModel
            The metric to add to the additional event metrics list.

        Raises
        ------
        ValueError
            If a metric with the same name already exists.
        """
        if any(m.name == metric.name for m in self.additional_metrics_event):
            raise ValueError(f"Event metric with name '{metric.name}' already exists.")
        self.additional_metrics_event.append(metric)

    def add_risk_metric(self, metric: MetricModel) -> None:
        """
        Add an additional risk metric.

        Parameters
        ----------
        metric : MetricModel
            The metric to add to the additional risk metrics list.

        Raises
        ------
        ValueError
            If a metric with the same name already exists.
        """
        if any(m.name == metric.name for m in self.additional_metrics_risk):
            raise ValueError(f"Risk metric with name '{metric.name}' already exists.")
        self.additional_metrics_risk.append(metric)

    def create_infographics_metrics_event(
        self,
        config: EventInfographicModel,
        base_filt=f"`{_FIAT_COLUMNS.total_damage}` > 0",
    ) -> list[MetricModel]:
        """
        Create infographic metrics for event analysis.

        Parameters
        ----------
        config : EventInfographicModel
            Configuration for event infographics.
        base_filt : str, default="`Total Damage` > 0"
            Base SQL filter to apply to all metrics.

        Returns
        -------
        list[MetricModel]
            List of infographic event metrics.
        """
        # Generate queries for all building types and categories
        if config.buildings:
            self._setup_buildings(config.buildings, base_filt)
        if config.svi:
            self._setup_svi(config.svi, base_filt)
        if config.roads:
            self._setup_roads(config.roads)
        return self.infographics_metrics_event

    def create_infographics_metrics_risk(
        self, config: RiskInfographicModel, base_filt=f"`{_FIAT_COLUMNS.risk_ead}` > 0"
    ) -> list[MetricModel]:
        """
        Create infographic metrics for risk analysis.

        Parameters
        ----------
        config : RiskInfographicModel
            Configuration for risk infographics.
        base_filt : str, default="`Risk (EAD)` > 0"
            Base SQL filter to apply to all metrics.

        Returns
        -------
        list[MetricModel]
            List of infographic risk metrics.
        """
        infographics_metrics_risk = []

        # Get mapping from config.svi
        mapping = config.homes.mapping

        # Build type filter string using TypeMapping
        type_cond = mapping.to_sql_filter()

        # FloodedHomes (Exceedance Probability > 50)
        fe = config.flood_exceedance
        filter_str = combine_filters(
            "`Exceedance Probability` > 50", type_cond, base_filt
        )
        infographics_metrics_risk.append(
            MetricModel(
                name="LikelyFloodedHomes",
                description=f"Homes likely to flood ({fe.column} > {fe.threshold} {fe.unit}) in {fe.period} year period",
                select="COUNT(*)",
                filter=filter_str,
                long_name=f"Homes likely to flood in {fe.period}-year period (#)",
                show_in_metrics_table=True,
            )
        )

        # ImpactedHomes for each RP - use class return periods and config SVI thresholds
        rps = self.return_periods
        if config.homes.svi is not None:
            svi_thresholds = config.homes.svi.thresholds
            svi_classes = config.homes.svi.classes
        else:
            svi_thresholds = []
            svi_classes = []

        for rp in rps:
            # ImpactedHomes{RP} (all homes)
            filter_str = combine_filters(
                f"`{fe.column} ({int(rp)}Y)` >= {fe.threshold}", type_cond, base_filt
            )
            infographics_metrics_risk.append(
                MetricModel(
                    name=f"ImpactedHomes{int(rp)}Y",
                    description=f"Number of homes impacted ({fe.column} > {fe.threshold} {fe.unit}) in the {int(rp)}-year event",
                    select="COUNT(*)",
                    filter=filter_str,
                    long_name=f"Flooded homes - RP{int(rp)} (#)",
                    show_in_metrics_table=True,
                )
            )

            # Create metrics for each SVI class
            for j, svi_class in enumerate(svi_classes):
                # Build SVI condition based on thresholds
                if j == 0:
                    # First class: SVI < first_threshold
                    svi_cond = f"`SVI` < {svi_thresholds[0]}"
                elif j == len(svi_classes) - 1:
                    # Last class: SVI >= last_threshold
                    svi_cond = f"`SVI` >= {svi_thresholds[-1]}"
                else:
                    # Middle classes: previous_threshold <= SVI < current_threshold
                    svi_cond = f"`SVI` >= {svi_thresholds[j-1]} AND `SVI` < {svi_thresholds[j]}"

                # Clean class name for metric naming (remove spaces, special chars)
                clean_class_name = svi_class.replace(" ", "").replace("-", "")

                filter_str = combine_filters(
                    f"`{fe.column} ({int(rp)}Y)` >= {fe.threshold}",
                    type_cond,
                    svi_cond,
                    base_filt,
                )

                infographics_metrics_risk.append(
                    MetricModel(
                        name=f"ImpactedHomes{int(rp)}Y{clean_class_name}SVI",
                        description=f"{svi_class} vulnerable homes impacted ({fe.column} > {fe.threshold} {fe.unit}) in the {int(rp)}-year event",
                        select="COUNT(*)",
                        filter=filter_str,
                        long_name=f"Flooded homes with {svi_class} vulnerability - RP{int(rp)} (#)",
                        show_in_metrics_table=True,
                    )
                )

        self.infographics_metrics_risk = infographics_metrics_risk
        self.additional_risk_configs = {
            "flood_exceedance": {
                "column": fe.column,
                "threshold": fe.threshold,
                "period": fe.period,
            }
        }
        self._make_infographics_config_risk(config)
        return self.infographics_metrics_risk

    def _setup_buildings(self, config: BuildingsInfographicModel, base_filt) -> None:
        """
        Configure building metrics and configuration for infographics.

        Parameters
        ----------
        config : BuildingsInfographicModel
            Building infographic configuration.
        base_filt : str
            Base SQL filter to apply.
        """
        # Generate queries for all building types and categories
        building_queries = []
        for btype in config.types:
            type_mapping = config.type_mapping.get(btype, TypeMapping())
            for i, cat in enumerate(config.impact_categories.categories):
                query_name = f"{pascal_case(btype)}{pascal_case(cat)}Count"
                desc = (
                    f"Number of {btype.lower()} buildings with {cat.lower()} flooding"
                )
                long_name = f"{btype} with {cat.lower()} flooding (#)"
                filter_str = get_filter(
                    type_mapping=type_mapping,
                    cat_field=config.impact_categories.field,
                    cat_idx=i,
                    bins=config.impact_categories.bins,
                    base_filt=base_filt,
                )
                building_queries.append(
                    MetricModel(
                        name=query_name,
                        select="COUNT(*)",
                        filter=filter_str,
                        description=desc,
                        long_name=long_name,
                    )
                )
        self.infographics_metrics_event.extend(building_queries)
        self.infographics_config["buildings"] = (
            self._make_infographics_config_buildings(config)
        )

    def _setup_svi(self, config: HomesInfographicModel, base_filt) -> None:
        """
        Configure SVI metrics and configuration for infographics.

        Parameters
        ----------
        config : SviInfographicModel
            SVI infographic configuration.
        base_filt : str
            Base SQL filter to apply.
        """
        # Generate queries for all SVI categories and vulnerability levels
        svi_queries = []
        cat_field = config.impact_categories.field
        bins = config.impact_categories.bins
        if config.svi is not None:
            svi_thresholds = config.svi.thresholds
            svi_classes = config.svi.classes
        else:
            svi_thresholds = []
            svi_classes = []
        mapping = config.mapping

        for i, cat in enumerate(config.impact_categories.categories):
            for j, svi_class in enumerate(svi_classes):
                # Build SVI condition based on thresholds
                if j == 0:
                    # First class: SVI < first_threshold
                    svi_cond = f"`SVI` < {svi_thresholds[0]}"
                elif j == len(svi_classes) - 1:
                    # Last class: SVI >= last_threshold
                    svi_cond = f"`SVI` >= {svi_thresholds[-1]}"
                else:
                    # Middle classes: previous_threshold <= SVI < current_threshold
                    svi_cond = f"`SVI` >= {svi_thresholds[j-1]} AND `SVI` < {svi_thresholds[j]}"

                # Build impact category condition based on bins
                if i == 0:
                    # First category: field <= first_bin
                    cat_cond = f"`{cat_field}` <= {bins[0]}"
                elif i == len(config.impact_categories.categories) - 1:
                    # Last category: field > last_bin
                    cat_cond = f"`{cat_field}` > {bins[-1]}"
                else:
                    # Middle categories: previous_bin < field <= current_bin
                    cat_cond = (
                        f"`{cat_field}` > {bins[i-1]} AND `{cat_field}` <= {bins[i]}"
                    )

                # Build type filter using TypeMapping
                type_cond = mapping.to_sql_filter()

                filter_str = combine_filters(type_cond, cat_cond, svi_cond, base_filt)

                name = f"{cat}{svi_class.replace(' ', '')}Vulnerability"
                desc = f"Number of {cat.lower()} homes with {svi_class.lower()} vulnerability"
                long_name = f"{cat} Homes - {svi_class} Vulnerability (#)"

                svi_queries.append(
                    MetricModel(
                        name=name,
                        select="COUNT(*)",
                        filter=filter_str,
                        description=desc,
                        long_name=long_name,
                        show_in_metrics_table=True,
                    )
                )
        self.infographics_metrics_event.extend(svi_queries)
        self.infographics_config["svi"] = self._make_infographics_config_svi(config)

    def _setup_roads(self, config: RoadsInfographicModel) -> None:
        """
        Configure roads metrics and configuration for infographics.

        Parameters
        ----------
        config : RoadsInfographicModel
            Roads infographic configuration.
        """
        # Generate queries for all road categories
        road_queries = []
        cat_field = config.field
        thresholds = config.thresholds
        road_length_field = config.road_length_field

        if config.unit == "meters":
            unit_conversion = 1 / 1000
            unit = "Kilometers"
        elif config.unit == "feet":
            unit_conversion = 1 / 5280
            unit = "Miles"

        for i, cat in enumerate(config.categories):
            name = f"{pascal_case(cat)}FloodedRoadsLength"
            desc = f"{unit} of roads disrupted for {config.users[i].lower()}"
            long_name = f"Length of roads with {cat.lower()} flooding ({unit})"
            select = f"SUM(`{road_length_field}`)*{unit_conversion}"
            filter_str = f"`{cat_field}` >= {thresholds[i]}"
            road_queries.append(
                MetricModel(
                    name=name,
                    description=desc,
                    long_name=long_name,
                    select=select,
                    filter=filter_str,
                    show_in_metrics_table=True,
                )
            )
        self.infographics_metrics_event.extend(road_queries)
        self.infographics_config["roads"] = self._make_infographics_config_roads(config)

    @staticmethod
    def _make_infographics_config_buildings(
        buildings_config: BuildingsInfographicModel,
    ) -> Dict[str, Any]:
        """
        Create infographics configuration dictionary for buildings.

        Parameters
        ----------
        buildings_config : BuildingsInfographicModel
            Building infographic configuration.

        Returns
        -------
        Dict[str, Any]
            Configuration dictionary for building infographics.
        """
        image_path = "{image_path}"
        # Default plot configuration, matching your existing template:
        # Dynamically generate the Info text based on the number of categories and bins
        info_lines = [f"{buildings_config.impact_categories.field}:<br>"]
        for idx, cat in enumerate(buildings_config.impact_categories.categories):
            if idx < len(buildings_config.impact_categories.bins):
                info_lines.append(
                    f"    {cat}: <={buildings_config.impact_categories.bins[idx]} {buildings_config.impact_categories.unit}<br>"
                )
            else:
                # Last category: greater than last bin
                info_lines.append(
                    f"    {cat}: >{buildings_config.impact_categories.bins[-1]} {buildings_config.impact_categories.unit}<br>"
                )

        other_config: Dict[str, Any] = {
            "Plot": {
                "image_scale": 0.15,
                "numbers_font": 20,
                "height": 350,
                "width": 1200,
            },
            "Title": {"text": "Building Impacts", "font": 30},
            "Subtitle": {"font": 25},
            "Legend": {"font": 20},
            "Info": {
                "text": "".join(info_lines),
                "image": "https://openclipart.org/image/800px/302413",
                "scale": 0.1,
            },
        }

        cfg: Dict[str, Any] = {
            "Charts": {},
            "Categories": {},
            "Slices": {},
            "Other": other_config,
        }

        # Categories block - keys have no special characters, Names are original
        if buildings_config.impact_categories.colors is not None:
            for k, cat in enumerate(buildings_config.impact_categories.categories):
                clean_cat_key = pascal_case(cat.replace(" ", "").replace("-", ""))
                cfg["Categories"][clean_cat_key] = {
                    "Name": cat,  # Original name
                    "Color": buildings_config.impact_categories.colors[k],
                }

        # Charts block - keys have no special characters, Names are original
        for i, btype in enumerate(buildings_config.types):
            clean_btype_key = pascal_case(btype.replace(" ", "").replace("-", ""))
            cfg["Charts"][clean_btype_key] = {
                "Name": btype,  # Original name
                "Image": f"{image_path}/{buildings_config.icons[i]}.png",
            }

        # Slices block - reference Chart and Category Names (not keys)
        for i, btype in enumerate(buildings_config.types):
            for cat in buildings_config.impact_categories.categories:
                clean_cat_key = pascal_case(cat.replace(" ", "").replace("-", ""))
                clean_btype_key = pascal_case(btype.replace(" ", "").replace("-", ""))
                slice_key = f"{clean_cat_key}{clean_btype_key}"
                cfg["Slices"][slice_key] = {
                    "Name": f"{cat} {btype}",
                    "Query": f"{pascal_case(btype)}{pascal_case(cat)}Count",
                    "Chart": btype,  # Reference Chart Name, not key
                    "Category": cat,  # Reference Category Name, not key
                }

        return cfg

    @staticmethod
    def _make_infographics_config_svi(
        svi_config: HomesInfographicModel,
    ) -> Dict[str, Any]:
        """
        Create infographics configuration dictionary for SVI.

        Parameters
        ----------
        svi_config : SviInfographicModel
            SVI infographic configuration.

        Returns
        -------
        Dict[str, Any]
            Configuration dictionary for SVI infographics.
        """
        image_path = "{image_path}"
        svi_classes = svi_config.svi.classes if svi_config.svi is not None else []
        charts = {}
        slices = {}
        categories_cfg = {}

        # Charts block - keys have no special characters, Names are original
        for cat in svi_config.impact_categories.categories:
            clean_cat_key = pascal_case(cat.replace(" ", "").replace("-", ""))
            charts[clean_cat_key] = {
                "Name": cat,  # Original name
                "Image": f"{image_path}/house.png",
            }

        # Categories block - keys have no special characters, Names are original
        for idx, svi_class in enumerate(svi_classes):
            color = (
                svi_config.svi.colors[idx] if svi_config.svi is not None else "#cccccc"
            )
            clean_svi_key = (
                pascal_case(svi_class.replace(" ", "").replace("-", ""))
                + "Vulnerability"
            )
            categories_cfg[clean_svi_key] = {
                "Name": f"{svi_class} Vulnerability",  # Original name with "Vulnerability"
                "Color": color,
            }

        # Slices block - reference Chart and Category Names (not keys)
        for cat in svi_config.impact_categories.categories:
            for svi_class in svi_classes:
                clean_cat_key = pascal_case(cat.replace(" ", "").replace("-", ""))
                clean_svi_key = (
                    pascal_case(svi_class.replace(" ", "").replace("-", ""))
                    + "Vulnerability"
                )
                slice_key = f"{clean_cat_key}{clean_svi_key}"
                name = f"{cat} {svi_class.lower()} vulnerability homes"
                query = (
                    f"{cat}{svi_class.replace(' ', '').replace('-', '')}Vulnerability"
                )
                slices[slice_key] = {
                    "Name": name,
                    "Query": query,
                    "Chart": cat,  # Reference Chart Name, not key
                    "Category": f"{svi_class} Vulnerability",  # Reference Category Name, not key
                }

        # Info text - dynamically build threshold information
        bins = svi_config.impact_categories.bins
        unit = svi_config.impact_categories.unit
        thresholds = svi_config.svi.thresholds if svi_config.svi is not None else []

        info_lines = [
            "Thresholds:<br>",
        ]

        # Add impact category threshold information
        for i, cat in enumerate(svi_config.impact_categories.categories):
            if i == 0:
                info_lines.append(f"    {cat}: <= {bins[0]} {unit}<br>")
            elif i == len(svi_config.impact_categories.categories) - 1:
                info_lines.append(f"    {cat}: > {bins[-1]} {unit}<br>")
            else:
                info_lines.append(f"    {cat}: {bins[i-1]} - {bins[i]} {unit}<br>")

        info_lines.append("<br>SVI Classes:<br>")

        # Add SVI threshold information
        for i, svi_class in enumerate(svi_classes):
            if i == 0:
                info_lines.append(f"    {svi_class}: < {thresholds[0]}<br>")
            elif i == len(svi_classes) - 1:
                info_lines.append(f"    {svi_class}: >= {thresholds[-1]}<br>")
            else:
                info_lines.append(
                    f"    {svi_class}: {thresholds[i-1]} - {thresholds[i]}<br>"
                )

        info_lines.extend(
            [
                "'Since some homes do not have an SVI,<br>",
                "total number of homes might be different <br>",
                "between this and the above graph.'",
            ]
        )

        other_config = {
            "Plot": {
                "image_scale": 0.15,
                "numbers_font": 20,
                "height": 350,
                "width": 600,
            },
            "Title": {"text": "Impacted Homes", "font": 30},
            "Subtitle": {"font": 25},
            "Legend": {"font": 20},
            "Info": {
                "text": "".join(info_lines),
                "image": "https://openclipart.org/image/800px/302413",
                "scale": 0.1,
            },
        }
        cfg = {
            "Charts": charts,
            "Categories": categories_cfg,
            "Slices": slices,
            "Other": other_config,
        }
        return cfg

    @staticmethod
    def _make_infographics_config_roads(
        roads_config: RoadsInfographicModel,
    ) -> Dict[str, Any]:
        """
        Create infographics configuration dictionary for roads.

        Parameters
        ----------
        roads_config : RoadsInfographicModel
            Roads infographic configuration.

        Returns
        -------
        Dict[str, Any]
            Configuration dictionary for roads infographics.
        """
        image_path = "{image_path}"

        # Charts block - key has no special characters, Name is original
        chart_key = "FloodedRoads"
        chart_name = "Flooded Roads"
        charts = {chart_key: {"Name": chart_name}}

        # Categories block - keys have no special characters, Names are original
        categories_cfg = {}
        for idx, cat in enumerate(roads_config.categories):
            clean_cat_key = (
                pascal_case(cat.replace(" ", "").replace("-", "")) + "Flooding"
            )
            cat_name = f"{cat} Flooding"
            categories_cfg[clean_cat_key] = {
                "Name": cat_name,  # Original name with "Flooding"
                "Color": roads_config.colors[idx],
                "Image": f"{image_path}/{roads_config.icons[idx]}.png",
            }

        # Slices block - reference Chart and Category Names (not keys)
        slices = {}
        for idx, cat in enumerate(roads_config.categories):
            clean_cat_key = (
                pascal_case(cat.replace(" ", "").replace("-", "")) + "Flooding"
            )
            cat_name = f"{cat} Flooding"
            query_name = f"{pascal_case(cat)}FloodedRoadsLength"
            slices[clean_cat_key] = {
                "Name": cat_name,
                "Query": query_name,
                "Chart": chart_name,  # Reference Chart Name, not key
                "Category": cat_name,  # Reference Category Name, not key
            }

        # Info text
        thresholds = roads_config.thresholds
        # Consistent unit naming
        if roads_config.unit == "feet":
            unit = "Miles"
        else:
            unit = "Kilometers"
        info_lines = ["Thresholds:<br>"]
        for user, threshold in zip(roads_config.users, thresholds):
            info_lines.append(f"    {user}: {threshold} {roads_config.unit}<br>")
        other_config = {
            "Plot": {
                "image_scale": 0.1,
                "numbers_font": 20,
                "height": 350,
                "width": 600,
            },
            "Title": {"text": "Interrupted roads", "font": 30},
            "Subtitle": {"font": 25},
            "Y_axis_title": {"text": unit},
            "Info": {
                "text": "".join(info_lines),
                "image": f"{image_path}/info.png",
                "scale": 0.1,
            },
        }
        cfg = {
            "Charts": charts,
            "Categories": categories_cfg,
            "Slices": slices,
            "Other": other_config,
        }
        return cfg

    def _make_infographics_config_risk(self, risk_config: RiskInfographicModel) -> dict:
        """
        Create infographics configuration dictionary for risk infographics.

        Parameters
        ----------
        risk_config : RiskInfographicModel
            Risk infographic configuration.

        Returns
        -------
        dict
            Configuration dictionary for risk infographics.
        """
        image_path = "{image_path}"
        rps = self.return_periods
        homes = risk_config.homes
        svi = homes.svi if homes.svi is not None else None

        # Charts block - keys have no special characters, Names are original
        charts = {}
        for rp in rps:
            chart_key = f"RP{int(rp)}Y"
            chart_name = f"{int(rp)}Y"
            charts[chart_key] = {
                "Name": chart_name,  # Original name
                "Image": f"{image_path}/house.png",
            }

        # Categories block - keys have no special characters, Names are original
        categories = {}
        if svi:
            for idx, svi_class in enumerate(svi.classes):
                cat_key = (
                    pascal_case(svi_class.replace(" ", "").replace("-", ""))
                    + "Vulnerability"
                )
                cat_name = f"{svi_class} Vulnerability"
                categories[cat_key] = {
                    "Name": cat_name,  # Original name with "Vulnerability"
                    "Color": svi.colors[idx] if svi.colors else "#cccccc",
                }
        else:
            # Create a single "All Homes" category when no SVI data
            categories["AllHomes"] = {
                "Name": "All Homes",
                "Color": "#88A2AA",  # Default color
            }

        # Slices block - reference Chart and Category Names (not keys)
        slices = {}
        if svi:
            for rp in rps:
                chart_name = f"{int(rp)}Y"
                for idx, svi_class in enumerate(svi.classes):
                    clean_svi = svi_class.replace(" ", "").replace("-", "")
                    cat_name = f"{svi_class} Vulnerability"
                    slice_key = f"{pascal_case(svi_class.replace(' ', '').replace('-', ''))}VulnerabilityRP{int(rp)}Y"
                    name = f"{int(rp)}Y {svi_class} Vulnerability"
                    query = f"ImpactedHomes{int(rp)}Y{clean_svi}SVI"
                    slices[slice_key] = {
                        "Name": name,
                        "Query": query,
                        "Chart": chart_name,  # Reference Chart Name, not key
                        "Category": cat_name,  # Reference Category Name, not key
                    }
        else:
            # Create slices for each return period without SVI breakdown
            for rp in rps:
                chart_name = f"{int(rp)}Y"
                slice_key = f"AllHomesRP{int(rp)}Y"
                name = f"{int(rp)}Y All Homes"
                query = f"ImpactedHomes{int(rp)}Y"
                slices[slice_key] = {
                    "Name": name,
                    "Query": query,
                    "Chart": chart_name,  # Reference Chart Name, not key
                    "Category": "All Homes",  # Reference Category Name, not key
                }

        # Other block: static info, but use config where possible
        other = {
            "Expected_Damages": {
                "title": "Expected annual damages",
                "query": "ExpectedAnnualDamages",
                "image": f"{image_path}/money.png",
                "image_scale": 1.3,
                "title_font_size": 25,
                "numbers_font_size": 20,
                "height": 300,
            },
            "Flooded": {
                "title": f"Number of homes with a high chance of being flooded in a {risk_config.flood_exceedance.period}-year period",
                "query": "LikelyFloodedHomes",
                "image": f"{image_path}/house.png",
                "image_scale": 0.7,
                "title_font_size": 25,
                "numbers_font_size": 20,
                "height": 300,
            },
            "Return_Periods": {
                "title": "Buildings impacted",
                "font_size": 25,
                "image_scale": 0.2,
                "numbers_font": 15,
                "subtitle_font": 22,
                "legend_font": 20,
                "plot_height": 300,
            },
            "Info": {
                "text": (
                    "Thresholds:<br>"
                    f"    Impacted: >= {risk_config.flood_exceedance.threshold} {risk_config.flood_exceedance.unit}<br>"
                ),
                "image": "https://openclipart.org/image/800px/302413",
                "scale": 0.1,
            },
        }

        cfg = {
            "Charts": charts,
            "Categories": categories,
            "Slices": slices,
            "Other": other,
        }
        self.infographics_config["risk"] = cfg
        return cfg
