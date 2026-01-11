from typing import Optional

from pydantic import BaseModel, HttpUrl


class Node(BaseModel):
    displayName: str
    offline: bool

    executors: list['NodeExecutor']


class NodeExecutor(BaseModel):
    currentExecutable: Optional['NodeExecutorCurrentExecutable'] = None


class NodeExecutorCurrentExecutable(BaseModel):
    url: HttpUrl = None
    timestamp: int = None
    number: int = None
    fullDisplayName: str = None
