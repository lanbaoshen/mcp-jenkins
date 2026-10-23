from pydantic import BaseModel, field_validator


class Queue(BaseModel):
    discoverableItems: list
    items: list['QueueItem']


class QueueItem(BaseModel):
    id: int
    inQueueSince: int
    url: str
    why: str | None

    task: 'QueueItemTask'
    executable: 'QueueItemExecutable | None' = None

    @field_validator('executable', mode='before')
    @classmethod
    def _empty_executable_is_none(cls, value: dict | None) -> dict | None:
        # Jenkins returns an empty object while the item is still waiting in the queue.
        return value or None


class QueueItemTask(BaseModel):
    fullDisplayName: str = None
    name: str = None
    url: str = None


class QueueItemExecutable(BaseModel):
    number: int
    url: str
