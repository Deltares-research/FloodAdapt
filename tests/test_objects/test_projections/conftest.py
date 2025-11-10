import pytest

from flood_adapt import unit_system as us
from flood_adapt.objects import (
    PhysicalProjection,
    Projection,
    SocioEconomicChange,
)
from flood_adapt.objects.data_container import GeoDataFrameContainer


@pytest.fixture()
def projection_full(test_data_dir):
    return Projection(
        name="all_projections",
        physical_projection=PhysicalProjection(
            sea_level_rise=us.UnitfulLength(value=2.0, units=us.UnitTypesLength.feet),
            subsidence=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters),
            rainfall_multiplier=2.0,
            storm_frequency_increase=2.0,
        ),
        socio_economic_change=SocioEconomicChange(
            population_growth_existing=20.0,
            economic_growth=20.0,
            population_growth_new=20.0,
            new_development_elevation=us.UnitfulLengthRefValue(
                value=1.0,
                units=us.UnitTypesLength.feet,
                type=us.VerticalReference.floodmap,
            ),
            gdf=GeoDataFrameContainer(path=test_data_dir / "new_areas.geojson"),
        ),
    )


@pytest.fixture()
def projection_slr_2ft():
    return Projection(
        name="SLR_2ft",
        physical_projection=PhysicalProjection(
            sea_level_rise=us.UnitfulLength(value=2.0, units=us.UnitTypesLength.feet),
            subsidence=us.UnitfulLength(value=1.0, units=us.UnitTypesLength.feet),
            rainfall_multiplier=1.0,
            storm_frequency_increase=0.0,
        ),
        socio_economic_change=SocioEconomicChange(
            population_growth_existing=0.0,
            economic_growth=0.0,
            population_growth_new=0.0,
        ),
    )
