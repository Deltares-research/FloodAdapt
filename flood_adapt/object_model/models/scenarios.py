from typing import Optional

from pydantic import BaseModel, Field


class ScenarioModel(BaseModel):
    """BaseModel describing the expected variables and data types of a scenario"""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    event: str
    projection: str
    strategy: str

