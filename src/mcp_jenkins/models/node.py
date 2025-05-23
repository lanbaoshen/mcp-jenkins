from pydantic import BaseModel


class Node(BaseModel):
    name: str
    offline: bool
