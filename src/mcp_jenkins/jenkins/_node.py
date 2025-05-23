from jenkins import Jenkins

from mcp_jenkins.models.node import Node


class JenkinsNode:
    def __init__(self, jenkins: Jenkins) -> None:
        self._jenkins = jenkins

    @staticmethod
    def _to_model(data: dict) -> Node:
        return Node.model_validate(data)

    def get_all_nodes(self) -> list[Node]:
        return [self._to_model(node) for node in self._jenkins.get_nodes()]

    def get_node_config(self, name: str) -> str:
        return self._jenkins.get_node_config(name)
