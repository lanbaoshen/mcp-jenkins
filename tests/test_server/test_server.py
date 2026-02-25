from mcp_jenkins.server import JenkinsMCP


def test_http_app(mocker):
    jm = JenkinsMCP('mcp-jenkins-test')

    mock_wm = mocker.Mock()
    mocker.patch('mcp_jenkins.server.ASGIMiddleware', return_value=mock_wm)

    assert jm.http_app(path='/mcp', middleware=[mock_wm], transport='http').user_middleware.count(mock_wm) == 2
