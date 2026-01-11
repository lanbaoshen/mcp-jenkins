from pydantic import BaseModel, HttpUrl


class Queue(BaseModel):
    discoverableItems: list
    items: list['QueueItem']


class QueueItem(BaseModel):
    id: int
    inQueueSince: int
    url: HttpUrl
    why: str | None

    task: 'QueueItemTask'


class QueueItemTask(BaseModel):
    fullDisplayName: str = None
    name: str = None
    url: HttpUrl = None
