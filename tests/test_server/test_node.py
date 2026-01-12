import pytest

from mcp_jenkins.jenkins.model.node import Node
from mcp_jenkins.server import node


@pytest.fixture()
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()

    mocker.patch('mcp_jenkins.server.node.jenkins', return_value=mock_jenkins)

    yield mock_jenkins


@pytest.mark.asyncio
async def test_get_all_queue_items(mock_jenkins, mocker):
    node1 = Node(displayName='node1', offline=False, executors=[])
    node2 = Node(displayName='node2', offline=True, executors=[])

    mock_jenkins.get_nodes.return_value = [node1, node2]
    assert await node.get_all_nodes.fn(mocker.Mock()) == [
        {'displayName': 'node1', 'offline': False},
        {'displayName': 'node2', 'offline': True},
    ]


@pytest.mark.asyncio
async def test_get_node(mock_jenkins, mocker):
    node1 = Node(displayName='node1', offline=False, executors=[])

    mock_jenkins.get_node.return_value = node1
    assert await node.get_node.fn(mocker.Mock(), name='node1') == {
        'displayName': 'node1',
        'offline': False,
        'executors': [],
    }


@pytest.mark.asyncio
async def test_get_node_config(mock_jenkins, mocker):
    mock_jenkins.get_node_config.return_value = '<node>config</node>'
    assert await node.get_node_config.fn(mocker.Mock(), name='node1') == '<node>config</node>'
