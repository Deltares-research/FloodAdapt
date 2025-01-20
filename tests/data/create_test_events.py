from datetime import datetime
from pathlib import Path

from flood_adapt import unit_system as us
from flood_adapt.object_model.hazard.event.historical import (
    HistoricalEvent,
    HistoricalEventModel,
)
from flood_adapt.object_model.hazard.event.hurricane import (
    HurricaneEvent,
    HurricaneEventModel,
)
from flood_adapt.object_model.hazard.event.synthetic import (
    SyntheticEvent,
    SyntheticEventModel,
)
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.forcing.rainfall import RainfallMeteo
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.forcing.wind import WindConstant, WindMeteo
from flood_adapt.object_model.hazard.interface.forcing import ForcingType, ShapeType
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.config.sfincs import RiverModel


def create_events():
    EXTREME_12FT = SyntheticEvent(
        SyntheticEventModel(
            name="extreme12ft",
            time=TimeModel(
                start_time=datetime(2020, 1, 1), end_time=datetime(2020, 1, 2)
            ),
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
                            timeseries=SyntheticTimeseriesModel[us.UnitfulLength](
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
                    ),
                ],
            },
        )
    )

    EXTREME_12FT_RIVERSHAPE_WINDCONST = SyntheticEvent(
        SyntheticEventModel(
            name="extreme12ft_rivershape_windconst",
            time=TimeModel(
                start_time=datetime(2020, 1, 1), end_time=datetime(2020, 1, 2)
            ),
            description="extreme 12 foot event",
            forcings={
                ForcingType.WIND: [
                    WindConstant(
                        direction=us.UnitfulDirection(
                            value=60, units=us.UnitTypesDirection.degrees
                        ),
                        speed=us.UnitfulVelocity(
                            value=10, units=us.UnitTypesVelocity.mps
                        ),
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
                        timeseries=SyntheticTimeseriesModel[us.UnitfulDischarge](
                            shape_type=ShapeType.block,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
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
                            timeseries=SyntheticTimeseriesModel(
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
    )

    FLORENCE = HurricaneEvent(
        HurricaneEventModel(
            name="FLORENCE",
            time=TimeModel(
                start_time=datetime(2019, 8, 30), end_time=datetime(2019, 9, 1)
            ),
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
                        timeseries=SyntheticTimeseriesModel(
                            shape_type=ShapeType.block,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulDischarge(
                                value=10000, units=us.UnitTypesDischarge.cfs
                            ),
                        ),
                    )
                ],
                ForcingType.WATERLEVEL: [WaterlevelModel()],
            },
        )
    )

    KINGTIDE_NOV2021 = HistoricalEvent(
        HistoricalEventModel(
            name="kingTideNov2021",
            time=TimeModel(
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
                        timeseries=SyntheticTimeseriesModel(
                            shape_type=ShapeType.block,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulDischarge(
                                value=10000, units=us.UnitTypesDischarge.cfs
                            ),
                        ),
                    ),
                ],
                ForcingType.RAINFALL: [RainfallMeteo()],
                ForcingType.WIND: [WindMeteo()],
                ForcingType.WATERLEVEL: [WaterlevelModel()],
            },
        )
    )
    return EXTREME_12FT, EXTREME_12FT_RIVERSHAPE_WINDCONST, FLORENCE, KINGTIDE_NOV2021


if __name__ == "__main__":
    from flood_adapt import Settings
    from flood_adapt.api.static import read_database

    Settings(
        database_name="charleston_test",
        database_root=Path(__file__).parents[3] / "Database",
    )
    db = read_database(Settings().database_root, Settings().database_name)

    for event in create_events():
        db.events.save(event, overwrite=True)
