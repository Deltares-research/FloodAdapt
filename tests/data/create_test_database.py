import shutil
from pathlib import Path

from create_test_events import DATA_DIR, create_eventset
from create_test_events import create_events as create_event_objects

from flood_adapt import unit_system as us
from flood_adapt.api.static import read_database
from flood_adapt.misc.config import Settings
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.impact.measure.buyout import Buyout
from flood_adapt.object_model.impact.measure.elevate import Elevate
from flood_adapt.object_model.impact.measure.floodproof import FloodProof
from flood_adapt.object_model.interface.benefits import (
    BenefitModel,
    CurrentSituationModel,
)
from flood_adapt.object_model.interface.measures import (
    BuyoutModel,
    ElevateModel,
    FloodProofModel,
    FloodWallModel,
    GreenInfrastructureModel,
    MeasureType,
    PumpModel,
    SelectionType,
)
from flood_adapt.object_model.interface.projections import (
    PhysicalProjectionModel,
    ProjectionModel,
    SocioEconomicChangeModel,
)
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.interface.strategies import StrategyModel
from flood_adapt.object_model.io.unit_system import VerticalReference
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.strategy import Strategy


def update_database_input(database_path: Path):
    """
    Create the input directory for the FloodAdapt testing database.

    This function is intended to be run at startup to ensure that the input directory is up-to-date.
    It assumes data files are located in this repository's `tests/data` directory.

    Parameters
    ----------
    database : IDatabase
        The database object to be updated

    """
    database = read_database(database_path.parent, database_path.name)
    input_dir = database.input_path
    if input_dir.exists():
        shutil.rmtree(input_dir)

    input_dir.mkdir(parents=True)
    for obj_dir in [
        "events",
        "projections",
        "measures",
        "strategies",
        "scenarios",
        "benefits",
    ]:
        (input_dir / obj_dir).mkdir()

    events = create_events()
    for event in events:
        database.events.save(event)

    projections = create_projections()
    for projection in projections:
        database.projections.save(projection)

    measures = create_measures()
    for measure in measures:
        database.measures.save(measure)

    strategies = create_strategies()
    for strategy in strategies:
        database.strategies.save(strategy)

    scenarios = create_scenarios()
    for scenario in scenarios:
        database.scenarios.save(scenario)

    benefits = create_benefits()
    for benefit in benefits:
        missing = benefit.check_scenarios()
        to_create = missing[missing["scenario created"].str.contains("No")]
        database.create_benefit_scenarios(benefit)

        database.benefits.save(benefit)

        for name, scenario in to_create.iterrows():
            scn_name = (
                f"{scenario['projection']}_{scenario['event']}_{scenario['strategy']}"
            )
            shutil.rmtree(input_dir / "scenarios" / scn_name)

    database.shutdown()


def create_events():
    events = create_event_objects()
    event_set = create_eventset("test_set")
    return [*events, event_set]


def create_projections():
    ALL_PROJECTIONS = Projection(
        data=ProjectionModel(
            name="all_projections",
            physical_projection=PhysicalProjectionModel(
                sea_level_rise=us.UnitfulLength(value=2, units=us.UnitTypesLength.feet),
                rainfall_multiplier=2,
                storm_frequency_increase=2,
            ),
            socio_economic_change=SocioEconomicChangeModel(
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
    )

    CURRENT = Projection(
        data=ProjectionModel(
            name="current",
            physical_projection=PhysicalProjectionModel(),
            socio_economic_change=SocioEconomicChangeModel(),
        )
    )

    POP_GROWTH_NEW_20 = Projection(
        data=ProjectionModel(
            name="pop_growth_new_20",
            physical_projection=PhysicalProjectionModel(
                rainfall_multiplier=1.0,
                storm_frequency_increase=0.0,
                sea_level_rise=us.UnitfulLength(
                    value=0.0, units=us.UnitTypesLength.feet
                ),
                subsidence=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.feet),
            ),
            socio_economic_change=SocioEconomicChangeModel(
                population_growth_new=20.0,
                economic_growth=0.0,
                population_growth_existing=0.0,
                new_development_elevation=us.UnitfulLengthRefValue(
                    value=1.0,
                    units=us.UnitTypesLength.feet,
                    type=VerticalReference.floodmap,
                ),
            ),
        )
    )

    SLR_2FT = Projection(
        data=ProjectionModel(
            name="SLR_2ft",
            physical_projection=PhysicalProjectionModel(
                sea_level_rise=us.UnitfulLength(value=2, units=us.UnitTypesLength.feet),
                subsidence=us.UnitfulLength(value=1, units=us.UnitTypesLength.feet),
            ),
            socio_economic_change=SocioEconomicChangeModel(),
        )
    )

    return [ALL_PROJECTIONS, CURRENT, POP_GROWTH_NEW_20, SLR_2FT]


def create_measures():
    # Hazard Measures
    BUYOUT = Buyout(
        BuyoutModel(
            name="buyout",
            type=MeasureType.buyout_properties,
            selection_type=SelectionType.aggregation_area,
            aggregation_area_name="name1",
            aggregation_area_type="aggr_lvl_2",
            property_type="RES",
        )
    )

    PUMP = Pump(
        PumpModel(
            name="pump",
            type=MeasureType.pump,
            discharge=us.UnitfulDischarge(value=500, units=us.UnitTypesDischarge.cfs),
            selection_type=SelectionType.polyline,
            polygon_file=str(DATA_DIR / "pump.geojson"),
        )
    )

    GREEN_INFRA = GreenInfrastructure(
        GreenInfrastructureModel(
            name="green_infra",
            type=MeasureType.greening,
            volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
            height=us.UnitfulHeight(value=2, units=us.UnitTypesLength.meters),
            percent_area=100,
            selection_type=SelectionType.polygon,
            polygon_file=str(DATA_DIR / "green_infra.geojson"),
        )
    )

    GREENING = GreenInfrastructure(
        GreenInfrastructureModel(
            name="greening",
            type=MeasureType.greening,
            selection_type=SelectionType.polygon,
            polygon_file=str(DATA_DIR / "greening.geojson"),
            percent_area=30.0,
            volume=us.UnitfulVolume(
                value=13181722.5726565, units=us.UnitTypesVolume.cf
            ),
            height=us.UnitfulHeight(value=3.0, units=us.UnitTypesLength.feet),
        )
    )

    SEAWALL = FloodWall(
        data=FloodWallModel(
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
    )

    TOTAL_STORAGE = GreenInfrastructure(
        GreenInfrastructureModel(
            name="total_storage",
            type=MeasureType.total_storage,
            selection_type=SelectionType.polygon,
            polygon_file=str(DATA_DIR / "total_storage.geojson"),
            volume=us.UnitfulVolume(value=100000000.0, units=us.UnitTypesVolume.cf),
        )
    )

    TOTAL_STORAGE_AGGREGATION_AREA = GreenInfrastructure(
        GreenInfrastructureModel(
            name="total_storage_aggregation_area",
            type=MeasureType.total_storage,
            selection_type=SelectionType.aggregation_area,
            aggregation_area_name="name5",
            aggregation_area_type="aggr_lvl_2",
            volume=us.UnitfulVolume(value=100000000.0, units=us.UnitTypesVolume.cf),
        )
    )

    WATER_SQUARE = GreenInfrastructure(
        GreenInfrastructureModel(
            name="water_square",
            type=MeasureType.water_square,
            selection_type=SelectionType.polygon,
            polygon_file=str(DATA_DIR / "water_square.geojson"),
            volume=us.UnitfulVolume(
                value=43975190.31512848, units=us.UnitTypesVolume.cf
            ),
            height=us.UnitfulHeight(value=3.0, units=us.UnitTypesLength.feet),
        )
    )

    # Impact Measures
    FLOOD_PROOF = FloodProof(
        FloodProofModel(
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
    )

    RAISE_PROPERTY_AGGREGATION_AREA = Elevate(
        ElevateModel(
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
    )

    RAISE_PROPERTY_AGGREGATION_DATUM = Elevate(
        ElevateModel(
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
    )

    RAISE_PROPERTY_AGGREGATION_ALL_PROPERTIES = Elevate(
        ElevateModel(
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
    )

    RAISE_PROPERTY_POLYGON = Elevate(
        ElevateModel(
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
        StrategyModel(
            name="elevate_comb_correct",
            measures=[
                "raise_property_aggregation_area",
                "raise_property_polygon",
            ],
        )
    )

    GREEN_INFRA = Strategy(
        StrategyModel(
            name="greeninfra",
            measures=[
                "greening",
                "total_storage",
                "water_square",
            ],
        )
    )

    NO_MEASURES = Strategy(
        StrategyModel(
            name="no_measures",
        )
    )

    PUMP = Strategy(
        StrategyModel(
            name="pump",
            measures=[
                "pump",
            ],
        )
    )

    RAISE_DATUM = Strategy(
        StrategyModel(
            name="raise_datum",
            measures=[
                "raise_property_aggregation_datum",
            ],
        )
    )

    STRATEGY_COMB = Strategy(
        StrategyModel(
            name="strategy_comb",
            measures=[
                "seawall",
                "raise_property_aggregation_area",
                "buyout",
                "floodproof",
            ],
        )
    )

    STRATEGY_IMPACT_COMB = Strategy(
        StrategyModel(
            name="strategy_impact_comb",
            measures=["raise_property_aggregation_area", "buyout", "floodproof"],
        )
    )

    TOTAL_STORAGE_AGGREGATION_AREA = Strategy(
        StrategyModel(
            name="total_storage_aggregation_area",
            measures=["total_storage_aggregation_area"],
        )
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
        data=ScenarioModel(
            name="all_projections_extreme12ft_strategy_comb",
            projection="all_projections",
            event="extreme12ft",
            strategy="strategy_comb",
        )
    )

    FLORENCE_ALL_PROJECTIONS_ELEVATE_COMB_CORRECT = Scenario(
        data=ScenarioModel(
            name="FLORENCE_all_projections_elevate_comb_correct",
            projection="all_projections",
            event="FLORENCE",
            strategy="strategy_comb",
        )
    )

    CURRENT_TEST_SET_NO_MEASURES = Scenario(
        data=ScenarioModel(
            name="current_test_set_no_measures",
            projection="current",
            event="test_set",
            strategy="no_measures",
        )
    )

    CURRENT_EXTREME12FT_STRATEGY_IMPACT_COMB = Scenario(
        data=ScenarioModel(
            name="current_extreme12ft_strategy_impact_comb",
            projection="current",
            event="extreme12ft",
            strategy="strategy_impact_comb",
        )
    )

    CURRENT_EXTREME12FT_RIVERSHAPE_WINDCONST_NO_MEASURES = Scenario(
        data=ScenarioModel(
            name="current_extreme12ft_rivershape_windconst_no_measures",
            projection="current",
            event="extreme12ft_rivershape_windconst",
            strategy="no_measures",
        )
    )

    CURRENT_EXTREME12FT_RAISE_DATUM = Scenario(
        data=ScenarioModel(
            name="current_extreme12ft_raise_datum",
            projection="current",
            event="extreme12ft",
            strategy="raise_datum",
        )
    )

    CURRENT_EXTREME12FT_NO_MEASURES = Scenario(
        data=ScenarioModel(
            name="current_extreme12ft_no_measures",
            projection="current",
            event="extreme12ft",
            strategy="no_measures",
        )
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
        data=BenefitModel(
            name="benefit_raise_properties_2050_no_costs",
            event_set="test_set",
            baseline_strategy="no_measures",
            strategy="elevate_comb_correct",
            projection="all_projections",
            future_year=2050,
            current_situation=CurrentSituationModel(projection="current", year=2023),
            discount_rate=0.07,
        )
    )

    BENEFIT_RAISE_PROPERTIES_2050 = Benefit(
        data=BenefitModel(
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
    )

    BENEFITS = [
        BENEFIT_RAISE_PROPERTIES_2050_NO_COSTS,
        BENEFIT_RAISE_PROPERTIES_2050,
    ]

    return BENEFITS


if __name__ == "__main__":
    settings = Settings(
        DATABASE_ROOT=Path("C:/Users/blom_lk/dev/Workspace_FloodAdapt/Database"),
        DATABASE_NAME="charleston_test",
    )

    update_database_input(settings.database_path)
