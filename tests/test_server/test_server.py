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
