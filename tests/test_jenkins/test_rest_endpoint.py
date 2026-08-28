import pytest

from mcp_jenkins.jenkins import rest_endpoint
from mcp_jenkins.jenkins.rest_endpoint import RestEndpoint


def test_rest_endpoint_new():
    assert RestEndpoint('api/json?depth={depth}')._fields == {'depth'}
    assert RestEndpoint('api/json')._fields == set()


def test_rest_endpoint_call():
    endpoint = RestEndpoint('api/json?depth={depth}')

    assert endpoint(depth=0) == 'api/json?depth=0'


def test_rest_endpoint_call_missing():
    endpoint = RestEndpoint('api/json?depth={depth}')

    with pytest.raises(KeyError) as exc_info:
        endpoint()

    assert str(exc_info.value) == '"Missing: {\'depth\'}"'


@pytest.mark.parametrize(
    ('endpoint', 'kwargs', 'expected'),
    [
        (
            rest_endpoint.BUILD,
            {'folder': '', 'name': 'example-job', 'number': 'lastFailedBuild', 'depth': 0},
            'job/example-job/lastFailedBuild/api/json?depth=0',
        ),
        (
            rest_endpoint.BUILD_CONSOLE_OUTPUT,
            {'folder': '', 'name': 'example-job', 'number': 'lastFailedBuild'},
            'job/example-job/lastFailedBuild/consoleText',
        ),
        (
            rest_endpoint.BUILD_REPLAY,
            {'folder': '', 'name': 'example-job', 'number': 'lastFailedBuild'},
            'job/example-job/lastFailedBuild/replay',
        ),
        (
            rest_endpoint.BUILD_PARAMETERS,
            {'folder': '', 'name': 'example-job', 'number': 'lastFailedBuild'},
            'job/example-job/lastFailedBuild/api/json?tree=actions[parameters[name,value]]',
        ),
        (
            rest_endpoint.BUILD_TEST_REPORT,
            {'folder': '', 'name': 'example-job', 'number': 'lastFailedBuild', 'depth': 0},
            'job/example-job/lastFailedBuild/testReport/api/json?depth=0',
        ),
        (
            rest_endpoint.BUILD_ARTIFACTS,
            {'folder': '', 'name': 'example-job', 'number': 'lastFailedBuild'},
            'job/example-job/lastFailedBuild/api/json?tree=artifacts[fileName,relativePath,displayPath]',
        ),
        (
            rest_endpoint.BUILD_ARTIFACT,
            {
                'folder': '',
                'name': 'example-job',
                'number': 'lastFailedBuild',
                'relative_path': 'report.txt',
            },
            'job/example-job/lastFailedBuild/artifact/report.txt',
        ),
    ],
)
def test_read_build_endpoints_accept_permalinks(endpoint, kwargs, expected):
    assert endpoint(**kwargs) == expected
