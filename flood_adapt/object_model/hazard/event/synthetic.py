import os
from typing import Any, Union

import tomli

from flood_adapt.object_model.interface.events import (
    IEvent,
    SyntheticEventModel,
)


class SyntheticEvent(IEvent):
    """
    Event class that is described by a validated EventModel.
    """

    attrs: SyntheticEventModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> "SyntheticEvent":
        """create SyntheticEvent from toml file"""
        obj = SyntheticEvent()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SyntheticEventModel.model_validate(toml)

    @staticmethod
    def load_dict(data: dict[str, Any]) -> "SyntheticEvent":
        """create SyntheticEvent from object, e.g. when initialized from GUI"""
        obj = SyntheticEvent()
        obj.attrs = SyntheticEventModel.model_validate(data)
        return obj
