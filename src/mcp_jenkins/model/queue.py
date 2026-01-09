from pydantic import BaseModel


class Queue(BaseModel):
    discoverableItems: list
    items: list['QueueItem']


class QueueItem(BaseModel):
    id: int
    inQueueSince: int
    url: str
    why: str | None

    task: 'QueueItemTask'


class QueueItemTask(BaseModel):
    fullDisplayName: str = None
    name: str = None
    url: str = None
