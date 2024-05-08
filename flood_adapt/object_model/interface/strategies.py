from typing import Optional

from .objectModel import IDbsObject, DbsObjectModel


class StrategyModel(DbsObjectModel):
    measures: Optional[list[str]] = []


class IStrategy(IDbsObject):
    attrs: StrategyModel
