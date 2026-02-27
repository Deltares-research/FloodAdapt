import shutil
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import List

from flood_adapt.config.hazard import RiverModel
from flood_adapt.config.settings import Settings
from flood_adapt.dbs_classes.database import Database
from flood_adapt.objects.benefits.benefits import (
    Benefit,
    CurrentSituationModel,
)
from flood_adapt.objects.events.event_set import (
    EventSet,
    SubEventModel,
)
from flood_adapt.objects.events.events import Event
from flood_adapt.objects.events.historical import (
    HistoricalEvent,
)
from flood_adapt.objects.events.hurricane import (
    HurricaneEvent,
)
from flood_adapt.objects.events.synthetic import (
    SyntheticEvent,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
)
from flood_adapt.objects.forcing.forcing import ForcingType
from flood_adapt.objects.forcing.rainfall import (
    RainfallConstant,
    RainfallTrack,
)
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.timeseries import (
    ShapeType,
    TimeseriesFactory,
)
from flood_adapt.objects.forcing.unit_system import VerticalReference
from flood_adapt.objects.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.objects.forcing.wind import (
    WindConstant,
    WindTrack,
)
from flood_adapt.objects.measures.measures import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    MeasureType,
    Pump,
    SelectionType,
)
from flood_adapt.objects.projections.projections import (
    PhysicalProjection,
    Projection,
    SocioEconomicChange,
)
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.objects.strategies.strategies import Strategy
from flood_adapt.workflows.benefit_runner import BenefitRunner

DATA_DIR = Path(__file__).parent


def update_database_input(database_path: Path):
    """
    Create the input directory for the FloodAdapt testing database.

    This function is intended to be run at startup to ensure that the input directory is up-to-date.
    It assumes data files are located in this repository's `tests/data` directory.

    Parameters
    ----------
    database_path : Path
        The path to the database directory. This is the directory that contains the `input`, `static` and `output` directories.

    """
    # Clear existing input and output directories
    shutil.rmtree(database_path / "input", ignore_errors=True)
    shutil.rmtree(database_path / "output", ignore_errors=True)
    for obj_dir in [
        "events",
        "projections",
        "measures",
        "strategies",
        "scenarios",
        "benefits",
    ]:
        (database_path / "input" / obj_dir).mkdir(parents=True, exist_ok=True)

    # Initialize database
    database = Database(database_path.parent, database_path.name)

    for event in create_events():
        database.events.add(event)

    for projection in create_projections():
        database.projections.add(projection)

    for measure in create_measures():
        database.measures.add(measure)

    for strategy in create_strategies():
        database.strategies.add(strategy)

    for scenario in create_scenarios():
        database.scenarios.add(scenario)

    for benefit in create_benefits():
        runner = BenefitRunner(database, benefit)
        runner.create_benefit_scenarios()
        database.benefits.add(benefit)

    # write to disk
    database.flush()

    # Cleanup singleton
    database.shutdown()


def create_events():
    return [
        *_create_single_events(),
        _create_event_set("test_set"),
    ]


def create_projections():
    ALL_PROJECTIONS = Projection(
        name="all_projections",
        physical_projection=PhysicalProjection(
            sea_level_rise=us.UnitfulLength(value=2, units=us.UnitTypesLength.feet),
            rainfall_multiplier=2,
            storm_frequency_increase=2,
        ),
        socio_economic_change=SocioEconomicChange(
            economic_growth=20,
            population_growth_new=20,
            population_growth_existing=20,
            new_development_elevation=us.UnitfulLengthRefValue(
                value=1,
                units=us.UnitTypesLength.feet,
                type=VerticalReference.floodmap,
            ),
            new_development_shapefile=str(DATA_DIR / "new_areas.geojson"),
        ),
    )

    CURRENT = Projection(
        name="current",
        physical_projection=PhysicalProjection(),
        socio_economic_change=SocioEconomicChange(),
    )

    POP_GROWTH_NEW_20 = Projection(
        name="pop_growth_new_20",
        physical_projection=PhysicalProjection(
            rainfall_multiplier=1.0,
            storm_frequency_increase=0.0,
            sea_level_rise=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.feet),
            subsidence=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.feet),
        ),
        socio_economic_change=SocioEconomicChange(
            population_growth_new=20.0,
            economic_growth=0.0,
            population_growth_existing=0.0,
            new_development_elevation=us.UnitfulLengthRefValue(
                value=1.0,
                units=us.UnitTypesLength.feet,
                type=VerticalReference.floodmap,
            ),
            new_development_shapefile=str(DATA_DIR / "new_areas.geojson"),
        ),
    )

    SLR_2FT = Projection(
        name="SLR_2ft",
        physical_projection=PhysicalProjection(
            sea_level_rise=us.UnitfulLength(value=2, units=us.UnitTypesLength.feet),
            subsidence=us.UnitfulLength(value=1, units=us.UnitTypesLength.feet),
        ),
        socio_economic_change=SocioEconomicChange(),
    )

    return [ALL_PROJECTIONS, CURRENT, POP_GROWTH_NEW_20, SLR_2FT]


def create_measures():
    # Hazard Measures
    BUYOUT = Buyout(
        name="buyout",
        type=MeasureType.buyout_properties,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_name="name1",
        aggregation_area_type="aggr_lvl_2",
        property_type="RES",
    )

    PUMP = Pump(
        name="pump",
        type=MeasureType.pump,
        discharge=us.UnitfulDischarge(value=500, units=us.UnitTypesDischarge.cfs),
        selection_type=SelectionType.polyline,
        polygon_file=str(DATA_DIR / "pump.geojson"),
    )

    GREEN_INFRA = GreenInfrastructure(
        name="green_infra",
        type=MeasureType.greening,
        volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
        height=us.UnitfulHeight(value=2, units=us.UnitTypesLength.meters),
        percent_area=100,
        selection_type=SelectionType.polygon,
        polygon_file=str(DATA_DIR / "green_infra.geojson"),
    )

    GREENING = GreenInfrastructure(
        name="greening",
        type=MeasureType.greening,
        selection_type=SelectionType.polygon,
        polygon_file=str(DATA_DIR / "greening.geojson"),
        percent_area=30.0,
        volume=us.UnitfulVolume(value=13181722.5726565, units=us.UnitTypesVolume.cf),
        height=us.UnitfulHeight(value=3.0, units=us.UnitTypesLength.feet),
    )

    SEAWALL = FloodWall(
        name="seawall",
        type=MeasureType.floodwall,
        selection_type=SelectionType.polygon,
        polygon_file=str(DATA_DIR / "seawall.geojson"),
        elevation=us.UnitfulLengthRefValue(
            value=12,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
    )

    TOTAL_STORAGE = GreenInfrastructure(
        name="total_storage",
        type=MeasureType.total_storage,
        selection_type=SelectionType.polygon,
        polygon_file=str(DATA_DIR / "total_storage.geojson"),
        volume=us.UnitfulVolume(value=100000000.0, units=us.UnitTypesVolume.cf),
    )

    TOTAL_STORAGE_AGGREGATION_AREA = GreenInfrastructure(
        name="total_storage_aggregation_area",
        type=MeasureType.total_storage,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_name="name5",
        aggregation_area_type="aggr_lvl_2",
        volume=us.UnitfulVolume(value=100000000.0, units=us.UnitTypesVolume.cf),
    )

    WATER_SQUARE = GreenInfrastructure(
        name="water_square",
        type=MeasureType.water_square,
        selection_type=SelectionType.polygon,
        polygon_file=str(DATA_DIR / "water_square.geojson"),
        volume=us.UnitfulVolume(value=43975190.31512848, units=us.UnitTypesVolume.cf),
        height=us.UnitfulHeight(value=3.0, units=us.UnitTypesLength.feet),
    )

    # Impact Measures
    FLOOD_PROOF = FloodProof(
        name="floodproof",
        type=MeasureType.floodproof_properties,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_name="name3",
        aggregation_area_type="aggr_lvl_2",
        elevation=us.UnitfulLengthRefValue(
            value=3,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
        property_type="RES",
    )

    RAISE_PROPERTY_AGGREGATION_AREA = Elevate(
        name="raise_property_aggregation_area",
        type=MeasureType.elevate_properties,
        elevation=us.UnitfulLengthRefValue(
            value=1,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
        selection_type=SelectionType.aggregation_area,
        aggregation_area_name="name5",
        aggregation_area_type="aggr_lvl_2",
        property_type="RES",
    )

    RAISE_PROPERTY_AGGREGATION_DATUM = Elevate(
        name="raise_property_aggregation_datum",
        type=MeasureType.elevate_properties,
        elevation=us.UnitfulLengthRefValue(
            value=1,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.datum,
        ),
        selection_type=SelectionType.aggregation_area,
        aggregation_area_name="name5",
        aggregation_area_type="aggr_lvl_2",
        property_type="RES",
    )

    RAISE_PROPERTY_AGGREGATION_ALL_PROPERTIES = Elevate(
        name="raise_property_aggregation_all_properties",
        type=MeasureType.elevate_properties,
        elevation=us.UnitfulLengthRefValue(
            value=1,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
        selection_type=SelectionType.all,
        property_type="RES",
    )

    RAISE_PROPERTY_POLYGON = Elevate(
        name="raise_property_polygon",
        type=MeasureType.elevate_properties,
        elevation=us.UnitfulLengthRefValue(
            value=1,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
        selection_type=SelectionType.polygon,
        property_type="RES",
        polygon_file=str(DATA_DIR / "raise_property_polygon.geojson"),
    )

    MEASURES = [
        BUYOUT,
        PUMP,
        FLOOD_PROOF,
        GREEN_INFRA,
        GREENING,
        SEAWALL,
        RAISE_PROPERTY_AGGREGATION_AREA,
        RAISE_PROPERTY_AGGREGATION_DATUM,
        RAISE_PROPERTY_AGGREGATION_ALL_PROPERTIES,
        RAISE_PROPERTY_POLYGON,
        TOTAL_STORAGE,
        TOTAL_STORAGE_AGGREGATION_AREA,
        WATER_SQUARE,
    ]

    return MEASURES


def create_strategies():
    ELEVATE_COMB_CORRECT = Strategy(
        name="elevate_comb_correct",
        measures=[
            "raise_property_aggregation_area",
            "raise_property_polygon",
        ],
    )

    GREEN_INFRA = Strategy(
        name="greeninfra",
        measures=[
            "greening",
            "total_storage",
            "water_square",
        ],
    )

    NO_MEASURES = Strategy(
        name="no_measures",
        measures=[],
    )

    PUMP = Strategy(
        name="pump",
        measures=[
            "pump",
        ],
    )

    RAISE_DATUM = Strategy(
        name="raise_datum",
        measures=[
            "raise_property_aggregation_datum",
        ],
    )

    STRATEGY_COMB = Strategy(
        name="strategy_comb",
        measures=[
            "seawall",
            "raise_property_aggregation_area",
            "buyout",
            "floodproof",
        ],
    )

    STRATEGY_IMPACT_COMB = Strategy(
        name="strategy_impact_comb",
        measures=["raise_property_aggregation_area", "buyout", "floodproof"],
    )

    TOTAL_STORAGE_AGGREGATION_AREA = Strategy(
        name="total_storage_aggregation_area",
        measures=["total_storage_aggregation_area"],
    )

    STRATEGIES = [
        ELEVATE_COMB_CORRECT,
        GREEN_INFRA,
        NO_MEASURES,
        PUMP,
        RAISE_DATUM,
        STRATEGY_COMB,
        STRATEGY_IMPACT_COMB,
        TOTAL_STORAGE_AGGREGATION_AREA,
    ]
    return STRATEGIES


def create_scenarios():
    ALL_PROJECTIONS_EXTREME12FT_STRATEGY_COMB = Scenario(
        name="all_projections_extreme12ft_strategy_comb",
        projection="all_projections",
        event="extreme12ft",
        strategy="strategy_comb",
    )

    FLORENCE_ALL_PROJECTIONS_ELEVATE_COMB_CORRECT = Scenario(
        name="FLORENCE_all_projections_elevate_comb_correct",
        projection="all_projections",
        event="FLORENCE",
        strategy="strategy_comb",
    )

    CURRENT_TEST_SET_NO_MEASURES = Scenario(
        name="current_test_set_no_measures",
        projection="current",
        event="test_set",
        strategy="no_measures",
    )

    CURRENT_EXTREME12FT_STRATEGY_IMPACT_COMB = Scenario(
        name="current_extreme12ft_strategy_impact_comb",
        projection="current",
        event="extreme12ft",
        strategy="strategy_impact_comb",
    )

    CURRENT_EXTREME12FT_RIVERSHAPE_WINDCONST_NO_MEASURES = Scenario(
        name="current_extreme12ft_rivershape_windconst_no_measures",
        projection="current",
        event="extreme12ft_rivershape_windconst",
        strategy="no_measures",
    )

    CURRENT_EXTREME12FT_RAISE_DATUM = Scenario(
        name="current_extreme12ft_raise_datum",
        projection="current",
        event="extreme12ft",
        strategy="raise_datum",
    )

    CURRENT_EXTREME12FT_NO_MEASURES = Scenario(
        name="current_extreme12ft_no_measures",
        projection="current",
        event="extreme12ft",
        strategy="no_measures",
    )

    SCENARIOS = [
        ALL_PROJECTIONS_EXTREME12FT_STRATEGY_COMB,
        FLORENCE_ALL_PROJECTIONS_ELEVATE_COMB_CORRECT,
        CURRENT_TEST_SET_NO_MEASURES,
        CURRENT_EXTREME12FT_STRATEGY_IMPACT_COMB,
        CURRENT_EXTREME12FT_RIVERSHAPE_WINDCONST_NO_MEASURES,
        CURRENT_EXTREME12FT_RAISE_DATUM,
        CURRENT_EXTREME12FT_NO_MEASURES,
    ]

    return SCENARIOS


def create_benefits():
    BENEFIT_RAISE_PROPERTIES_2050_NO_COSTS = Benefit(
        name="benefit_raise_properties_2050_no_costs",
        event_set="test_set",
        baseline_strategy="no_measures",
        strategy="elevate_comb_correct",
        projection="all_projections",
        future_year=2050,
        current_situation=CurrentSituationModel(projection="current", year=2023),
        discount_rate=0.07,
    )

    BENEFIT_RAISE_PROPERTIES_2050 = Benefit(
        name="benefit_raise_properties_2050",
        event_set="test_set",
        strategy="elevate_comb_correct",
        projection="all_projections",
        future_year=2050,
        current_situation=CurrentSituationModel(projection="current", year=2023),
        baseline_strategy="no_measures",
        discount_rate=0.07,
        implementation_cost=200000000,
        annual_maint_cost=100000,
    )

    BENEFITS = [
        BENEFIT_RAISE_PROPERTIES_2050_NO_COSTS,
        BENEFIT_RAISE_PROPERTIES_2050,
    ]

    return BENEFITS


def _create_single_events():
    EXTREME_12FT = SyntheticEvent(
        name="extreme12ft",
        time=TimeFrame(start_time=datetime(2020, 1, 1), end_time=datetime(2020, 1, 2)),
        description="extreme 12 foot event",
        forcings={
            ForcingType.DISCHARGE: [
                DischargeConstant(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=5000, units=us.UnitTypesDischarge.cfs
                    ),
                ),
            ],
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=3, units=us.UnitTypesLength.feet
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                    surge=SurgeModel(
                        timeseries=TimeseriesFactory.from_args(
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=9.22, units=us.UnitTypesLength.feet
                            ),
                        )
                    ),
                ),
            ],
        },
    )

    EXTREME_12FT_RIVERSHAPE_WINDCONST = SyntheticEvent(
        name="extreme12ft_rivershape_windconst",
        time=TimeFrame(start_time=datetime(2020, 1, 1), end_time=datetime(2020, 1, 2)),
        description="extreme 12 foot event",
        forcings={
            ForcingType.WIND: [
                WindConstant(
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                    speed=us.UnitfulVelocity(value=10, units=us.UnitTypesVelocity.mps),
                )
            ],
            ForcingType.DISCHARGE: [
                DischargeSynthetic(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    timeseries=TimeseriesFactory.from_args(
                        shape_type=ShapeType.block,
                        duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
                        peak_time=us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                        peak_value=us.UnitfulDischarge(
                            value=10000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                )
            ],
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=3, units=us.UnitTypesLength.feet
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                    surge=SurgeModel(
                        timeseries=TimeseriesFactory.from_args(
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=9.22, units=us.UnitTypesLength.feet
                            ),
                        ),
                    ),
                )
            ],
        },
    )

    FLORENCE = HurricaneEvent(
        name="FLORENCE",
        time=TimeFrame(start_time=datetime(2019, 8, 30), end_time=datetime(2019, 9, 1)),
        description="extreme 12 foot event",
        track_name="FLORENCE",
        forcings={
            ForcingType.DISCHARGE: [
                DischargeSynthetic(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    timeseries=TimeseriesFactory.from_args(
                        shape_type=ShapeType.block,
                        duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
                        peak_time=us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                        peak_value=us.UnitfulDischarge(
                            value=10000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                )
            ],
            ForcingType.WATERLEVEL: [WaterlevelModel()],
            ForcingType.WIND: [WindTrack(path=DATA_DIR / "cyclones" / "FLORENCE.cyc")],
            ForcingType.RAINFALL: [
                RainfallTrack(path=DATA_DIR / "cyclones" / "FLORENCE.cyc")
            ],
        },
    )

    KINGTIDE_NOV2021 = HistoricalEvent(
        name="kingTideNov2021",
        time=TimeFrame(
            start_time=datetime(2021, 11, 4),
            end_time=datetime(
                year=2021,
                month=11,
                day=4,
                hour=3,
            ),
        ),
        description="kingtide_nov2021",
        forcings={
            ForcingType.DISCHARGE: [
                DischargeSynthetic(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    timeseries=TimeseriesFactory.from_args(
                        shape_type=ShapeType.block,
                        duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
                        peak_time=us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                        peak_value=us.UnitfulDischarge(
                            value=10000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                ),
            ],
            # ForcingType.RAINFALL: [RainfallMeteo()],      # Temporarily excluded due to bug in hydromt-sfincs. fixed in v1.3.0
            # ForcingType.WIND: [WindMeteo()],              # Temporarily excluded due to bug in hydromt-sfincs. fixed in v1.3.0
            # ForcingType.WATERLEVEL: [WaterlevelModel()],  # Temporarily excluded due to bug in hydromt-sfincs. fixed in v1.3.0
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    surge=SurgeModel(
                        timeseries=TimeseriesFactory.from_args(
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=1, units=us.UnitTypesLength.meters
                            ),
                        )
                    ),
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.meters
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                )
            ],
        },
    )
    return EXTREME_12FT, EXTREME_12FT_RIVERSHAPE_WINDCONST, FLORENCE, KINGTIDE_NOV2021


def _create_event_set(name: str) -> EventSet:
    sub_event_models: List[SubEventModel] = []
    sub_events: List[Event] = []

    sub_events.append(_create_synthetic_event(name=f"subevent_{1:04d}"))
    sub_event_models.append(SubEventModel(name=f"subevent_{1:04d}", frequency=1))

    sub_events.append(_create_hurricane_event(name=f"subevent_hurricane{78:04d}"))
    sub_event_models.append(
        SubEventModel(name=f"subevent_hurricane{78:04d}", frequency=78)
    )

    event_set = EventSet(
        name=name,
        sub_events=sub_event_models,
    )
    event_set.load_sub_events(sub_events=sub_events)
    return event_set


def create_event_set_with_hurricanes():
    sub_event_models: List[SubEventModel] = []
    sub_events: List[Event] = []

    for i in range(1, 5):
        sub_events.append(_create_hurricane_event(name=f"subevent_hurricane{i:04d}"))
        sub_event_models.append(
            SubEventModel(name=f"subevent_hurricane{i:04d}", frequency=i)
        )

    event_set = EventSet(
        name="test_event_set_with_hurricanes",
        sub_events=sub_event_models,
    )
    event_set.load_sub_events(sub_events=sub_events)
    return event_set


def _create_synthetic_event(name: str) -> SyntheticEvent:
    return SyntheticEvent(
        name=name,
        time=TimeFrame(),
        forcings={
            ForcingType.WIND: [
                WindConstant(
                    speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                )
            ],
            ForcingType.RAINFALL: [
                RainfallConstant(
                    intensity=us.UnitfulIntensity(
                        value=2, units=us.UnitTypesIntensity.mm_hr
                    )
                )
            ],
            ForcingType.DISCHARGE: [
                DischargeConstant(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=5000, units=us.UnitTypesDischarge.cfs
                    ),
                )
            ],
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    surge=SurgeModel(
                        timeseries=TimeseriesFactory.from_args(
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=1, units=us.UnitTypesLength.meters
                            ),
                        )
                    ),
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.meters
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                )
            ],
        },
    )


def _create_hurricane_event(name: str) -> HurricaneEvent:
    cyc_file = DATA_DIR / "cyclones" / "IAN.cyc"
    return HurricaneEvent(
        name=name,
        time=TimeFrame(),
        track_name="IAN",
        forcings={
            ForcingType.WATERLEVEL: [WaterlevelModel()],
            ForcingType.WIND: [WindTrack(path=cyc_file)],
            ForcingType.RAINFALL: [RainfallTrack(path=cyc_file)],
            ForcingType.DISCHARGE: [
                DischargeConstant(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=5000, units=us.UnitTypesDischarge.cfs
                    ),
                ),
            ],
        },
    )


if __name__ == "__main__":
    parser = ArgumentParser(description="Create the static data for the database.")
    parser.add_argument(
        "-d",
        "--database_root",
        type=Path,
        default=Path(__file__).parents[3] / "Database",
        help="Path to the database root folder.",
    )
    parser.add_argument(
        "-n",
        "--database_name",
        type=str,
        default="charleston_test",
        help="Name of the database.",
    )
    args = parser.parse_args()

    settings = Settings(
        DATABASE_ROOT=args.database_root,
        DATABASE_NAME=args.database_name,
    )
    print(f"Updating database: {settings.database_path}")
    update_database_input(settings.database_path)
