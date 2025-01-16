import shutil
import tempfile
from pathlib import Path

import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.hurricane import HurricaneEvent
from flood_adapt.object_model.hazard.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallTrack,
)
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelModel,
)
from flood_adapt.object_model.hazard.forcing.wind import (
    WindTrack,
)
from flood_adapt.object_model.hazard.interface.events import (
    ForcingType,
    Mode,
    Template,
)
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.interface.config.sfincs import RiverModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.scenario import Scenario
from tests.fixtures import TEST_DATA_DIR


@pytest.fixture()
def setup_hurricane_event() -> tuple[HurricaneEvent, Path]:
    event_attrs = {
        "name": "hurricane",
        "time": TimeModel(),
        "template": Template.Hurricane,
        "mode": Mode.single_event,
        "forcings": {
            "WATERLEVEL": [WaterlevelModel()],
            "WIND": [WindTrack()],
            "RAINFALL": [RainfallTrack()],
            "DISCHARGE": [
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
        "track_name": "IAN",
        "hurricane_translation": {
            "eastwest_translation": us.UnitfulLength(
                value=0.0, units=us.UnitTypesLength.meters
            ),
            "northsouth_translation": us.UnitfulLength(
                value=0.0, units=us.UnitTypesLength.meters
            ),
        },
    }
    return HurricaneEvent.load_dict(event_attrs), TEST_DATA_DIR / "IAN.cyc"


@pytest.fixture()
def setup_hurricane_scenario(
    test_db: IDatabase, setup_hurricane_event: tuple[HurricaneEvent, Path]
) -> tuple[Scenario, HurricaneEvent]:
    event, cyc_file = setup_hurricane_event
    scenario_attrs = {
        "name": "test_scenario",
        "event": event.attrs.name,
        "projection": "current",
        "strategy": "no_measures",
    }
    scn = Scenario.load_dict(scenario_attrs)
    test_db.events.save(event)
    shutil.copy2(cyc_file, test_db.events.input_path / event.attrs.name / cyc_file.name)
    test_db.scenarios.save(scn)
    return scn, event


class TestHurricaneEvent:
    def test_save_event_toml(
        self, setup_hurricane_event: tuple[HurricaneEvent, Path], tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        event, cyc_file = setup_hurricane_event
        event.save(path)
        event.attrs.forcings[ForcingType.WIND].path = cyc_file

        event.save_additional(path.parent)
        assert path.exists()
        assert (path.parent / cyc_file.name).exists()

    def test_load_file(
        self, setup_hurricane_event: tuple[HurricaneEvent, Path], tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        saved_event, cyc_file = setup_hurricane_event
        saved_event.save(path)
        assert path.exists()

        loaded_event = HurricaneEvent.load_file(path)

        assert loaded_event == saved_event

    def test_make_spw_file_with_args(
        self,
        setup_hurricane_event: tuple[HurricaneEvent, Path],
    ):
        # Arrange
        cyc_file = TEST_DATA_DIR / "IAN.cyc"
        spw_file = Path(tempfile.gettempdir()) / "IAN.spw"
        hurricane_event, cyc_file = setup_hurricane_event
        hurricane_event.attrs.track_name = "IAN"
        hurricane_event.track_file = cyc_file

        # Act
        hurricane_event.make_spw_file(recreate=True, output_dir=spw_file.parent)

        # Assert
        assert spw_file.exists()

    def test_make_spw_file_no_args(
        self, setup_hurricane_event: tuple[HurricaneEvent, Path], test_db: IDatabase
    ):
        # Arrange
        hurricane_event, cyc_file = setup_hurricane_event
        spw_file = test_db.events.input_path / hurricane_event.attrs.name / "IAN.spw"
        hurricane_event.attrs.track_name = "IAN"
        test_db.events.save(hurricane_event)

        shutil.copy2(
            cyc_file,
            test_db.events.input_path / hurricane_event.attrs.name / "IAN.cyc",
        )

        # Act
        hurricane_event.make_spw_file()

        # Assert
        assert spw_file.exists()

    def test_save_additional_saves_cyc_file(
        self, setup_hurricane_event: tuple[HurricaneEvent, Path]
    ):
        # Arrange
        event, cyc_file = setup_hurricane_event
        event.track_file = cyc_file
        toml_path = Path(tempfile.gettempdir()) / "test_event.toml"

        # Act
        event.save_additional(toml_path.parent)

        # Assert
        assert (toml_path.parent / cyc_file.name).exists()
