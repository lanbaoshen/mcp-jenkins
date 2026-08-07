from typing import Optional

from pydantic import BaseModel


class Artifact(BaseModel):
    fileName: str
    relativePath: str
    displayPath: str | None = None


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


# The wfapi URL fields (proceedUrl, abortUrl, redirectApprovalUrl) are deliberately not modeled: they
# embed the input id already URL-encoded, and exposing them invites feeding that encoded segment back
# as input_id, which gets encoded a second time on submission.
class PendingInput(BaseModel):
    id: str

    message: str | None = None
    proceedText: str | None = None

    inputs: list[dict] = []
