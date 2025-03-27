import tempfile
from pathlib import Path

import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.hurricane import (
    HurricaneEvent,
    HurricaneEventModel,
)
from flood_adapt.object_model.hazard.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.forcing.rainfall import RainfallTrack
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelModel,
)
from flood_adapt.object_model.hazard.forcing.wind import WindTrack
from flood_adapt.object_model.hazard.interface.events import (
    ForcingType,
)
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.interface.config.sfincs import RiverModel
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.scenario import Scenario
from tests.fixtures import TEST_DATA_DIR


@pytest.fixture()
def setup_hurricane_event() -> tuple[HurricaneEvent, Path]:
    cyc_file = TEST_DATA_DIR / "IAN.cyc"
    event = HurricaneEvent(
        HurricaneEventModel(
            name="hurricane",
            time=TimeModel(),
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
        ),
    )
    return event


@pytest.fixture()
def setup_hurricane_scenario(
    test_db: IDatabase, setup_hurricane_event: HurricaneEvent
) -> tuple[Scenario, HurricaneEvent]:
    event = setup_hurricane_event
    scn = Scenario(
        ScenarioModel(
            name="test_scenario",
            event=event.attrs.name,
            projection="current",
            strategy="no_measures",
        )
    )
    test_db.events.save(event)
    test_db.scenarios.save(scn)
    return scn, event


class TestHurricaneEvent:
    def test_save_event_toml_and_track_file(
        self, setup_hurricane_event: HurricaneEvent, tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        event = setup_hurricane_event

        event.save(path)

        cyc_file = path.parent / f"{event.attrs.track_name}.cyc"
        assert path.exists()
        assert cyc_file.exists()

    def test_load_file(self, setup_hurricane_event: HurricaneEvent, tmp_path: Path):
        path = tmp_path / "test_event.toml"
        saved_event = setup_hurricane_event
        saved_event.save(path)
        cyc_file = path.parent / f"{saved_event.attrs.track_name}.cyc"
        assert path.exists()
        assert cyc_file.exists()

        loaded_event = HurricaneEvent.load_file(path)

        assert loaded_event == saved_event

    def test_load_file_raises_when_files_are_missing(
        self, setup_hurricane_event: HurricaneEvent, tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        saved_event = setup_hurricane_event
        saved_event.save(path)
        assert path.exists()
        cyc_file = path.parent / f"{saved_event.attrs.track_name}.cyc"

        cyc_file.unlink()
        assert not cyc_file.exists()

        with pytest.raises(FileNotFoundError) as e:
            HurricaneEvent.load_file(path)

        assert f"File {cyc_file.name} not found in {path.parent}" in str(e.value)

    def test_save_additional_saves_cyc_file(
        self, setup_hurricane_event: HurricaneEvent
    ):
        # Arrange
        event = setup_hurricane_event
        toml_path = Path(tempfile.gettempdir()) / "test_event.toml"

        # Act
        event.save_additional(toml_path.parent)

        # Assert
        cyc_file = toml_path.parent / f"{event.attrs.track_name}.cyc"
        assert cyc_file.exists()
