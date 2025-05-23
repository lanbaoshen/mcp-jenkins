from jenkins import Jenkins

from mcp_jenkins.models.queue_item import QueueItem


class JenkinsQueueItem:
    def __init__(self, jenkins: Jenkins) -> None:
        self._jenkins = jenkins

    @staticmethod
    def _to_model(data: dict) -> QueueItem:
        return QueueItem.model_validate(data)

    def get_all_queue_items(self) -> list[QueueItem]:
        return [self._to_model(item) for item in self._jenkins.get_queue_info()]

    def get_queue_item(self, id_: int) -> QueueItem:
        return self._to_model(self._jenkins.get_queue_item(id_, depth=1))

    def cancel_queue_item(self, id_: int) -> None:
        self._jenkins.cancel_queue(id_)
