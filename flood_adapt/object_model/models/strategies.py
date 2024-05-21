from typing import Optional

from pydantic import BaseModel, Field


class StrategyModel(BaseModel):
    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    measures: Optional[list[str]] = []
