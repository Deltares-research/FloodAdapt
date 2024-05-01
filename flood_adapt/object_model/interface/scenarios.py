import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel, Field
from .objectModel import ObjectModel, IObject

class ScenarioModel(ObjectModel):
    """BaseModel describing the expected variables and data types of a scenario"""

    event: str
    projection: str
    strategy: str


class IScenario(IObject):
    attrs: ScenarioModel


    @abstractmethod
    def run(self) -> None: ...
