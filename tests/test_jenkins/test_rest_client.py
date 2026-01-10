import pytest
from pydantic import HttpUrl
from requests import HTTPError

from mcp_jenkins.jenkins.rest_client import Jenkins
from mcp_jenkins.model.build import Build, BuildReplay
from mcp_jenkins.model.node import Node, NodeExecutor, NodeExecutorCurrentExecutable
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


class TestNode:
    def test_get_node(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'displayName': 'node-1',
                'offline': False,
                'executors': [
                    {
                        'currentExecutable': {
                            'url': 'https://example.com/job/example-job/1/',
                            'timestamp': 1767975558000,
                            'number': 1,
                            'fullDisplayName': 'Example Job #1',
                        }
                    }
                ],
            }
        )

        assert jenkins.get_node(name='node-1') == Node(
            displayName='node-1',
            offline=False,
            executors=[
                NodeExecutor(
                    currentExecutable=NodeExecutorCurrentExecutable(
                        url=HttpUrl('https://example.com/job/example-job/1/'),
                        timestamp=1767975558000,
                        number=1,
                        fullDisplayName='Example Job #1',
                    )
                )
            ],
        )

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/computer/node-1/api/json?depth=0',
            headers={'Jenkins-Crumb': 'crumb-value'},
        )

    def test_get_node_master(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'displayName': 'Built-In Node',
                'offline': False,
                'executors': [
                    {
                        'currentExecutable': {
                            'url': 'https://example.com/job/example-job/1/',
                            'timestamp': 1767975558000,
                            'number': 1,
                            'fullDisplayName': 'Example Job #1',
                        }
                    }
                ],
            }
        )

        assert jenkins.get_node(name='Built-In Node') == Node(
            displayName='Built-In Node',
            offline=False,
            executors=[
                NodeExecutor(
                    currentExecutable=NodeExecutorCurrentExecutable(
                        url=HttpUrl('https://example.com/job/example-job/1/'),
                        timestamp=1767975558000,
                        number=1,
                        fullDisplayName='Example Job #1',
                    )
                )
            ],
        )

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/computer/(master)/api/json?depth=0',
            headers={'Jenkins-Crumb': 'crumb-value'},
        )

    def test_get_nodes(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'computer': [
                    {
                        'displayName': 'node-1',
                        'offline': False,
                        'executors': [],
                    },
                    {
                        'displayName': 'Built-In Node',
                        'offline': True,
                        'executors': [],
                    },
                ]
            }
        )

        assert jenkins.get_nodes() == [
            Node(displayName='node-1', offline=False, executors=[]),
            Node(displayName='Built-In Node', offline=True, executors=[]),
        ]

    def test_get_node_config(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(text='<node>config</node>')

        assert jenkins.get_node_config(name='node-1') == '<node>config</node>'


class TestBuild:
    def test_get_build(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'number': 2,
                'url': 'https://example.com/job/example-job/2/',
                'timestamp': 1767975558000,
                'duration': 120000,
                'estimatedDuration': 130000,
                'building': False,
                'result': 'SUCCESS',
                'nextBuild': None,
                'previousBuild': {
                    'number': 1,
                    'url': 'https://example.com/job/example-job/1/',
                },
            }
        )

        assert jenkins.get_build(fullname='example-job', number=1) == Build(
            number=2,
            url='https://example.com/job/example-job/2/',
            timestamp=1767975558000,
            duration=120000,
            estimatedDuration=130000,
            building=False,
            result='SUCCESS',
            nextBuild=None,
            previousBuild=Build(
                number=1,
                url='https://example.com/job/example-job/1/',
            ),
        )

    def test_get_build_console_output(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(text='Console output here')

        assert jenkins.get_build_console_output(fullname='example-job', number=1) == 'Console output here'

    def test_stop_build(self, jenkins, mock_session):
        assert jenkins.stop_build(fullname='example-job', number=42) is None

        mock_session.request.assert_called_once_with(
            method='POST',
            url='https://example.com/job/example-job/42/stop',
            headers={'Jenkins-Crumb': 'crumb-value'},
        )

    def test_get_build_replay(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            text=(
                '<textarea name="_.mainScript" checkMethod="post">main script code here</textarea>'
                '<textarea name="_.additionalScripts" checkMethod="post">additional script code here</textarea>'
                '<body>Foo</body>'
            )
        )

        assert jenkins.get_build_replay(fullname='example-job', number=1) == BuildReplay(
            scripts=['main script code here', 'additional script code here']
        )

    def test_get_build_test_report(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'suites': [
                    {
                        'name': 'Example Suite',
                        'cases': [
                            {
                                'name': 'test_case_1',
                                'className': 'ExampleTest',
                                'status': 'PASSED',
                            },
                            {
                                'name': 'test_case_2',
                                'className': 'ExampleTest',
                                'status': 'FAILED',
                                'errorDetails': 'AssertionError: expected X but got Y',
                            },
                        ],
                    }
                ]
            }
        )

        assert jenkins.get_build_test_report(fullname='example-job', number=1) == {
            'suites': [
                {
                    'name': 'Example Suite',
                    'cases': [
                        {
                            'name': 'test_case_1',
                            'className': 'ExampleTest',
                            'status': 'PASSED',
                        },
                        {
                            'name': 'test_case_2',
                            'className': 'ExampleTest',
                            'status': 'FAILED',
                            'errorDetails': 'AssertionError: expected X but got Y',
                        },
                    ],
                }
            ]
        }

    def test_get_running_builds(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'computer': [
                    {
                        'displayName': 'node-1',
                        'offline': False,
                        'executors': [
                            {
                                'currentExecutable': {
                                    'number': 3,
                                    'url': 'https://example.com/job/example-job/3/',
                                    'timestamp': 1767975558000,
                                    'fullDisplayName': 'Example Job #3',
                                }
                            }
                        ],
                    }
                ]
            }
        )

        assert jenkins.get_running_builds() == [
            Build(
                url='https://example.com/job/example-job/3/',
                number=3,
                timestamp=1767975558000,
            )
        ]
