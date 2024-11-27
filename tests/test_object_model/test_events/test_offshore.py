import pandas as pd
import pytest
from adapter.sfincs_offshore import OffshoreSfincsHandler
from dbs_classes.interface.database import IDatabase
from object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
)
from object_model.hazard.event.forcing.rainfall import (
    RainfallMeteo,
)
from object_model.hazard.event.forcing.waterlevels import (
    WaterlevelModel,
)
from object_model.hazard.event.forcing.wind import (
    WindMeteo,
)
from object_model.hazard.event.historical import HistoricalEvent
from object_model.hazard.interface.models import (
    Mode,
    Template,
    TimeModel,
)
from object_model.interface.site import RiverModel
from object_model.io import unit_system as us
from object_model.scenario import Scenario


@pytest.fixture()
def setup_offshore_scenario(test_db: IDatabase):
    event_attrs = {
        "name": "test_historical_offshore_meteo",
        "time": TimeModel(),
        "template": Template.Historical,
        "mode": Mode.single_event,
        "forcings": {
            "WATERLEVEL": WaterlevelModel(),
            "WIND": WindMeteo(),
            "RAINFALL": RainfallMeteo(),
            "DISCHARGE": DischargeConstant(
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
        },
    }

    event = HistoricalEvent.load_dict(event_attrs)
    test_db.events.save(event)

    scenario_attrs = {
        "name": "test_scenario",
        "event": event.attrs.name,
        "projection": "current",
        "strategy": "no_measures",
    }
    scn = Scenario.load_dict(scenario_attrs)
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
