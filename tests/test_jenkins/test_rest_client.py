import pytest
from requests import HTTPError

from mcp_jenkins.jenkins import Jenkins
from mcp_jenkins.jenkins.model.build import Build, BuildReplay
from mcp_jenkins.jenkins.model.item import (
    Folder,
    FreeStyleProject,
    Job,
    MultiBranchProject,
)
from mcp_jenkins.jenkins.model.node import (
    Node,
    NodeExecutor,
    NodeExecutorCurrentExecutable,
)
from mcp_jenkins.jenkins.model.queue import Queue, QueueItem, QueueItemTask


@pytest.fixture(autouse=True)
def mock_session(mocker):
    mock_session = mocker.Mock()
    mocker.patch(
        'mcp_jenkins.jenkins.rest_client.requests.Session',
        autospec=True,
        return_value=mock_session,
    )
    yield mock_session


@pytest.fixture
def jenkins(mocker):
    jenkins = Jenkins(url='https://example.com/', username='username', password='password')
    mocker.patch.object(
        Jenkins,
        'crumb_header',
        new_callable=mocker.PropertyMock,
        return_value={'Jenkins-Crumb': 'crumb-value'},
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
            params=None,
            data=None,
            timeout=75,
        )

    def test_request_without_crumb(self, jenkins, mock_session):
        jenkins.request('GET', 'api/json', crumb=False, headers={'Custom-Header': 'value'})

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/api/json',
            headers={
                'Custom-Header': 'value',
            },
            params=None,
            data=None,
            timeout=75,
        )


class TestCrumbHeader:
    def test_crumb_header(self, mocker):
        jenkins = Jenkins(url='https://example.com/', username='username', password='password')
        mocker.patch.object(
            jenkins,
            'request',
            return_value=mocker.Mock(
                json=lambda: {
                    'crumbRequestField': 'Jenkins-Crumb',
                    'crumb': 'crumb-value',
                }
            ),
        )
        assert jenkins.crumb_header == {'Jenkins-Crumb': 'crumb-value'}

    def test_crumb_header_404(self, mocker):
        jenkins = Jenkins(url='https://example.com/', username='username', password='password')
        mocker.patch.object(
            jenkins,
            'request',
            side_effect=HTTPError(response=mocker.Mock(status_code=404)),
        )

        assert jenkins.crumb_header == {}

    def test_crumb_header_other_http_error(self, mocker):
        jenkins = Jenkins(url='https://example.com/', username='username', password='password')
        mocker.patch.object(
            jenkins,
            'request',
            side_effect=HTTPError(response=mocker.Mock(status_code=500)),
        )

        with pytest.raises(HTTPError):
            _ = jenkins.crumb_header


class TestCrumbRetry:
    def test_retry_on_403_refreshes_crumb(self, mock_session, mocker):
        j = Jenkins(url='https://example.com/', username='username', password='password')
        # Simulate stale crumb cached from earlier
        j._crumb_header = {'Jenkins-Crumb': 'stale-crumb'}

        forbidden_resp = mocker.Mock(status_code=403)
        forbidden_resp.raise_for_status.side_effect = HTTPError(response=forbidden_resp)

        success_resp = mocker.Mock(status_code=201)
        success_resp.raise_for_status.return_value = None

        crumb_resp = mocker.Mock(
            status_code=200,
            json=lambda: {'crumbRequestField': 'Jenkins-Crumb', 'crumb': 'fresh-crumb'},
        )
        crumb_resp.raise_for_status.return_value = None

        # First POST → 403, crumb refresh GET → new crumb, retry POST → 201
        mock_session.request.side_effect = [forbidden_resp, crumb_resp, success_resp]

        result = j.request('POST', 'job/test/build')

        assert result.status_code == 201
        assert j._crumb_header == {'Jenkins-Crumb': 'fresh-crumb'}
        assert mock_session.request.call_count == 3

    def test_no_retry_when_crumb_was_empty(self, mock_session, mocker):
        j = Jenkins(url='https://example.com/', username='username', password='password')
        # Empty crumb (CSRF disabled) — should NOT retry on 403
        j._crumb_header = {}

        forbidden_resp = mocker.Mock(status_code=403)
        forbidden_resp.raise_for_status.side_effect = HTTPError(response=forbidden_resp)
        mock_session.request.return_value = forbidden_resp

        with pytest.raises(HTTPError):
            j.request('POST', 'job/test/build')

        assert mock_session.request.call_count == 1

    def test_no_retry_on_non_403_errors(self, mock_session, mocker):
        """Server errors (500, 401, etc.) must not trigger the crumb retry path."""
        j = Jenkins(url='https://example.com/', username='username', password='password')
        j._crumb_header = {'Jenkins-Crumb': 'some-crumb'}

        for status in (401, 500, 502):
            mock_session.reset_mock()
            error_resp = mocker.Mock(status_code=status)
            error_resp.raise_for_status.side_effect = HTTPError(response=error_resp)
            mock_session.request.return_value = error_resp

            with pytest.raises(HTTPError):
                j.request('POST', 'job/test/build')

            # Only 1 call — no retry
            assert mock_session.request.call_count == 1

    def test_no_retry_when_crumb_is_false(self, mock_session, mocker):
        """Requests with crumb=False must never trigger the retry path, even on 403."""
        j = Jenkins(url='https://example.com/', username='username', password='password')
        j._crumb_header = {'Jenkins-Crumb': 'some-crumb'}

        forbidden_resp = mocker.Mock(status_code=403)
        forbidden_resp.raise_for_status.side_effect = HTTPError(response=forbidden_resp)
        mock_session.request.return_value = forbidden_resp

        with pytest.raises(HTTPError):
            j.request('GET', 'crumbIssuer/api/json', crumb=False)

        assert mock_session.request.call_count == 1

    def test_retry_also_fails_raises_original_error(self, mock_session, mocker):
        """When the retry request also returns 403, the error must propagate."""
        j = Jenkins(url='https://example.com/', username='username', password='password')
        j._crumb_header = {'Jenkins-Crumb': 'stale-crumb'}

        forbidden_resp = mocker.Mock(status_code=403)
        forbidden_resp.raise_for_status.side_effect = HTTPError(response=forbidden_resp)

        crumb_resp = mocker.Mock(
            status_code=200,
            json=lambda: {'crumbRequestField': 'Jenkins-Crumb', 'crumb': 'fresh-crumb'},
        )
        crumb_resp.raise_for_status.return_value = None

        still_forbidden_resp = mocker.Mock(status_code=403)
        still_forbidden_resp.raise_for_status.side_effect = HTTPError(response=still_forbidden_resp)

        # First POST → 403, crumb refresh → ok, retry POST → still 403
        mock_session.request.side_effect = [forbidden_resp, crumb_resp, still_forbidden_resp]

        with pytest.raises(HTTPError) as exc_info:
            j.request('POST', 'job/test/build')

        assert exc_info.value.response.status_code == 403
        assert mock_session.request.call_count == 3


def test_parse_fullname(jenkins):
    assert jenkins._parse_fullname('job-name') == ('', 'job-name')
    assert jenkins._parse_fullname('folder/job-name') == ('job/folder/', 'job-name')
    assert jenkins._parse_fullname('folder/subfolder/job-name') == (
        'job/folder/job/subfolder/',
        'job-name',
    )


class TestView:
    def test_build_view_path(self, jenkins):
        assert jenkins._build_view_path('All') == 'view/All'
        assert jenkins._build_view_path('frontend/nightly') == 'view/frontend/view/nightly'
        assert jenkins._build_view_path('frontend/nightly/nightly linux') == (
            'view/frontend/view/nightly/view/nightly%20linux'
        )

    def test_get_views(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'views': [
                    {'name': 'All', 'url': 'https://example.com/view/All/'},
                    {'name': 'frontend', 'url': 'https://example.com/view/frontend/'},
                ]
            }
        )

        assert jenkins.get_views() == [
            {'name': 'All', 'url': 'https://example.com/view/All/'},
            {'name': 'frontend', 'url': 'https://example.com/view/frontend/'},
        ]

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/api/json?tree=views[name,url]',
            headers={'Jenkins-Crumb': 'crumb-value'},
            params=None,
            data=None,
            timeout=75,
        )

    def test_get_view(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'name': 'frontend',
                'jobs': [
                    {
                        'name': 'build-ui',
                        'url': 'https://example.com/job/build-ui/',
                        'color': 'blue',
                    }
                ],
            }
        )

        result = jenkins.get_view(view_path='frontend')

        assert result == {
            'name': 'frontend',
            'jobs': [
                {
                    'name': 'build-ui',
                    'url': 'https://example.com/job/build-ui/',
                    'color': 'blue',
                }
            ],
        }

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/view/frontend/api/json?depth=0',
            headers={'Jenkins-Crumb': 'crumb-value'},
            params=None,
            data=None,
            timeout=75,
        )

    def test_get_view_nested(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'name': 'nightly linux',
                'jobs': [
                    {
                        'name': 'integration-tests',
                        'url': 'https://example.com/job/integration-tests/',
                        'color': 'blue',
                    }
                ],
            }
        )

        result = jenkins.get_view(view_path='frontend/nightly/nightly linux')

        assert result['name'] == 'nightly linux'
        assert len(result['jobs']) == 1

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/view/frontend/view/nightly/view/nightly%20linux/api/json?depth=0',
            headers={'Jenkins-Crumb': 'crumb-value'},
            params=None,
            data=None,
            timeout=75,
        )


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
                        fullDisplayName='Example Job',
                        name='example-job',
                        url='https://example.com/job/example-job/',
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
                fullDisplayName='Example Job',
                name='example-job',
                url='https://example.com/job/example-job/',
            ),
        )

    def test_cancel_queue_item(self, jenkins, mock_session):
        assert jenkins.cancel_queue_item(id=42) is None
        mock_session.request.assert_called_once_with(
            method='POST',
            url='https://example.com/queue/cancelItem?id=42',
            headers={'Jenkins-Crumb': 'crumb-value'},
            params=None,
            data=None,
            timeout=75,
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
                        url='https://example.com/job/example-job/1/',
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
            params=None,
            data=None,
            timeout=75,
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
                        url='https://example.com/job/example-job/1/',
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
            params=None,
            data=None,
            timeout=75,
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

    def test_set_node_config(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(status_code=200)

        assert jenkins.set_node_config(name='node-1', config_xml='<node>new config</node>') is None

        mock_session.request.assert_called_once_with(
            method='POST',
            url='https://example.com/computer/node-1/config.xml',
            headers={
                'Jenkins-Crumb': 'crumb-value',
                'Content-Type': 'text/xml; charset=utf-8',
            },
            params=None,
            data='<node>new config</node>',
            timeout=75,
        )


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

    def _mock_console_lines(self, mock_session, mocker, lines: list[str]):
        mock_response = mocker.Mock()
        mock_response.iter_lines.return_value = iter(lines)
        mock_session.get.return_value = mock_response
        return mock_response

    def test_get_build_console_output(self, jenkins, mock_session, mocker):
        self._mock_console_lines(mock_session, mocker, ['line1', 'line2', 'line3'])

        assert jenkins.get_build_console_output(fullname='example-job', number=1) == 'line1\nline2\nline3'

        mock_session.get.assert_called_once_with(
            'https://example.com/job/example-job/1/consoleText',
            timeout=jenkins.timeout,
            stream=True,
        )

    def test_get_build_console_output_with_pattern(self, jenkins, mock_session, mocker):
        self._mock_console_lines(
            mock_session,
            mocker,
            ['ERROR: something failed', 'INFO: all good', 'ERROR: again'],
        )

        result = jenkins.get_build_console_output(fullname='example-job', number=1, pattern='ERROR')
        assert result == 'ERROR: something failed\nERROR: again'

    def test_get_build_console_output_with_offset(self, jenkins, mock_session, mocker):
        self._mock_console_lines(mock_session, mocker, ['line1', 'line2', 'line3', 'line4'])

        result = jenkins.get_build_console_output(fullname='example-job', number=1, offset=2)
        assert result == 'line3\nline4'

    def test_get_build_console_output_with_limit(self, jenkins, mock_session, mocker):
        self._mock_console_lines(mock_session, mocker, ['line1', 'line2', 'line3', 'line4'])

        result = jenkins.get_build_console_output(fullname='example-job', number=1, limit=2)
        assert result == 'line1\nline2'

    def test_get_build_console_output_with_offset_and_limit(self, jenkins, mock_session, mocker):
        self._mock_console_lines(mock_session, mocker, ['line1', 'line2', 'line3', 'line4', 'line5'])

        result = jenkins.get_build_console_output(fullname='example-job', number=1, offset=1, limit=2)
        assert result == 'line2\nline3'

    def test_get_build_console_output_pattern_with_offset_and_limit(self, jenkins, mock_session, mocker):
        self._mock_console_lines(
            mock_session,
            mocker,
            ['ERROR: a', 'INFO: b', 'ERROR: c', 'ERROR: d', 'ERROR: e'],
        )

        # pattern filters to: ERROR:a, ERROR:c, ERROR:d, ERROR:e → offset=1 → c,d,e → limit=2 → c,d
        result = jenkins.get_build_console_output(fullname='example-job', number=1, pattern='ERROR', offset=1, limit=2)
        assert result == 'ERROR: c\nERROR: d'

    def test_get_build_console_output_stops_early_on_limit(self, jenkins, mock_session, mocker):
        """Verify response.close() is called when limit is reached mid-stream."""
        mock_response = self._mock_console_lines(mock_session, mocker, ['a', 'b', 'c', 'd', 'e'])

        jenkins.get_build_console_output(fullname='example-job', number=1, limit=2)
        mock_response.close.assert_called_once()

    def test_stop_build(self, jenkins, mock_session):
        assert jenkins.stop_build(fullname='example-job', number=42) is None

        mock_session.request.assert_called_once_with(
            method='POST',
            url='https://example.com/job/example-job/42/stop',
            headers={'Jenkins-Crumb': 'crumb-value'},
            params=None,
            data=None,
            timeout=75,
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

    def test_get_build_parameters(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'actions': [
                    {
                        '_class': 'hudson.model.ParametersAction',
                        'parameters': [
                            {'name': 'BRANCH', 'value': 'main'},
                            {'name': 'DEBUG', 'value': True},
                        ],
                    },
                ]
            }
        )

        assert jenkins.get_build_parameters(fullname='example-job', number=1) == {
            'BRANCH': 'main',
            'DEBUG': True,
        }

        mock_session.request.assert_called_once_with(
            method='GET',
            url='https://example.com/job/example-job/1/api/json?tree=actions[parameters[name,value]]',
            headers={'Jenkins-Crumb': 'crumb-value'},
            params=None,
            data=None,
            timeout=75,
        )

    def test_get_build_parameters_no_params(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(json=lambda: {'actions': []})

        assert jenkins.get_build_parameters(fullname='example-job', number=1) == {}

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


class TestItem:
    def test_get_items(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'jobs': [
                    {
                        'name': 'example-job',
                        'url': 'https://example.com/job/example-job/',
                        '_class': 'hudson.model.WorkflowJob',
                        'color': 'blue',
                        'fullName': 'example-job',
                    },
                    {
                        'name': 'example-folder',
                        'url': 'https://example.com/job/example-folder/',
                        '_class': 'com.cloudbees.hudson.plugins.folder.Folder',
                        'fullName': 'example-folder',
                        'jobs': [
                            {
                                'name': 'nested-job',
                                'url': 'https://example.com/job/example-folder/job/nested-job/',
                                '_class': 'hudson.model.FreeStyleProject',
                                'color': 'red',
                                'fullname': 'example-folder',
                            },
                            {
                                'name': 'nested-multibranch',
                                'url': 'https://example.com/job/example-folder/job/nested-multibranch',
                                '_class': 'org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject',
                                'fullname': 'example-multibranch',
                                'jobs': [
                                    {
                                        'name': 'example-job',
                                        'url': 'https://example.com/job/example-folder/job/nested-multibranch/job/example-job/',
                                        '_class': 'hudson.model.WorkflowJob',
                                        'color': 'blue',
                                        'fullname': 'example-multibranch/job/example-job',
                                    }
                                ],
                            },
                        ],
                    },
                ]
            }
        )

        assert jenkins.get_items() == [
            Job(
                class_='hudson.model.WorkflowJob',
                name='example-job',
                url='https://example.com/job/example-job/',
                fullname='example-job',
                color='blue',
            ),
            Folder(
                class_='com.cloudbees.hudson.plugins.folder.Folder',
                name='example-folder',
                url='https://example.com/job/example-folder/',
                fullname='example-folder',
                jobs=[
                    FreeStyleProject(
                        class_='hudson.model.FreeStyleProject',
                        name='nested-job',
                        url='https://example.com/job/example-folder/job/nested-job/',
                        fullname='example-folder',
                        color='red',
                    ),
                    MultiBranchProject(
                        class_='org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject',
                        name='nested-multibranch',
                        url='https://example.com/job/example-folder/job/nested-multibranch',
                        fullname='example-multibranch',
                        jobs=[
                            Job(
                                class_='hudson.model.WorkflowJob',
                                name='example-job',
                                url='https://example.com/job/example-folder/job/nested-multibranch/job/example-job/',
                                fullname='example-multibranch/job/example-job',
                                color='blue',
                            )
                        ],
                    ),
                ],
            ),
            FreeStyleProject(
                class_='hudson.model.FreeStyleProject',
                name='nested-job',
                url='https://example.com/job/example-folder/job/nested-job/',
                fullname='example-folder',
                color='red',
            ),
            MultiBranchProject(
                class_='org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject',
                name='nested-multibranch',
                url='https://example.com/job/example-folder/job/nested-multibranch',
                fullname='example-multibranch',
                jobs=[
                    Job(
                        class_='hudson.model.WorkflowJob',
                        name='example-job',
                        url='https://example.com/job/example-folder/job/nested-multibranch/job/example-job/',
                        fullname='example-multibranch/job/example-job',
                        color='blue',
                    )
                ],
            ),
            Job(
                class_='hudson.model.WorkflowJob',
                name='example-job',
                url='https://example.com/job/example-folder/job/nested-multibranch/job/example-job/',
                fullname='example-multibranch/job/example-job',
                color='blue',
            ),
        ]

    def test_get_item(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'name': 'example-folder',
                'url': 'https://example.com/job/example-folder/',
                '_class': 'com.cloudbees.hudson.plugins.folder.Folder',
                'fullName': 'example-folder',
                'jobs': [
                    {
                        'name': 'nested-job',
                        'url': 'https://example.com/job/example-folder/job/nested-job/',
                        '_class': 'hudson.model.WorkflowJob',
                        'color': 'red',
                        'fullname': 'example-folder/example-job',
                    }
                ],
            }
        )

        assert jenkins.get_item(fullname='example-folder') == Folder(
            class_='com.cloudbees.hudson.plugins.folder.Folder',
            name='example-folder',
            url='https://example.com/job/example-folder/',
            fullname='example-folder',
            jobs=[
                Job(
                    class_='hudson.model.WorkflowJob',
                    name='nested-job',
                    url='https://example.com/job/example-folder/job/nested-job/',
                    fullname='example-folder/example-job',
                    color='red',
                )
            ],
        )

    def test_get_item_config(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(text='<project>config</project>')

        assert jenkins.get_item_config(fullname='example-job') == '<project>config</project>'

    def test_set_item_config(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(status_code=200)

        assert jenkins.set_item_config(fullname='example-job', config_xml='<project>new config</project>') is None

        mock_session.request.assert_called_once_with(
            method='POST',
            url='https://example.com/job/example-job/config.xml',
            headers={
                'Jenkins-Crumb': 'crumb-value',
                'Content-Type': 'text/xml; charset=utf-8',
            },
            params=None,
            data='<project>new config</project>',
            timeout=75,
        )

    def test_query_items(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'jobs': [
                    {
                        'name': 'example-job',
                        'url': 'https://example.com/job/example-job/',
                        '_class': 'hudson.model.WorkflowJob',
                        'color': 'blue',
                        'fullName': 'example-job',
                    },
                    {
                        'name': 'another-job',
                        'url': 'https://example.com/job/another-job/',
                        '_class': 'hudson.model.FreeStyleProject',
                        'color': 'red',
                        'fullName': 'another-job',
                    },
                ]
            }
        )

        assert jenkins.query_items(
            class_pattern='.*WorkflowJob',
        ) == [
            Job(
                class_='hudson.model.WorkflowJob',
                name='example-job',
                url='https://example.com/job/example-job/',
                fullname='example-job',
                color='blue',
            )
        ]

        assert jenkins.query_items(
            color_pattern='red',
        ) == [
            FreeStyleProject(
                class_='hudson.model.FreeStyleProject',
                name='another-job',
                url='https://example.com/job/another-job/',
                fullname='another-job',
                color='red',
            )
        ]

        assert jenkins.query_items(fullname_pattern='example') == [
            Job(
                class_='hudson.model.WorkflowJob',
                name='example-job',
                url='https://example.com/job/example-job/',
                fullname='example-job',
                color='blue',
            )
        ]

    def test_build_item(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            status_code=201, headers={'Location': 'https://example.com/queue/item/123/'}
        )

        assert (
            jenkins.build_item(
                fullname='example-job',
                build_type='buildWithParameters',
                params={'param1': 'value1'},
            )
            == 123
        )

        mock_session.request.assert_called_once_with(
            method='POST',
            url='https://example.com/job/example-job/buildWithParameters',
            headers={'Jenkins-Crumb': 'crumb-value'},
            params=None,
            data={'param1': 'value1'},
            timeout=75,
        )


class TestPlugin:
    def test_get_plugins(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {'shortName': 'plugin-a', 'version': '1.0', 'enabled': True},
                    {'shortName': 'plugin-b', 'version': '2.0', 'enabled': False},
                ]
            }
        )

        assert jenkins.get_plugins(depth=0) == [
            {'shortName': 'plugin-a', 'version': '1.0', 'enabled': True},
            {'shortName': 'plugin-b', 'version': '2.0', 'enabled': False},
        ]

    def test_get_plugin_found(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {'shortName': 'plugin-a', 'version': '1.0'},
                    {'shortName': 'plugin-b', 'version': '2.0'},
                ]
            }
        )

        result = jenkins.get_plugin(short_name='plugin-b')
        assert result == {'shortName': 'plugin-b', 'version': '2.0'}

    def test_get_plugin_not_found(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {'shortName': 'plugin-a', 'version': '1.0'},
                ]
            }
        )

        result = jenkins.get_plugin(short_name='nonexistent')
        assert result is None

    def test_get_plugins_with_problems(self, jenkins, mock_session, mocker):
        pass

    def test_get_plugins_with_problems_missing_dependency(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'version': '2.479.3',
            }
        )
        mock_session.request.return_value.headers = {'X-Jenkins': '2.479.3'}

        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {
                        'shortName': 'plugin-a',
                        'version': '1.0',
                        'enabled': True,
                        'dependencies': [
                            {'shortName': 'missing-dep', 'version': '1.0', 'optional': False, 'bundled': False},
                        ],
                    },
                ]
            }
        )

        problems = jenkins.get_plugins_with_problems()
        missing_dep = next((p for p in problems if p['problem'] == 'missing_dependency'), None)
        assert missing_dep is not None
        assert missing_dep['dependency'] == 'missing-dep'

    def test_get_plugins_with_problems_optional_dependency_ignored(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'version': '2.479.3',
            }
        )
        mock_session.request.return_value.headers = {'X-Jenkins': '2.479.3'}

        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {
                        'shortName': 'plugin-a',
                        'version': '1.0',
                        'enabled': True,
                        'dependencies': [
                            {'shortName': 'optional-dep', 'version': '1.0', 'optional': True, 'bundled': False},
                        ],
                    },
                ]
            }
        )

        problems = jenkins.get_plugins_with_problems()
        missing_optional = next((p for p in problems if p['problem'] == 'missing_optional_dependency'), None)
        assert missing_optional is not None

    def test_get_plugins_with_problems_version_mismatch(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'version': '2.479.3',
            }
        )
        mock_session.request.return_value.headers = {'X-Jenkins': '2.479.3'}

        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {
                        'shortName': 'plugin-a',
                        'version': '1.0',
                        'enabled': True,
                        'dependencies': [
                            {'shortName': 'dep-plugin', 'version': '2.0', 'optional': False, 'bundled': False},
                        ],
                    },
                    {'shortName': 'dep-plugin', 'version': '1.5'},
                ]
            }
        )

        problems = jenkins.get_plugins_with_problems()
        version_issue = next((p for p in problems if p['problem'] == 'version_mismatch'), None)
        assert version_issue is not None

    def test_get_plugins_with_problems_installed_version_higher_no_issue(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'version': '2.479.3',
            }
        )
        mock_session.request.return_value.headers = {'X-Jenkins': '2.479.3'}

        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {
                        'shortName': 'plugin-a',
                        'version': '1.0',
                        'enabled': True,
                        'dependencies': [
                            {'shortName': 'dep-plugin', 'version': '1.0', 'optional': False, 'bundled': False},
                        ],
                    },
                    {'shortName': 'dep-plugin', 'version': '2.0'},
                ]
            }
        )

        problems = jenkins.get_plugins_with_problems()
        version_issue = next((p for p in problems if p['problem'] == 'version_mismatch'), None)
        assert version_issue is None

    def test_get_plugins_with_updates(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {'shortName': 'plugin-a', 'version': '1.0', 'hasUpdate': True},
                    {'shortName': 'plugin-b', 'version': '2.0', 'hasUpdate': False},
                ]
            }
        )

        result = jenkins.get_plugins_with_updates()
        assert len(result) == 1
        assert result[0]['shortName'] == 'plugin-a'

    def test_get_plugins_with_backup(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {'shortName': 'plugin-a', 'version': '1.0', 'backupVersion': '0.9', 'downgradable': True},
                    {'shortName': 'plugin-b', 'version': '2.0'},
                ]
            }
        )

        result = jenkins.get_plugins_with_backup()
        assert len(result) == 1
        assert result[0]['shortName'] == 'plugin-a'
        assert result[0]['backupVersion'] == '0.9'

    def test_get_plugin_dependency_graph(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {
                        'shortName': 'plugin-a',
                        'version': '1.0',
                        'dependencies': [
                            {'shortName': 'plugin-b', 'version': '1.0', 'optional': False},
                            {'shortName': 'plugin-c', 'version': '1.0', 'optional': True},
                        ],
                    },
                    {
                        'shortName': 'plugin-b',
                        'version': '1.0',
                        'dependencies': [],
                    },
                    {'shortName': 'plugin-c', 'version': '1.0', 'dependencies': []},
                ]
            }
        )

        result = jenkins.get_plugin_dependency_graph('plugin-a')
        assert 'nodes' in result
        assert 'edges' in result
        assert len(result['nodes']) == 3
        assert len(result['edges']) == 2

    def test_get_plugin_dependency_graph_not_found(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {'shortName': 'plugin-a', 'version': '1.0', 'dependencies': []},
                ]
            }
        )

        result = jenkins.get_plugin_dependency_graph('nonexistent')
        assert 'error' in result
        assert result['error'] == 'Plugin not found: nonexistent'

    def test_get_plugins_with_problems_disabled_plugin(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'version': '2.479.3',
            }
        )
        mock_session.request.return_value.headers = {'X-Jenkins': '2.479.3'}

        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {
                        'shortName': 'plugin-a',
                        'version': '1.0',
                        'enabled': False,
                        'dependencies': [],
                    },
                ]
            }
        )

        problems = jenkins.get_plugins_with_problems()
        disabled = next((p for p in problems if p['problem'] == 'plugin_disabled'), None)
        assert disabled is not None
        assert disabled['shortName'] == 'plugin-a'

    def test_get_plugins_with_problems_optional_version_mismatch(self, jenkins, mock_session, mocker):
        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'version': '2.479.3',
            }
        )
        mock_session.request.return_value.headers = {'X-Jenkins': '2.479.3'}

        mock_session.request.return_value = mocker.Mock(
            json=lambda: {
                'plugins': [
                    {
                        'shortName': 'plugin-a',
                        'version': '1.0',
                        'enabled': True,
                        'dependencies': [
                            {'shortName': 'optional-dep', 'version': '2.0', 'optional': True, 'bundled': False},
                        ],
                    },
                    {'shortName': 'optional-dep', 'version': '1.5'},
                ]
            }
        )

        problems = jenkins.get_plugins_with_problems()
        version_issue = next((p for p in problems if p['problem'] == 'version_mismatch_optional'), None)
        assert version_issue is not None
        assert version_issue['dependency'] == 'optional-dep'
