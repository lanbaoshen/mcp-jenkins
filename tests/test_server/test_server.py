import pytest
from starlette.testclient import TestClient

from mcp_jenkins.server import JenkinsMCP, mcp


def test_http_app(mocker):
    jm = JenkinsMCP('mcp-jenkins-test')

    mock_wm = mocker.Mock()
    mocker.patch('mcp_jenkins.server.ASGIMiddleware', return_value=mock_wm)

    assert jm.http_app(path='/mcp', middleware=[mock_wm], transport='http').user_middleware.count(mock_wm) == 2


def test_healthz_returns_200():
    client = TestClient(mcp.http_app(transport='http'))

    response = client.get('/healthz')

    assert response.status_code == 200
    assert response.text == 'OK'


@pytest.mark.asyncio
async def test_read_build_tools_expose_permalink_schema():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    read_build_tools = (
        'get_build',
        'get_build_scripts',
        'get_build_console_output',
        'get_build_test_report',
        'get_build_parameters',
        'get_all_build_artifacts',
        'get_build_artifact',
        'get_build_artifact_url',
    )

    for name in read_build_tools:
        schema = tools[name].parameters['properties']['number']
        assert {option['type'] for option in schema['anyOf']} == {'integer', 'string', 'null'}

    assert tools['stop_build'].parameters['properties']['number'] == {'type': 'integer'}
