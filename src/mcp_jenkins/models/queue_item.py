from pydantic import BaseModel


class _QueueItemTask(BaseModel):
    fullDisplayName: str = None
    name: str = None
    url: str = None


class QueueItem(BaseModel):
    id: int
    inQueueSince: int
    url: str
    why: str

    task: '_QueueItemTask'
