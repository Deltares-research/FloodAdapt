import pandas as pd
import pytest

from flood_adapt.adapter.sfincs_offshore import OffshoreSfincsHandler
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.historical import (
    HistoricalEvent,
    HistoricalEventModel,
)
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
)
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallMeteo,
)
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelModel,
)
from flood_adapt.object_model.hazard.forcing.wind import (
    WindMeteo,
)
from flood_adapt.object_model.hazard.interface.forcing import ForcingType
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.interface.config.sfincs import RiverModel
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.scenario import Scenario


@pytest.fixture()
def setup_offshore_scenario(test_db: IDatabase):
    event = HistoricalEvent(
        HistoricalEventModel(
            name="test_historical_offshore_meteo",
            time=TimeModel(),
            forcings={
                ForcingType.WATERLEVEL: [WaterlevelModel()],
                ForcingType.WIND: [WindMeteo()],
                ForcingType.RAINFALL: [RainfallMeteo()],
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
            },
        )
    )
    test_db.events.save(event)

    scn = Scenario(
        ScenarioModel(
            name="test_scenario",
            event=event.attrs.name,
            projection="current",
            strategy="no_measures",
        )
    )
    test_db.scenarios.save(scn)

    return test_db, scn, event


class TestOffshoreSfincsHandler:
    def test_process_sfincs_offshore(
        self, setup_offshore_scenario: tuple[IDatabase, Scenario, HistoricalEvent]
    ):
        # Arrange
        _, scenario, _ = setup_offshore_scenario

        # Act
        wl_df = OffshoreSfincsHandler().get_resulting_waterlevels(scenario)

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
