import pytest

from mcp_jenkins.jenkins._queue_item import JenkinsQueueItem
from mcp_jenkins.models.queue_item import QueueItem, _QueueItemTask


@pytest.fixture()
def jenkins_queue_item(mock_jenkins):
    mock_jenkins.get_queue_info.return_value = [
        {
            '_class': 'hudson.model.Queue$BuildableItem',
            'actions': [],
            'blocked': False,
            'buildable': True,
            'id': 53213,
            'inQueueSince': 1747990548424,
            'params': '',
            'stuck': False,
            'task': {'_class': 'org.jenkinsci.plugins.workflow.support.steps.ExecutorStepExecution$PlaceholderTask'},
            'url': 'queue/item/53213/',
            'why': 'Waiting for next available executor on ‘node 000’',
            'buildableStartMilliseconds': 1747990548424,
            'pending': False,
        }
    ]
    mock_jenkins.get_queue_item.return_value = {
        '_class': 'hudson.model.Queue$BuildableItem',
        'actions': [],
        'blocked': False,
        'buildable': True,
        'id': 53213,
        'inQueueSince': 1747990548424,
        'params': '',
        'stuck': False,
        'task': {
            '_class': 'org.jenkinsci.plugins.workflow.support.steps.ExecutorStepExecution$PlaceholderTask',
            'fullDisplayName': 'name',
            'name': 'name',
            'url': 'url',
        },
        'url': 'queue/item/53213/',
        'why': 'Waiting for next available executor on ‘node 000’',
        'buildableStartMilliseconds': 1747990548424,
        'pending': False,
    }
    mock_jenkins.cancel_queue_item.return_value = None

    yield JenkinsQueueItem(mock_jenkins)


def test_to_model(jenkins_queue_item):
    model = jenkins_queue_item._to_model(
        {
            '_class': 'hudson.model.Queue$BuildableItem',
            'actions': [],
            'blocked': False,
            'buildable': True,
            'id': 53213,
            'inQueueSince': 1747990548424,
            'params': '',
            'stuck': False,
            'task': {
                '_class': 'org.jenkinsci.plugins.workflow.support.steps.ExecutorStepExecution$PlaceholderTask',
                'fullDisplayName': 'name',
                'name': 'name',
                'url': 'url',
            },
            'url': 'queue/item/53213/',
            'why': 'Waiting for next available executor on ‘node 000’',
            'buildableStartMilliseconds': 1747990548424,
            'pending': False,
        }
    )

    assert model == QueueItem(
        id=53213,
        inQueueSince=1747990548424,
        url='queue/item/53213/',
        why='Waiting for next available executor on ‘node 000’',
        task=_QueueItemTask(
            fullDisplayName='name',
            name='name',
            url='url',
        ),
    )


def test_get_all_queue_items(jenkins_queue_item):
    queue_items = jenkins_queue_item.get_all_queue_items()
    print(queue_items)
    assert queue_items == [
        QueueItem(
            id=53213,
            inQueueSince=1747990548424,
            url='queue/item/53213/',
            why='Waiting for next available executor on ‘node 000’',
            task=_QueueItemTask(),
        )
    ]


def test_get_queue_item(jenkins_queue_item):
    queue_item = jenkins_queue_item.get_queue_item(id_=53213)
    assert queue_item == QueueItem(
        id=53213,
        inQueueSince=1747990548424,
        url='queue/item/53213/',
        why='Waiting for next available executor on ‘node 000’',
        task=_QueueItemTask(
            fullDisplayName='name',
            name='name',
            url='url',
        ),
    )


def test_cancel_queue_item(jenkins_queue_item):
    assert jenkins_queue_item.cancel_queue_item(id_=53213) is None
