import pytest

from mcp_jenkins.jenkins.model.queue import Queue, QueueItem, QueueItemTask
from mcp_jenkins.server import queue


@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()

    mocker.patch('mcp_jenkins.server.queue.jenkins', return_value=mock_jenkins)

    yield mock_jenkins


@pytest.mark.asyncio
async def test_get_all_queue_items(mock_jenkins, mocker):
    q_item1 = QueueItem(id=1, inQueueSince=1, url='1', why='1', task=QueueItemTask())
    q_item2 = QueueItem(id=2, inQueueSince=2, url='2', why='2', task=QueueItemTask())

    mock_jenkins.get_queue.return_value = Queue(discoverableItems=[], items=[q_item1, q_item2])
    assert await queue.get_all_queue_items.fn(mocker.Mock()) == [
        {'id': 1, 'inQueueSince': 1, 'url': '1', 'why': '1'},
        {'id': 2, 'inQueueSince': 2, 'url': '2', 'why': '2'},
    ]


@pytest.mark.asyncio
async def test_get_queue_item(mock_jenkins, mocker):
    q_item = QueueItem(
        id=1, inQueueSince=1, url='1', why='1', task=QueueItemTask(fullDisplayName='1', name='1', url='1')
    )

    mock_jenkins.get_queue_item.return_value = q_item
    assert await queue.get_queue_item.fn(mocker.Mock(), id=1) == {
        'id': 1,
        'inQueueSince': 1,
        'url': '1',
        'why': '1',
        'task': {'fullDisplayName': '1', 'name': '1', 'url': '1'},
    }


@pytest.mark.asyncio
async def test_cancel_queue_item(mock_jenkins, mocker):
    await queue.cancel_queue_item.fn(mocker.Mock(), id=1)
    mock_jenkins.cancel_queue_item.assert_called_once_with(id=1)
