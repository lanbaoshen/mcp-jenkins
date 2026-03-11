from typing import Any, Optional

from pydantic import BaseModel, field_validator


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

    parameters: dict[str, Any] | None = None
    actions: list[dict[str, Any]] | None = None

    @field_validator('actions', mode='before')
    @classmethod
    def _extract_parameters(cls, v: Any) -> list[dict[str, Any]] | None:
        """Store raw actions but also extract parameters for convenience."""
        return v


class BuildReplay(BaseModel):
    scripts: list[str]
