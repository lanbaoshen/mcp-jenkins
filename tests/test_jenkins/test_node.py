import pytest

from mcp_jenkins.jenkins._node import JenkinsNode
from mcp_jenkins.models.node import Node


@pytest.fixture()
def jenkins_node(mock_jenkins):
    mock_jenkins.get_nodes.return_value = [
        {'name': 'node-000', 'offline': False},
        {'name': 'node-001', 'offline': True},
    ]
    mock_jenkins.get_node_config.return_value = '<node>...</node>'

    yield JenkinsNode(mock_jenkins)


def test_to_model(jenkins_node):
    data = {'name': 'node-000', 'offline': False}
    model = jenkins_node._to_model(data)
    assert model == Node(name='node-000', offline=False)


def test_get_all_nodes(jenkins_node):
    nodes = jenkins_node.get_all_nodes()
    assert nodes == [
        Node(name='node-000', offline=False),
        Node(name='node-001', offline=True),
    ]


def test_get_node_config(jenkins_node):
    config = jenkins_node.get_node_config('node-000')
    assert config == '<node>...</node>'
