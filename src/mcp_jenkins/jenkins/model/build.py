from typing import Optional

from pydantic import BaseModel


class Build(BaseModel):
    number: int
    url: str

    timestamp: int = None
    duration: int = None
    estimatedDuration: int = None

    building: bool = None
    result: str | None = None

    nextBuild: Optional['Build'] = None
    previousBuild: Optional['Build'] = None


class BuildReplay(BaseModel):
    scripts: list[str]
