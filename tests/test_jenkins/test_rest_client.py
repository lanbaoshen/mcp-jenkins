import pytest
from pydantic import HttpUrl
from requests import HTTPError

from mcp_jenkins.jenkins.rest_client import Jenkins
from mcp_jenkins.model.queue import Queue, QueueItem, QueueItemTask


@pytest.fixture(autouse=True)
def mock_session(mocker):
    mock_session = mocker.Mock()
    mocker.patch('mcp_jenkins.jenkins.rest_client.requests.Session', autospec=True, return_value=mock_session)
    yield mock_session


@pytest.fixture
def jenkins(mocker):
    jenkins = Jenkins(url=HttpUrl('https://example.com/'), username='username', password='password')
    mocker.patch.object(
        Jenkins, 'crumb_header', new_callable=mocker.PropertyMock, return_value={'Jenkins-Crumb': 'crumb-value'}
    )
    return jenkins


def test_endpoint_url(jenkins):
    assert jenkins.endpoint_url('/api/json') == jenkins.endpoint_url('api/json') == 'https://example.com/api/json'


class TestRequest:
    def test_request_with_crumb(self, jenkins, mock_session):
        jenkins.request('GET', 'api/json', crumb=True)

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/api/json',
            headers={
                'Jenkins-Crumb': 'crumb-value',
            },
        )

    def test_request_without_crumb(self, jenkins, mock_session):
        jenkins.request('GET', 'api/json', crumb=False, headers={'Custom-Header': 'value'})

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/api/json',
            headers={
                'Custom-Header': 'value',
            },
        )


class TestCrumbHeader:
    def test_crumb_header(self, mocker):
        jenkins = Jenkins(url=HttpUrl('https://example.com/'), username='username', password='password')
        mocker.patch.object(
            jenkins,
            'request',
            return_value=mocker.Mock(json=lambda: {'crumbRequestField': 'Jenkins-Crumb', 'crumb': 'crumb-value'}),
        )
        assert jenkins.crumb_header == {'Jenkins-Crumb': 'crumb-value'}

    def test_crumb_header_404(self, mocker):
        jenkins = Jenkins(url=HttpUrl('https://example.com/'), username='username', password='password')
        mocker.patch.object(jenkins, 'request', side_effect=HTTPError(response=mocker.Mock(status_code=404)))

        assert jenkins.crumb_header == {}

    def test_crumb_header_other_http_error(self, mocker):
        jenkins = Jenkins(url=HttpUrl('https://example.com/'), username='username', password='password')
        mocker.patch.object(jenkins, 'request', side_effect=HTTPError(response=mocker.Mock(status_code=500)))

        with pytest.raises(HTTPError):
            _ = jenkins.crumb_header


def test_parse_fullname(jenkins):
    assert jenkins._parse_fullname('job-name') == ('', 'job-name')
    assert jenkins._parse_fullname('folder/job-name') == ('job/folder/', 'job-name')
    assert jenkins._parse_fullname('folder/subfolder/job-name') == ('job/folder/job/subfolder/', 'job-name')


class TestQueue:
    def test_get_queue(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'items': [
                    {
                        'id': 1,
                        'inQueueSince': 1767975558000,
                        'url': 'https://example.com/queue/item/1/',
                        'why': 'Waiting for next available executor',
                        'task': {
                            'fullDisplayName': 'Example Job',
                            'name': 'example-job',
                            'url': 'https://example.com/job/example-job/',
                        },
                    }
                ],
                'discoverableItems': [],
            }
        )

        assert jenkins.get_queue() == Queue(
            items=[
                QueueItem(
                    id=1,
                    inQueueSince=1767975558000,
                    url='https://example.com/queue/item/1/',
                    why='Waiting for next available executor',
                    task=QueueItemTask(
                        fullDisplayName='Example Job', name='example-job', url='https://example.com/job/example-job/'
                    ),
                )
            ],
            discoverableItems=[],
        )

    def test_get_queue_item(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'id': 1,
                'inQueueSince': 1767975558000,
                'url': 'https://example.com/queue/item/1/',
                'why': 'Waiting for next available executor',
                'task': {
                    'fullDisplayName': 'Example Job',
                    'name': 'example-job',
                    'url': 'https://example.com/job/example-job/',
                },
            }
        )

        assert jenkins.get_queue_item(id=1) == QueueItem(
            id=1,
            inQueueSince=1767975558000,
            url='https://example.com/queue/item/1/',
            why='Waiting for next available executor',
            task=QueueItemTask(
                fullDisplayName='Example Job', name='example-job', url='https://example.com/job/example-job/'
            ),
        )

    def test_cancel_queue_item(self, jenkins, mock_session):
        assert jenkins.cancel_queue_item(id=42) is None
        mock_session.request.assert_called_once_with(
            method='POST', url='https://example.com/queue/cancelItem?id=42', headers={'Jenkins-Crumb': 'crumb-value'}
        )
