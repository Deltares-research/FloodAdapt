import pandas as pd
import pytest

from flood_adapt.adapter.sfincs_offshore import OffshoreSfincsHandler
from flood_adapt.config.hazard import RiverModel
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.objects.events.historical import (
    HistoricalEvent,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import (
    DischargeConstant,
)
from flood_adapt.objects.forcing.forcing import ForcingType
from flood_adapt.objects.forcing.rainfall import (
    RainfallMeteo,
)
from flood_adapt.objects.forcing.time_frame import (
    TimeFrame,
)
from flood_adapt.objects.forcing.waterlevels import (
    WaterlevelModel,
)
from flood_adapt.objects.forcing.wind import (
    WindMeteo,
)
from flood_adapt.objects.scenarios.scenarios import Scenario
from tests.conftest import CAN_EXECUTE_SCENARIOS
from tests.test_adapter.test_sfincs_adapter import mock_meteohandler_read

__all__ = ["mock_meteohandler_read"]


@pytest.fixture()
def setup_offshore_scenario(test_db: IDatabase):
    event = HistoricalEvent(
        name="test_historical_offshore_meteo",
        time=TimeFrame(),
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
    test_db.events.add(event)

    scn = Scenario(
        name="test_scenario",
        event=event.name,
        projection="current",
        strategy="no_measures",
    )
    test_db.scenarios.add(scn)

    return test_db, scn, event


@pytest.mark.skipif(
    not CAN_EXECUTE_SCENARIOS,
    reason="Only run when we can execute scenarios. Requires either a working sfincs binary, or a working docker setup",
)
class TestOffshoreSfincsHandler:
    @pytest.mark.skip(
        reason="Skipped until METEO forcing is fixed in hydromt-sfincs 1.3.0",
    )
    def test_process_sfincs_offshore(
        self,
        setup_offshore_scenario: tuple[IDatabase, Scenario, HistoricalEvent],
        mock_meteohandler_read,
    ):
        # Arrange
        _, scenario, event = setup_offshore_scenario

        # Act
        wl_df = OffshoreSfincsHandler(
            scenario=scenario, event=event
        ).get_resulting_waterlevels()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
