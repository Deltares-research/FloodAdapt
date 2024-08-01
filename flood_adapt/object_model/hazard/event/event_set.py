import shutil
from typing import List

from pydantic import Field

from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    IEvent,
    IEventModel,
)
from flood_adapt.object_model.hazard.interface.models import Mode
from flood_adapt.object_model.interface.scenarios import IScenario


class EventSetModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    ALLOWED_FORCINGS: dict[ForcingType, List[ForcingSource]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.MODEL,
            ForcingSource.TRACK,
        ],
        ForcingType.WIND: [ForcingSource.TRACK],
        ForcingType.WATERLEVEL: [ForcingSource.MODEL],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
    }

    sub_events: List[str]
    frequency: List[float] = Field(gt=0, lt=1)


class EventSet(IEvent):
    MODEL_TYPE = EventSetModel

    attrs: EventSetModel

    def process(self, scenario: IScenario):
        """Prepare the forcings of the event set.

        Which is to say, prepare the forcings of the subevents of the event set.

        If the forcings require it, this function will:
        - download meteo data: download the meteo data from the meteo source and store it in the output directory.
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        Then, it will call the process function of the subevents.

        """
        for sub_event in self.get_subevents():
            sub_event.process(scenario)

    def get_subevents(self) -> List[IEvent]:
        base_path = self.database.events.get_database_path() / self.attrs.name
        base_event = self.attrs.model_dump(exclude={"sub_events", "frequency", "mode"})
        base_event.attrs.mode = Mode.single_event

        sub_event_paths = [
            base_path / sub_name / f"{sub_name}.toml"
            for sub_name in self.attrs.sub_events
        ]
        if not all(path.exists() for path in sub_event_paths):
            # something went wrong, we need to recreate the subevents
            for path in sub_event_paths:
                if path.parent.exists():
                    shutil.rmtree(path.parent)

            for sub_name in self.attrs.sub_events:
                sub_event = EventFactory.load_dict(base_event)
                sub_event.attrs.name = sub_name

                subdir = base_path / sub_name
                subdir.mkdir(parents=True, exist_ok=True)
                toml_path = subdir / f"{sub_name}.toml"

                sub_event.save(toml_path)

        return [EventFactory.load_file(path) for path in sub_event_paths]
