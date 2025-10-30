import platform

import pandas as pd
import pytest

from flood_adapt.adapter.sfincs_offshore import OffshoreSfincsHandler
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.objects import (
    HistoricalEvent,
    Scenario,
)


@pytest.mark.skipif(
    platform.system() == "Linux",
    reason="Skipped on Linux due to broken sfincs binary",
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
