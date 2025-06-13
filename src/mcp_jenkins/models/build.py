from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Build(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    number: int
    url: str

    # The following fields are determined by the depth when get info
    name: str = None
    node: str = None

    class_: str | None = Field(None, alias='_class')
    building: bool = None
    duration: int = None
    estimatedDuration: int = None
    result: str | None = None
    timestamp: int = None
    inProgress: bool = None
    nextBuild: Optional['Build'] = None
    previousBuild: Optional['Build'] = None
