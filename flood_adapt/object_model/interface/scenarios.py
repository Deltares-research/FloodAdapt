from abc import abstractmethod

from .objectModel import IDbsObject, DbsObjectModel


class ScenarioModel(DbsObjectModel):
    """BaseModel describing the expected variables and data types of a scenario"""

    event: str
    projection: str
    strategy: str


class IScenario(IDbsObject):
    attrs: ScenarioModel

    @abstractmethod
    def run(self) -> None: ...
