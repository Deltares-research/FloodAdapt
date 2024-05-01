
from typing import Optional

from .objectModel import ObjectModel, IObject


class StrategyModel(ObjectModel):
    measures: Optional[list[str]] = []


class IStrategy(IObject):
    attrs: StrategyModel
 