from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import tomli_w
from pydantic import BaseModel, Field, field_validator

# TODO update use of impact columns to adapter definition of columns
# TODO specify uniform impact thresholds for buildings and roads


def pascal_case(s):
    return "".join(word.capitalize() for word in s.split())


class MetricModel(BaseModel):
    """
    InfometricModel represents a metric configuration for infometric analysis.

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
        """Set default values for long_name and description fields."""
        # info.data contains all field values
        if value is None:
            # Use 'name' field as default
            return info.data.get("name")
        return value


class ImpactCategoriesModel(BaseModel):
    categories: list[str] = Field(default_factory=lambda: ["Minor", "Major", "Severe"])
    colors: Optional[list[str]] = Field(
        default_factory=lambda: ["#ffa500", "#ff0000", "#000000"]
    )
    field: str = "Inundation Depth"
    unit: str
    bins: list[float]

    @field_validator("colors", mode="before")
    @classmethod
    def validate_colors_length(cls, colors, info):
        categories = info.data.get("categories")
        if categories and colors and len(colors) != len(categories):
            raise ValueError("Length of 'colors' must match length of 'categories'.")
        return colors

    @field_validator("bins", mode="before")
    @classmethod
    def validate_bins_length(cls, bins, info):
        categories = info.data.get("categories")
        if categories and len(bins) != len(categories) - 1:
            raise ValueError(
                "Length of 'bins' must be one less than length of 'categories'."
            )
        return bins


class BuildingsInfographicModel(BaseModel):
    # Define building types
    types: list[str]
    icons: list[str]
    type_mapping: dict[str, dict[str, list[str]]]
    # Define impact categories
    impact_categories: ImpactCategoriesModel

    @field_validator("icons", mode="before")
    @classmethod
    def validate_icons_length(cls, icons, info):
        types = info.data.get("types")
        if types and len(icons) != len(types):
            raise ValueError("Length of 'icons' must equal to the length of 'types'.")
        return icons

    @staticmethod
    def get_template(type: Literal["OSM", "NSI"]):
        if type == "OSM":
            config = BuildingsInfographicModel(
                types=["Residential", "Commercial", "Industrial"],
                icons=["house", "cart", "factory"],
                type_mapping={
                    "Residential": {"Primary Object Type": ["residential"]},
                    "Commercial": {"Primary Object Type": ["commercial"]},
                    "Industrial": {"Primary Object Type": ["industrial"]},
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
                    "Residential": {"Primary Object Type": ["RES"]},
                    "Commercial": {
                        "Secondary Object Type": [
                            "COM1",
                            "COM2",
                            "COM3",
                            "COM4",
                            "COM5",
                            "COM8",
                            "COM9",
                        ]
                    },
                    "Health facilities": {
                        "Secondary Object Type": ["RES6", "COM6", "COM7"]
                    },
                    "Schools": {"Secondary Object Type": ["EDU1", "EDU2"]},
                    "Emergency facilities": {"Secondary Object Type": ["GOV2"]},
                },
                impact_categories=ImpactCategoriesModel(unit="feet", bins=[1, 6]),
            )
        return config


class SviModel(BaseModel):
    classes: list[str] = Field(default_factory=lambda: ["Low", "High"])
    colors: list[str] = Field(default_factory=lambda: ["#D5DEE1", "#88A2AA"])
    thresholds: list[float] = Field(default_factory=lambda: [0.7])


class SviInfographicModel(BaseModel):
    svi_threshold: float
    colors: list[str] = Field(default_factory=lambda: ["#D5DEE1", "#88A2AA"])
    mapping: dict[str, list[str]]
    impact_categories: ImpactCategoriesModel

    @staticmethod
    def get_template(svi_threshold: float, type: Literal["OSM", "NSI"]):
        if type == "OSM":
            config = SviInfographicModel(
                svi_threshold=svi_threshold,
                mapping={"Primary Object Type": ["residential"]},
                impact_categories=ImpactCategoriesModel(
                    categories=["Flooded", "Displaced"],
                    colors=None,
                    unit="meters",
                    bins=[1.5],
                ),
            )
        elif type == "NSI":
            config = SviInfographicModel(
                svi_threshold=svi_threshold,
                mapping={"Primary Object Type": ["RES"]},
                impact_categories=ImpactCategoriesModel(
                    categories=["Flooded", "Displaced"],
                    colors=None,
                    unit="feet",
                    bins=[6],
                ),
            )
        return config


class RoadsInfographicModel(BaseModel):
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
    field: str = "Inundation Depth"
    unit: str
    road_length_field: str = "Segment Length"

    @field_validator("categories", mode="after")
    @classmethod
    def validate_lengths(cls, v, info):
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
    buildings: Optional[BuildingsInfographicModel] = None
    svi: Optional[SviInfographicModel] = None
    roads: Optional[RoadsInfographicModel] = None


class FloodExceedanceModel(BaseModel):
    column: str = "Inundation Depth"
    threshold: float = 0.1
    unit: str = "meters"
    period: int = 30


class RiskInfographicModel(BaseModel):
    svi: SviInfographicModel
    flood_exceedances: FloodExceedanceModel

    @staticmethod
    def get_template(
        type: Literal["OSM", "NSI"], svi_threshold: Optional[float] = None
    ):
        if type == "OSM":
            config = RiskInfographicModel(
                svi=SviInfographicModel.get_template(svi_threshold, type="OSM")
                if svi_threshold
                else None,
                flood_exceedances=FloodExceedanceModel(),
            )
        elif type == "NSI":
            config = RiskInfographicModel(
                svi=SviInfographicModel.get_template(svi_threshold, type="NSI")
                if svi_threshold
                else None,
                flood_exceedances=FloodExceedanceModel(unit="feet", threshold=0.2),
            )
        return config


def get_filter(
    type_mapping: dict[str, list[str]],
    cat_field: str,
    cat_idx: int,
    bins: list[float],
    base_filt="",
) -> str:
    """
    Construct a SQL filter string based on provided type mapping and category criteria.

    Args:
        type_mapping (dict): Mapping of type_field to list of types to filter on.
        cat_field (str): Name of the field representing the category in the database.
        cat_idx (int): Index indicating which category bin to use for filtering.
        bins (list): List of bin thresholds for the category field.
        base_filt (str, optional): Additional base filter string to prepend. Defaults to "".

    Returns
    -------
        str: A SQL filter string combining type and category conditions.
    """
    base = base_filt + " AND " if base_filt else ""
    # Build type filters for each type_field in type_mapping
    type_filters = []
    for type_field, type_list in type_mapping.items():
        type_filters.append(
            f"`{type_field}` IN (" + ", ".join([f"'{t}'" for t in type_list]) + ")"
        )
    base += " AND ".join(type_filters)
    if cat_idx == 0:
        return f"{base} AND `{cat_field}` <= {bins[0]}"
    elif cat_idx == len(bins):
        return f"{base} AND `{cat_field}` > {bins[-1]}"
    else:
        return f"{base} AND `{cat_field}` <= {bins[cat_idx]} AND `{cat_field}` > {bins[cat_idx-1]}"


class Metrics:
    dmg_unit: str
    return_periods: list[float]

    def __init__(self, dmg_unit: str, return_periods: list[float]):
        self.dmg_unit = dmg_unit
        self.return_periods = return_periods
        self.create_mandatory_metrics_event()
        self.create_mandatory_metrics_risk()
        self.additional_metrics_event: list[MetricModel] = []
        self.additional_metrics_risk: list[MetricModel] = []
        self.infographics_metrics_event: list[MetricModel] = []
        self.infographics_metrics_risk: list[MetricModel] = []
        self.additional_risk_configs = {}
        self.infographics_config = {}

    @staticmethod
    def write_metrics(metrics, path, aggr_levels=[]):
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
        Write all metrics (mandatory, additional, and infographics) to TOML files in the specified directory.

        Parameters
        ----------
        metrics_path : Union[str, Path, PathLike]
            The directory path where the metrics configuration files will be saved.
        aggregation_levels : List[str]
            A list of aggregation levels to include in the metrics configuration files.
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
                self.infographics_metrics_event,
                path_im / "infographic_metrics_config_risk.toml",
                aggregation_levels,
            )

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
        self.mandatory_metrics_event = []
        self.mandatory_metrics_event.append(
            MetricModel(
                name="TotalDamageEvent",
                description="Total building damage",
                long_name=f"Total building damage ({self.dmg_unit})",
                select="SUM(`Total Damage`)",
                filter="",
                show_in_metrics_table=True,
            )
        )
        return self.mandatory_metrics_event

    def create_mandatory_metrics_risk(self) -> list[MetricModel]:
        self.mandatory_metrics_risk = []
        self.mandatory_metrics_risk.append(
            MetricModel(
                name="ExpectedAnnualDamages",
                description="Expected annual damages",
                long_name=f"Expected annual damages ({self.dmg_unit})",
                select="SUM(`Risk (EAD)`)",
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
                    select=f"SUM(`Total Damage ({int(rp)}Y)`)",
                    filter="",
                    show_in_metrics_table=True,
                )
            )

        return self.mandatory_metrics_risk

    def add_event_metric(self, metric: MetricModel) -> None:
        if any(m.name == metric.name for m in self.additional_metrics_event):
            raise ValueError(f"Event metric with name '{metric.name}' already exists.")
        self.additional_metrics_event.append(metric)

    def add_risk_metric(self, metric: MetricModel) -> None:
        if any(m.name == metric.name for m in self.additional_metrics_risk):
            raise ValueError(f"Risk metric with name '{metric.name}' already exists.")
        self.additional_metrics_risk.append(metric)

    def create_infographics_metrics_event(
        self, config: EventInfographicModel, base_filt="`Total Damage` > 0"
    ) -> list[MetricModel]:
        # Generate queries for all building types and categories
        if config.buildings:
            self._setup_buildings(config.buildings, base_filt)
        if config.svi:
            self._setup_svi(config.svi, base_filt)
        if config.roads:
            self._setup_roads(config.roads)
        return self.infographics_metrics_event

    def create_infographics_metrics_risk(
        self, config: RiskInfographicModel, base_filt="`Total Damage` > 0"
    ) -> list[MetricModel]:
        infographics_metrics_risk = []

        # Get mapping from config.svi if available, else default to {"Primary Object Type": ["RES"]}
        if config.svi and hasattr(config.svi, "mapping"):
            mapping = config.svi.mapping
        else:
            mapping = {"Primary Object Type": ["RES"]}

        # Build type filter string
        type_filters = []
        for type_field, type_list in mapping.items():
            type_filters.append(
                f"`{type_field}` IN (" + ", ".join([f"'{t}'" for t in type_list]) + ")"
            )
        type_cond = " AND ".join(type_filters)

        # FloodedHomes (Exceedance Probability > 50)
        fe = config.flood_exceedances
        infographics_metrics_risk.append(
            MetricModel(
                name="LikelyFloodedHomes",
                description=f"Homes likely to flood ({fe.column} > {fe.threshold} {fe.unit}) in {fe.period} year period",
                select="COUNT(*)",
                filter=f"`Exceedance Probability` > 50 AND {type_cond}",
                long_name=f"Homes likely to flood in {fe.period}-year period (#)",
                show_in_metrics_table=True,
            )
        )

        # ImpactedHomes for each RP (2, 5, 10, 25, 50, 100)
        rps = [2, 5, 10, 25, 50, 100]
        svi_threshold = 0.7
        for rp in rps:
            # ImpactedHomes{RP} (all homes)
            infographics_metrics_risk.append(
                MetricModel(
                    name=f"ImpactedHomes{rp}Y",
                    description=f"Homes impacted (Inundation Depth > 0.25) in the {rp}-year event",
                    select="COUNT(*)",
                    filter=f"`Inundation Depth ({rp}Y)` >= 0.25 AND {type_cond}",
                    long_name=f"Flooded homes RP{rp}",
                    show_in_metrics_table=True,
                )
            )
            # ImpactedHomes{RP}HighSVI
            infographics_metrics_risk.append(
                MetricModel(
                    name=f"ImpactedHomes{rp}YHighSVI",
                    description=f"Highly vulnerable homes impacted (Inundation Depth > 0.25) in the {rp}-year event",
                    select="COUNT(*)",
                    filter=f"`Inundation Depth ({rp}Y)` >= 0.25 AND {type_cond} AND `SVI` >= {svi_threshold}",
                    long_name=f"Highly vulnerable flooded homes RP{rp}",
                    show_in_metrics_table=True,
                )
            )
            # ImpactedHomes{RP}LowSVI
            infographics_metrics_risk.append(
                MetricModel(
                    name=f"ImpactedHomes{rp}YLowSVI",
                    description=f"Less-vulnerable homes impacted (Inundation Depth > 0.25) in the {rp}-year event",
                    select="COUNT(*)",
                    filter=f"`Inundation Depth ({rp}Y)` >= 0.25 AND {type_cond} AND `SVI` < {svi_threshold}",
                    long_name=f"Less vulnerable flooded homes RP{rp}",
                    show_in_metrics_table=True,
                )
            )
        self.infographics_metrics_risk = infographics_metrics_risk
        return self.infographics_metrics_risk

    def _setup_buildings(self, config: BuildingsInfographicModel, base_filt) -> None:
        # Generate queries for all building types and categories
        building_queries = []
        for btype in config.types:
            type_mapping = config.type_mapping.get(btype, {})
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

    def _setup_svi(self, config: SviInfographicModel, base_filt) -> None:
        # Generate queries for all SVI categories and vulnerability levels
        svi_queries = []
        cat_field = config.impact_categories.field
        bins = config.impact_categories.bins
        svi_threshold = config.svi_threshold
        mapping = config.mapping

        for i, cat in enumerate(config.impact_categories.categories):
            for vuln in ["LowVulnerability", "HighVulnerability"]:
                if vuln == "LowVulnerability":
                    svi_cond = f"`SVI` < {svi_threshold}"
                    vuln_label = "Low Vulnerability"
                else:
                    svi_cond = f"`SVI` >= {svi_threshold}"
                    vuln_label = "High Vulnerability"

                if i == 0:
                    cat_cond = f"`{cat_field}` <= {bins[0]}"
                else:
                    cat_cond = f"`{cat_field}` > {bins[0]}"

                # Build type filter
                type_filters = []
                for type_field, type_list in mapping.items():
                    type_filters.append(
                        f"`{type_field}` IN ("
                        + ", ".join([f"'{t}'" for t in type_list])
                        + ")"
                    )
                type_cond = " AND ".join(type_filters)

                filter_str = (
                    f"{type_cond} AND {cat_cond} AND {svi_cond} AND {base_filt}"
                )

                name = f"{cat}{vuln}"
                desc = f"Number of {cat.lower()} homes with {vuln_label.lower()}"
                long_name = f"{cat} Homes - {vuln_label} (#)"

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
            if i == 0:
                filter_str = f"`{cat_field}` > {thresholds[0]}"
            else:
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
        # Categories block
        for k, cat in enumerate(buildings_config.impact_categories.categories):
            cfg["Categories"][cat] = {
                "Name": cat,
                "Color": buildings_config.impact_categories.colors[k],
            }

        for i, btype in enumerate(buildings_config.types):
            # Charts block
            cfg["Charts"][btype] = {
                "Name": btype,
                "Image": f"{image_path}/{buildings_config.icons[i]}.png",
            }

            # Slices blocks
            for cat in buildings_config.impact_categories.categories:
                slice_key = f"{cat}_{btype}"
                cfg["Slices"][slice_key] = {
                    "Name": f"{cat} {btype}",
                    "Query": f"{btype}{cat}Count",
                    "Chart": btype,
                    "Category": cat,
                }

        return cfg

    @staticmethod
    def _make_infographics_config_svi(
        svi_config: SviInfographicModel,
    ) -> Dict[str, Any]:
        image_path = "{image_path}"
        categories = ["LowVulnerability", "HighVulnerability"]
        charts = {}
        slices = {}
        categories_cfg = {}
        # Chart names correspond to impact categories
        for cat in svi_config.impact_categories.categories:
            charts[cat] = {"Name": cat, "Image": f"{image_path}/house.png"}
        # Categories block for vulnerability
        for idx, vuln in enumerate(categories):
            categories_cfg[vuln] = {"Name": vuln, "Color": svi_config.colors[idx]}
        # Slices block
        for cat in svi_config.impact_categories.categories:
            for vuln in categories:
                slice_key = f"{cat}_{vuln}_People"
                name = f"{cat} {vuln.replace('Vulnerability', ' vulnerability').lower()} homes"
                query = f"{cat}{vuln}"
                chart = cat
                category = vuln
                slices[slice_key] = {
                    "Name": name,
                    "Query": query,
                    "Chart": chart,
                    "Category": category,
                }
        # Info text
        bins = svi_config.impact_categories.bins
        unit = svi_config.impact_categories.unit
        info_lines = [
            "Thresholds:<br>",
            f"    {svi_config.impact_categories.categories[0]}: <= {bins[0]} {unit}<br>",
            f"    {svi_config.impact_categories.categories[1]}: > {bins[0]} {unit}<br>",
            "'Since some homes do not have an SVI,<br>",
            "total number of homes might be different <br>",
            "between this and the above graph.'",
        ]
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
        image_path = "{image_path}"
        # Chart block
        charts = {"Flooded Roads": {"Name": "Flooded Roads"}}
        # Categories block
        categories_cfg = {}
        for idx, cat in enumerate(roads_config.categories):
            cat_name = f"{cat} Flooding"
            categories_cfg[cat_name] = {
                "Name": cat_name,
                "Color": roads_config.colors[idx],
                "Image": f"{image_path}/{roads_config.icons[idx]}.png",
            }
        # Slices block
        slices = {}
        for idx, cat in enumerate(roads_config.categories):
            cat_name = f"{cat} Flooding"
            query_name = f"{pascal_case(cat)}FloodedRoadsLength"
            slices[cat_name] = {
                "Name": cat_name,
                "Query": query_name,
                "Chart": "Flooded Roads",
                "Category": cat_name,
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
