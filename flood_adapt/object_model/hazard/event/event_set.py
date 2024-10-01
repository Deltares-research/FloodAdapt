import shutil
from pathlib import Path
from typing import ClassVar, List

from pydantic import Field
from typing_extensions import Annotated

from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    IEvent,
    IEventModel,
)
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.interface.scenarios import IScenario


class EventSetModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.MODEL,
            ForcingSource.TRACK,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.WIND: [
            ForcingSource.TRACK,
            ForcingSource.CONSTANT,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.WATERLEVEL: [ForcingSource.MODEL, ForcingSource.SYNTHETIC],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
    }

    sub_events: List[str]
    frequency: List[Annotated[float, Field(strict=True, ge=0, le=1)]]

    @staticmethod
    def default() -> "EventSetModel":
        """Set default values for Synthetic event."""
        return EventSetModel(
            name="EventSet",
            time=TimeModel(),
            template=Template.Synthetic,
            mode=Mode.risk,
            sub_events=["sub_event1", "sub_event2"],
            frequency=[0.5, 0.5],
            forcings={
                ForcingType.RAINFALL: ForcingFactory.get_default_forcing(
                    ForcingType.RAINFALL, ForcingSource.SYNTHETIC
                ),
                ForcingType.WIND: ForcingFactory.get_default_forcing(
                    ForcingType.WIND, ForcingSource.SYNTHETIC
                ),
                ForcingType.WATERLEVEL: ForcingFactory.get_default_forcing(
                    ForcingType.WATERLEVEL, ForcingSource.SYNTHETIC
                ),
                ForcingType.DISCHARGE: ForcingFactory.get_default_forcing(
                    ForcingType.DISCHARGE, ForcingSource.SYNTHETIC
                ),
            },
        )


class EventSet(IEvent):
    MODEL_TYPE = EventSetModel

    attrs: EventSetModel

    def process(self, scenario: IScenario = None):
        """Prepare the forcings of the event set.

        Which is to say, prepare the forcings of the subevents of the event set.

        If the forcings require it, this function will:
        - download meteo data: download the meteo data from the meteo source and store it in the output directory.
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        Then, it will call the process function of the subevents.

        """
        # @gundula, run offshore only once and then copy results?
        # Same for downloading meteo data
        # I dont think I've seen any code that changes the forcings of the subevents wrt eachother, is that correct?
        # So, just run the first subevent and then copy the results to the other subevents ?
        for sub_event in self.get_subevents():
            sub_event.process(scenario)

    def get_sub_event_paths(self) -> List[Path]:
        base_path = self.database.events.get_database_path() / self.attrs.name
        return [
            base_path / sub_name / f"{sub_name}.toml"
            for sub_name in self.attrs.sub_events
        ]

    def get_subevents(self) -> List[IEvent]:
        from flood_adapt.object_model.hazard.event.event_factory import EventFactory

        paths = self.get_sub_event_paths()
        base_event = self.attrs.model_dump(exclude={"sub_events", "frequency", "mode"})
        base_event["mode"] = Mode.single_event

        if not all(path.exists() for path in paths):
            # something went wrong, we need to recreate the subevents
            for path in paths:
                if path.parent.exists():
                    shutil.rmtree(path.parent)

            for sub_name in self.attrs.sub_events:
                sub_event = EventFactory.load_dict(base_event)
                sub_event.attrs.name = sub_name

                subdir = (
                    self.database.events.get_database_path()
                    / self.attrs.name
                    / sub_name
                )
                subdir.mkdir(parents=True, exist_ok=True)
                toml_path = subdir / f"{sub_name}.toml"

                sub_event.save(toml_path)

        return [EventFactory.load_file(path) for path in paths]
